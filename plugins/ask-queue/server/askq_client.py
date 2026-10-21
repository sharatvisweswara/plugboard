#!/usr/bin/env python3
"""ask-queue client: runs on the machine that hosts the Claude session.

Called by the hooks with the hook input on stdin:
  askq_client.py pre-ask   PreToolUse on AskUserQuestion. Prints the hook output JSON.
  askq_client.py wait      Stop hook (asyncRewake). Exit 2 + answers on stderr wakes the session.

The client builds the session context, branch, and host itself, so the hub
never needs the session's filesystem. It talks to the hub named in
<state>/hub (first line, a URL), or to the local daemon when that file is
absent. With a remote hub, questions that cannot be sent go to <state>/spool/
and are sent by the next `wait`.

Every outcome and error goes to <state>/ask-queue.log, one line per event,
from both this client and the daemon (see log()).

Standard library only; must run on the macOS system python3 (3.9).
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("ASKQ_PORT", "7788"))
STATE_DIR = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")), "ask-queue")
HUB_FILE = os.path.join(STATE_DIR, "hub")
LOG_PATH = os.path.join(STATE_DIR, "ask-queue.log")
# At this size the log moves to ask-queue.log.1 (one old copy kept).
LOG_MAX_BYTES = 5 * 1024 * 1024
SPOOL_DIR = os.path.join(STATE_DIR, "spool")
# One marker per session that may have open questions on the hub. `wait`
# retries through connection errors only while the marker exists.
OUTSTANDING_DIR = os.path.join(STATE_DIR, "outstanding")
TAILSCALE_CLIS = ("tailscale", "/usr/local/bin/tailscale", "/Applications/Tailscale.app/Contents/MacOS/Tailscale")

# Total time `wait` keeps trying before it gives up.
WAIT_MAX_SECONDS = 24 * 3600
# Retry delays after a connection error: 5 s, doubling, capped at 60 s.
RETRY_FIRST, RETRY_MAX = 5, 60

DENY_REASON = (
    "Your question was queued as {id} in the user's ask-queue inbox. The user answers "
    "asynchronously, possibly hours from now. Do not ask it again and do not wait for it. "
    "Continue with any work that does not depend on the answer. If you have other "
    "independent questions, ask them now with AskUserQuestion so they are queued too. "
    "When you are blocked on answers, end your turn: the answer will arrive as a new message."
)


def log(role, event, **fields):
    """Append one event line to LOG_PATH:
      2026-10-21T15:01:02-0700 wait[4242] hub-error session=3d897396 error="..."
    A multi-line `trace` field follows the line, indented. Never raises: a
    logging problem must not break a hook."""
    try:
        trace = fields.pop("trace", None)
        parts = []
        for k, v in fields.items():
            v = "" if v is None else str(v)
            if not v or any(c.isspace() or c == '"' for c in v):
                v = json.dumps(v)
            parts.append("%s=%s" % (k, v))
        line = "%s %s[%d] %s %s" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), role, os.getpid(), event, " ".join(parts))
        if trace:
            line += "\n" + "\n".join("    " + t for t in trace.rstrip().splitlines())
        os.makedirs(STATE_DIR, exist_ok=True)
        try:
            if os.path.getsize(LOG_PATH) > LOG_MAX_BYTES:
                os.replace(LOG_PATH, LOG_PATH + ".1")
        except OSError:
            pass
        with open(LOG_PATH, "a") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass


def short(session_id):
    return (session_id or "unknown")[:8]


def deny_output(label):
    """PreToolUse hook output that denies AskUserQuestion with the queued label."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": DENY_REASON.format(id=label),
        }
    }


