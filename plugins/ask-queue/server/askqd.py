#!/usr/bin/env python3
"""ask-queue daemon: queues AskUserQuestion calls from many sessions, serves
the inbox page, and hands answers back to waiting Stop hooks.

Standard library only; written for the macOS system python3 (3.9).

Endpoints:
  GET  /health             liveness probe used by the hooks
  POST /hook/pre-ask       PreToolUse hook input in, hook output JSON out
  POST /hook/wait          Stop hook input in; long-polls for answers.
                           200 + wake text, or 204 when there is nothing to wait for
  GET  /                   inbox page
  GET  /api/inbox          open asks as JSON
  POST /api/answer         {"id", "kind": "answer"|"more_info", "answers", "note"}

Listens on 127.0.0.1 always, and also on this machine's tailnet address when
Tailscale is up, so the inbox is reachable from other tailnet devices. The
/hook/* endpoints answer on loopback only.
"""

import json
import os
import select
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
TAILSCALE_CLIS = ("tailscale", "/usr/local/bin/tailscale", "/Applications/Tailscale.app/Contents/MacOS/Tailscale")
PORT = int(os.environ.get("ASKQ_PORT", "7788"))
STATE_DIR = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")), "ask-queue")
DB_PATH = os.path.join(STATE_DIR, "queue.db")
HERE = os.path.dirname(os.path.abspath(__file__))

# Inbox URLs this daemon serves, loopback first; filled in by main().
URLS = []

# Max time one /hook/wait request holds before returning 204.
WAIT_MAX_SECONDS = 24 * 3600

DENY_REASON = (
    "Your question was queued as {id} in the user's ask-queue inbox. The user answers "
    "asynchronously, possibly hours from now. Do not ask it again and do not wait for it. "
    "Continue with any work that does not depend on the answer. If you have other "
    "independent questions, ask them now with AskUserQuestion so they are queued too. "
    "When you are blocked on answers, end your turn: the answer will arrive as a new message."
)

WAKE_FOOTER = (
    "If the user already answered you directly in this session, use your judgement "
    "about which answer to follow. If you still need input from the user, ask with "
    "AskUserQuestion, not in plain text: plain-text questions do not reach the user's inbox."
)

cond = threading.Condition()
# session_id -> token of the newest /hook/wait request; older waiters for the
# same session return 204 when superseded, so at most one waiter delivers.
waiters = {}
waiter_seq = 0


def db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(STATE_DIR, exist_ok=True)
    with db() as conn:
        conn.execute(
            """create table if not exists asks (
                 id integer primary key autoincrement,
                 session_id text not null,
                 cwd text,
                 branch text,
                 context text,
                 questions text not null,
                 status text not null default 'open',
                 response text,
                 created_at integer not null,
                 answered_at integer,
                 delivered_at integer
               )"""
        )


def is_tailnet_ip(ip):
    """True for an IPv4 address in Tailscale's CGNAT range, 100.64.0.0/10."""
    parts = ip.split(".")
    return len(parts) == 4 and parts[0] == "100" and 64 <= int(parts[1]) <= 127


def tailnet_ip():
    """Return this machine's tailnet IPv4 address, or None. Asks the tailscale
    CLI first, then falls back to scanning ifconfig for a 100.64.0.0/10 address."""
    for cli in TAILSCALE_CLIS:
        path = shutil.which(cli)
        if not path:
            continue
        try:
            out = subprocess.run([path, "ip", "-4"], capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            continue
        for line in out.stdout.split():
            if is_tailnet_ip(line.strip()):
                return line.strip()
    try:
        out = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in out.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] == "inet" and is_tailnet_ip(fields[1]):
            return fields[1]
    return None


def git_branch(cwd):
    if not cwd:
        return None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


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
        sys.stderr.write("context: no transcript at %r\n" % transcript_path)
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


def notify(title, body):
    """Desktop notification. terminal-notifier (if installed) opens the inbox
    on click; the osascript fallback can only open Script Editor on click."""
    body = body[:200]
    tn = shutil.which("terminal-notifier") or next(
        (p for p in ("/opt/homebrew/bin/terminal-notifier", "/usr/local/bin/terminal-notifier") if os.path.exists(p)),
        None,
    )
    if tn:
        cmd = [tn, "-title", title, "-message", body, "-open", "http://{}:{}/".format(HOST, PORT), "-group", "ask-queue"]
    else:
        cmd = ["osascript", "-e", "display notification {} with title {}".format(json.dumps(body), json.dumps(title))]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def ask_label(ask_id):
    return "Q-{}".format(ask_id)


def enqueue(hook_input):
    tool_input = hook_input.get("tool_input") or {}
    questions = tool_input.get("questions") or []
    cwd = hook_input.get("cwd")
    with db() as conn:
        cur = conn.execute(
            "insert into asks (session_id, cwd, branch, context, questions, created_at) values (?, ?, ?, ?, ?, ?)",
            (
                hook_input.get("session_id") or "unknown",
                cwd,
                git_branch(cwd),
                session_context(hook_input.get("transcript_path")),
                json.dumps(questions),
                int(time.time()),
            ),
        )
        ask_id = cur.lastrowid
    first = questions[0].get("question", "") if questions else ""
    repo = os.path.basename(cwd) if cwd else "?"
    notify("ask-queue: {} ({})".format(ask_label(ask_id), repo), first)
    with cond:
        cond.notify_all()
    return ask_id


def format_wake(rows):
    parts = []
    for row in rows:
        resp = json.loads(row["response"])
        questions = json.loads(row["questions"])
        label = ask_label(row["id"])
        if resp.get("kind") == "more_info":
            parts.append(
                "The user wants more information before answering queued question {}.\n"
                "Their note: {}\n"
                "Add the context they asked for and ask again with AskUserQuestion.".format(
                    label, resp.get("note") or "(no note)"
                )
            )
            continue
        lines = ["The user answered queued question {}:".format(label)]
        answers = resp.get("answers") or {}
        for q in questions:
            text = q.get("question", "")
            lines.append("- {}\n  Answer: {}".format(text, answers.get(text, "(no answer)")))
        if resp.get("note"):
            lines.append("User note: {}".format(resp["note"]))
        parts.append("\n".join(lines))
    parts.append(WAKE_FOOTER)
    return "\n\n".join(parts)


def peer_closed(sock):
    """True when the client hung up (the Stop hook was killed)."""
    try:
        r, _, _ = select.select([sock], [], [], 0)
        if not r:
            return False
        return sock.recv(1, socket.MSG_PEEK) == b""
    except OSError:
        return True


def wait_for_answers(session_id, sock):
    """Block until this session has answered, undelivered asks. Returns the
    rows (marked delivered), or None when there is nothing to wait for."""
    global waiter_seq
    with cond:
        waiter_seq += 1
        token = waiter_seq
        waiters[session_id] = token
        deadline = time.time() + WAIT_MAX_SECONDS
        try:
            while True:
                if waiters.get(session_id) != token:
                    return None
                with db() as conn:
                    rows = conn.execute(
                        "select * from asks where session_id = ? and status = 'answered' order by id",
                        (session_id,),
                    ).fetchall()
                    if rows:
                        conn.executemany(
                            "update asks set status = 'delivered', delivered_at = ? where id = ?",
                            [(int(time.time()), r["id"]) for r in rows],
                        )
                        return rows
                    pending = conn.execute(
                        "select count(*) from asks where session_id = ? and status = 'open'",
                        (session_id,),
                    ).fetchone()[0]
                if not pending or time.time() > deadline or peer_closed(sock):
                    return None
                cond.wait(timeout=15)
        finally:
            if waiters.get(session_id) == token:
                del waiters[session_id]


def inbox():
    with db() as conn:
        rows = conn.execute(
            "select * from asks where status = 'open' order by created_at"
        ).fetchall()
    with cond:
        live = set(waiters)
    return [
        {
            "id": r["id"],
            "label": ask_label(r["id"]),
            "session_id": r["session_id"],
            "cwd": r["cwd"],
            "branch": r["branch"],
            "context": r["context"],
            "questions": json.loads(r["questions"]),
            "created_at": r["created_at"],
            "session_waiting": r["session_id"] in live,
        }
        for r in rows
    ]


def answer(body):
    kind = body.get("kind")
    if kind not in ("answer", "more_info"):
        raise ValueError("kind must be answer or more_info")
    resp = {"kind": kind, "answers": body.get("answers") or {}, "note": body.get("note") or ""}
    with db() as conn:
        cur = conn.execute(
            "update asks set status = 'answered', response = ?, answered_at = ? where id = ? and status = 'open'",
            (json.dumps(resp), int(time.time()), int(body["id"])),
        )
        if cur.rowcount != 1:
            raise ValueError("ask is not open")
    with cond:
        cond.notify_all()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def send(self, code, body=b"", ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        if code != 204:
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if code != 204:
            self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send(200, {"ok": True, "urls": URLS})
        elif self.path == "/api/inbox":
            self.send(200, inbox())
        elif self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "inbox.html"), "rb") as f:
                self.send(200, f.read(), "text/html; charset=utf-8")
        else:
            self.send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self.read_json()
        except ValueError:
            self.send(400, {"error": "bad json"})
            return
        if self.path.startswith("/hook/") and not self.server.loopback:
            self.send(403, {"error": "hook endpoints are loopback only"})
            return
        if self.path == "/hook/pre-ask":
            ask_id = enqueue(body)
            self.send(200, {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": DENY_REASON.format(id=ask_label(ask_id)),
                }
            })
        elif self.path == "/hook/wait":
            rows = wait_for_answers(body.get("session_id") or "unknown", self.connection)
            if not rows:
                self.send(204)
                return
            try:
                self.send(200, format_wake(rows), "text/plain; charset=utf-8")
            except OSError:
                # The hook died before reading; put the answers back.
                with db() as conn:
                    conn.executemany(
                        "update asks set status = 'answered', delivered_at = null where id = ?",
                        [(r["id"],) for r in rows],
                    )
        elif self.path == "/api/answer":
            try:
                answer(body)
            except (ValueError, KeyError) as e:
                self.send(409, {"error": str(e)})
                return
            self.send(200, {"ok": True})
        else:
            self.send(404, {"error": "not found"})


def daemonize():
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
    log = open(os.path.join(STATE_DIR, "askqd.log"), "a", buffering=1)
    devnull = open(os.devnull)
    os.dup2(devnull.fileno(), 0)
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)


def make_server(host, loopback):
    server = ThreadingHTTPServer((host, PORT), Handler)
    server.daemon_threads = True
    server.loopback = loopback
    return server


def main():
    init_db()
    servers = [make_server(HOST, True)]
    ts = tailnet_ip()
    if ts:
        try:
            servers.append(make_server(ts, False))
        except OSError as e:
            sys.stderr.write("askqd: cannot bind tailnet %s: %s\n" % (ts, e))
    URLS.extend("http://%s:%d/" % (s.server_address[0], PORT) for s in servers)
    if "--daemon" in sys.argv:
        daemonize()
    for url in URLS:
        sys.stderr.write("askqd listening on %s\n" % url)
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    servers[0].serve_forever()


if __name__ == "__main__":
    main()