def hub_url():
    """Return (base URL, remote?). Remote when <state>/hub names a URL."""
    try:
        with open(HUB_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    return line.rstrip("/"), True
    except OSError:
        pass
    return "http://127.0.0.1:%d" % PORT, False


def post(url, payload, timeout):
    """POST JSON; return (status, body bytes). Raises OSError on connection failure."""
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
        raise OSError(str(e))


def alive(base):
    try:
        with urllib.request.urlopen(base + "/health", timeout=2) as resp:
            return resp.status == 200
    except (OSError, urllib.error.URLError):
        return False


def start_local_daemon(base):
    """Start askqd.py on this machine; True once /health answers (~3 s max)."""
    if alive(base):
        return True
    try:
        subprocess.run(
            [sys.executable, os.path.join(HERE, "askqd.py"), "--daemon"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        log("client", "daemon-start-failed", python=sys.executable, error=e)
        return False
    for _ in range(15):
        if alive(base):
            log("client", "daemon-started", url=base)
            return True
        time.sleep(0.2)
    log("client", "daemon-start-failed", python=sys.executable, error="no /health after 3 s; see askqd.log")
    return False


# --- context -------------------------------------------------------------


def entry_text(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        return "\n".join(t for t in texts if t.strip()).strip()
    return ""


def session_context(transcript_path, limit=3000):
    """Return the user's latest prompt plus the assistant text written since
    then, read from the session transcript. None when unavailable."""
    if not transcript_path or not os.path.isfile(transcript_path):
        return None
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 1024 * 1024))
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return None
    assistant = []
    prompt = None
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        kind = entry.get("type")
        content = (entry.get("message") or {}).get("content")
        if kind == "user" and isinstance(content, str) and content.strip():
            prompt = content.strip()
            break
        if kind == "assistant":
            text = entry_text(entry)
            if text:
                assistant.append(text)
    parts = []
    if prompt:
        parts.append("User asked:\n" + prompt[:1000])
    if assistant:
        parts.append("Claude said:\n" + "\n\n".join(reversed(assistant))[-(limit - 1000):])
    return "\n\n".join(parts) or None


def git_branch(cwd):
    if not cwd:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def host_name():
    """Tailscale host name when available (EC2 hostnames are ip-10-...), else hostname -s."""
    for cli in TAILSCALE_CLIS:
        path = shutil.which(cli)
        if not path:
            continue
        try:
            out = subprocess.run([path, "status", "--self", "--json"], capture_output=True, text=True, timeout=5)
            name = json.loads(out.stdout)["Self"]["HostName"]
            if name:
                return name
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError):
            continue
    return socket.gethostname().split(".")[0]


def enrich(hook_input):
    """Hook input plus the fields the hub would otherwise read from local files."""
    payload = dict(hook_input)
    payload["context"] = session_context(hook_input.get("transcript_path"))
    payload["branch"] = git_branch(hook_input.get("cwd"))
    payload["host"] = host_name()
    payload["client_ref"] = uuid.uuid4().hex
    return payload


# --- spool + outstanding markers -----------------------------------------


def mark_outstanding(session_id):
    os.makedirs(OUTSTANDING_DIR, exist_ok=True)
    open(os.path.join(OUTSTANDING_DIR, session_id), "w").close()


def clear_outstanding(session_id):
    try:
        os.remove(os.path.join(OUTSTANDING_DIR, session_id))
    except OSError:
        pass


def is_outstanding(session_id):
    return os.path.exists(os.path.join(OUTSTANDING_DIR, session_id))


def spool(payload):
    os.makedirs(SPOOL_DIR, exist_ok=True)
    path = os.path.join(SPOOL_DIR, "%d-%s.json" % (int(time.time() * 1000), payload["client_ref"]))
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.rename(tmp, path)


def spooled(session_id=None):
    """Spooled payload paths, oldest first; only this session's when given."""
    try:
        names = sorted(n for n in os.listdir(SPOOL_DIR) if n.endswith(".json"))
    except OSError:
        return []
    paths = [os.path.join(SPOOL_DIR, n) for n in names]
    if session_id is None:
        return paths
    mine = []
    for p in paths:
        try:
            with open(p) as f:
                if json.load(f).get("session_id") == session_id:
                    mine.append(p)
        except (OSError, ValueError):
            continue
    return mine


def flush_spool(base):
    """Send every spooled question (all sessions). Stops at the first connection error."""
    for path in spooled():
        name = os.path.basename(path)
        try:
            with open(path) as f:
                payload = json.load(f)
        except (OSError, ValueError) as e:
            log("wait", "spool-unreadable", file=name, error=e)
            continue
        try:
            status, body = post(base + "/hook/pre-ask", payload, timeout=10)
        except OSError as e:
            log("wait", "spool-flush-unreachable", hub=base, file=name, error=e)
            return
        if status == 200:
            os.remove(path)
            log("wait", "spool-sent", session=short(payload.get("session_id")), file=name)
        else:
            log("wait", "spool-refused", session=short(payload.get("session_id")), file=name,
                status=status, body=body[:200].decode("utf-8", "replace"))


# --- commands --------------------------------------------------------------


def cmd_pre_ask(hook_input):
    base, remote = hub_url()
    payload = enrich(hook_input)
    session_id = payload.get("session_id") or "unknown"
    sid = short(session_id)
    if not remote and not start_local_daemon(base):
        log("pre-ask", "fallback-native-picker", session=sid, reason="local daemon unavailable")
        return 0  # no output: the native picker shows as usual
    try:
        status, body = post(base + "/hook/pre-ask", payload, timeout=10)
        error = None
    except OSError as e:
        status, body, error = None, b"", e
    if status == 200:
        mark_outstanding(session_id)
        sys.stdout.write(body.decode() + "\n")
        log("pre-ask", "queued", session=sid, hub=base, ref=payload["client_ref"])
        return 0
    detail = error if status is None else "status %s: %s" % (status, body[:200].decode("utf-8", "replace"))
    if not remote:
        log("pre-ask", "fallback-native-picker", session=sid, hub=base, error=detail)
        return 0
    # Remote hub unreachable or refusing: keep the question and send it later.
    spool(payload)
    mark_outstanding(session_id)
    n = len(spooled(session_id))
    json.dump(deny_output("Q-pending-%d" % n), sys.stdout)
    sys.stdout.write("\n")
    log("pre-ask", "spooled", session=sid, hub=base, ref=payload["client_ref"], pending=n, error=detail)
    return 0


def cmd_wait(hook_input):
    base, remote = hub_url()
    session_id = hook_input.get("session_id") or "unknown"
    sid = short(session_id)
    if not is_outstanding(session_id) and not spooled(session_id):
        return 0
    log("wait", "start", session=sid, hub=base, spooled=len(spooled(session_id)))
    started = time.time()
    deadline = started + WAIT_MAX_SECONDS
    delay = RETRY_FIRST
    slices = errors = 0
    last_error = None
    while time.time() < deadline:
        flush_spool(base)
        try:
            # The hub answers 202 every few minutes with no news; the read
            # timeout only has to outlast that.
            status, body = post(base + "/hook/wait", {"session_id": session_id}, timeout=900)
        except OSError as e:
            errors += 1
            # Log the first failure and each change of error, not every retry.
            if str(e) != last_error:
                log("wait", "hub-error", session=sid, hub=base, error=e, retry_in=delay)
                last_error = str(e)
            if not remote:
                start_local_daemon(base)
            time.sleep(delay)
            delay = min(delay * 2, RETRY_MAX)
            continue
        if last_error is not None:
            log("wait", "hub-reconnected", session=sid, hub=base, failed_attempts=errors)
            last_error = None
        delay = RETRY_FIRST
        waited = int(time.time() - started)
        if status == 200:
            sys.stderr.write(body.decode())
            log("wait", "delivered", session=sid, waited_s=waited, slices=slices)
            return 2
        if status == 202:
            slices += 1
            continue
        if status == 204 and not spooled(session_id):
            clear_outstanding(session_id)
            log("wait", "nothing-open", session=sid, waited_s=waited, slices=slices)
            return 0
        # 204 with questions still spooled (hub refused them), or an error status.
        log("wait", "unexpected-status", session=sid, status=status,
            body=body[:200].decode("utf-8", "replace"), spooled=len(spooled(session_id)))
        time.sleep(delay)
        delay = min(delay * 2, RETRY_MAX)
    log("wait", "gave-up", session=sid, hub=base, waited_s=int(time.time() - started),
        slices=slices, errors=errors, spooled=len(spooled(session_id)))
    return 0


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ("pre-ask", "wait"):
        sys.stderr.write("usage: askq_client.py pre-ask|wait < hook-input.json\n")
        return 64
    role = sys.argv[1]
    try:
        hook_input = json.load(sys.stdin)
    except ValueError as e:
        log(role, "bad-hook-input", error=e)
        return 0
    try:
        if role == "pre-ask":
            return cmd_pre_ask(hook_input)
        return cmd_wait(hook_input)
    except Exception as e:
        # Exit 0 with no output: pre-ask falls back to the native picker,
        # wait ends quietly. The traceback is in the log.
        log(role, "crash", session=short(hook_input.get("session_id")), error=repr(e), trace=traceback.format_exc())
        return 0


if __name__ == "__main__":
    sys.exit(main())
