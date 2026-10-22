#!/usr/bin/env python3
"""ask-queue daemon: queues AskUserQuestion calls from many sessions, serves
the inbox page, and hands answers back to waiting Stop hooks.

Standard library only; written for the macOS system python3 (3.9).

Endpoints:
  GET  /health             liveness probe used by the hooks
  POST /hook/pre-ask       PreToolUse hook input in, hook output JSON out
  POST /hook/wait          Stop hook input in; long-polls for answers.
                           200 + wake text; 202 poll again; 204 when the session
                           has no open asks; 409 when a newer waiter for the
                           same session took over
  GET  /                   inbox page
  GET  /api/inbox          open asks as JSON
  POST /api/answer         {"id", "kind": "answer"|"more_info", "answers", "note"}

Listens on 127.0.0.1 always, and also on this machine's tailnet address when
Tailscale is up, so the inbox is reachable from other tailnet devices and
sessions on other tailnet machines can use this daemon as their hub. On the
tailnet listener, /hook/* accepts only peers that `tailscale whois` reports as
owned by this machine's Tailscale user.

Events and errors go to <state>/ask-queue.log (shared with the client, role
"askqd"). askqd.log keeps the raw stderr: the HTTP access log and anything
that escapes the handlers.

/hook/wait returns 202 every WAIT_SLICE_SECONDS with no news, so long-polls
over the network never sit idle for hours; the client polls again.
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
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from askq_client import TAILSCALE_CLIS, deny_output, git_branch, log, session_context, short

HOST = "127.0.0.1"
PORT = int(os.environ.get("ASKQ_PORT", "7788"))
STATE_DIR = os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")), "ask-queue")
DB_PATH = os.path.join(STATE_DIR, "queue.db")
HERE = os.path.dirname(os.path.abspath(__file__))

# Inbox URLs this daemon serves, loopback first; filled in by main().
URLS = []

# Max time one /hook/wait request holds before returning 202 (poll again).
WAIT_SLICE_SECONDS = int(os.environ.get("ASKQ_WAIT_SLICE", "600"))

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
# session_id -> last time a hook request from that session started or ended.
# In memory only: empty after a restart until each session's hook reconnects.
last_seen = {}


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
        cols = {r[1] for r in conn.execute("pragma table_info(asks)")}
        if "host" not in cols:
            conn.execute("alter table asks add column host text")
        if "client_ref" not in cols:
            conn.execute("alter table asks add column client_ref text")
            conn.execute("create unique index if not exists asks_client_ref on asks (client_ref)")


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


_whois_cache = {}


def tailscale_json(command, *args):
    """Run `tailscale <command> --json <args>` and return the parsed output, or None.
    --json goes before positional args: the CLI stops parsing flags at the
    first one ("whois <ip> --json" fails with "too many arguments")."""
    for cli in TAILSCALE_CLIS:
        path = shutil.which(cli)
        if not path:
            continue
        out = None
        try:
            out = subprocess.run([path, command, "--json"] + list(args), capture_output=True, text=True, timeout=5)
            return json.loads(out.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError) as e:
            log("askqd", "tailscale-cli-failed", cmd=command, args=" ".join(args), error=e,
                stderr=out.stderr[:200] if out else "")
            continue
    return None


def tailnet_user_id(ip=None):
    """Tailscale user id that owns `ip`, or this machine's user when ip is None."""
    try:
        if ip is None:
            return tailscale_json("status", "--self")["Self"]["UserID"]
        return tailscale_json("whois", ip)["UserProfile"]["ID"]
    except (TypeError, KeyError):
        return None


def same_tailnet_user(ip):
    """True when the peer at `ip` belongs to the same Tailscale user as this machine.
    Results are cached for 10 minutes per IP."""
    hit = _whois_cache.get(ip)
    if hit and hit[1] > time.time():
        return hit[0]
    me = tailnet_user_id()
    peer = tailnet_user_id(ip)
    ok = me is not None and peer == me
    _whois_cache[ip] = (ok, time.time() + 600)
    log("askqd", "whois", ip=ip, peer_user=peer, hub_user=me, allowed=ok)
    return ok


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
    except OSError as e:
        log("askqd", "notify-failed", cmd=cmd[0], error=e)


def ask_label(ask_id):
    return "Q-{}".format(ask_id)


def enqueue(hook_input):
    """Store one AskUserQuestion call; return its id. The client sends context,
    branch, and host; older hook inputs without them get them computed here.
    A repeated client_ref (a spool retry whose response was lost) returns the
    existing id instead of a duplicate."""
    tool_input = hook_input.get("tool_input") or {}
    questions = tool_input.get("questions") or []
    cwd = hook_input.get("cwd")
    ref = hook_input.get("client_ref")
    with db() as conn:
        if ref:
            row = conn.execute("select id from asks where client_ref = ?", (ref,)).fetchone()
            if row:
                log("askqd", "enqueue-duplicate", id=ask_label(row["id"]), ref=ref)
                return row["id"]
        cur = conn.execute(
            "insert into asks (session_id, cwd, branch, context, host, client_ref, questions, created_at)"
            " values (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                hook_input.get("session_id") or "unknown",
                cwd,
                hook_input["branch"] if "branch" in hook_input else git_branch(cwd),
                hook_input["context"] if "context" in hook_input else session_context(hook_input.get("transcript_path")),
                hook_input.get("host"),
                ref,
                json.dumps(questions),
                int(time.time()),
            ),
        )
        ask_id = cur.lastrowid
    log("askqd", "enqueued", id=ask_label(ask_id), session=short(hook_input.get("session_id")),
        host=hook_input.get("host"), cwd=cwd, questions=len(questions))
    first = questions[0].get("question", "") if questions else ""
    repo = os.path.basename(cwd) if cwd else "?"
    where = "{} on {}".format(repo, hook_input["host"]) if hook_input.get("host") else repo
    notify("ask-queue: {} ({})".format(ask_label(ask_id), where), first)
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
    rows (marked delivered), None when the session has no open asks or the
    client hung up, "superseded" when a newer waiter took over, or "again"
    after WAIT_SLICE_SECONDS so the client re-polls."""
    global waiter_seq
    with cond:
        waiter_seq += 1
        token = waiter_seq
        waiters[session_id] = token
        deadline = time.time() + WAIT_SLICE_SECONDS
        try:
            while True:
                if waiters.get(session_id) != token:
                    log("askqd", "wait-superseded", session=short(session_id))
                    return "superseded"
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
                if not pending:
                    return None
                if peer_closed(sock):
                    log("askqd", "wait-peer-closed", session=short(session_id))
                    return None
                if time.time() > deadline:
                    return "again"
                cond.wait(timeout=15)
        finally:
            last_seen[session_id] = time.time()
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
            "host": r["host"],
            "context": r["context"],
            "questions": json.loads(r["questions"]),
            "created_at": r["created_at"],
            "session_waiting": r["session_id"] in live,
            "last_seen": int(last_seen[r["session_id"]]) if r["session_id"] in last_seen else None,
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
    log("askqd", "answered", id=ask_label(int(body["id"])), kind=kind)
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
        self.guarded(self.get)

    def do_POST(self):
        self.guarded(self.post)

    def guarded(self, fn):
        """Run one request; log any exception with its traceback and try a 500."""
        try:
            fn()
        except (BrokenPipeError, ConnectionResetError) as e:
            log("askqd", "client-gone", method=self.command, path=self.path,
                peer=self.client_address[0], error=repr(e))
        except Exception as e:
            log("askqd", "request-crash", method=self.command, path=self.path,
                peer=self.client_address[0], error=repr(e), trace=traceback.format_exc())
            try:
                self.send(500, {"error": repr(e)})
            except OSError:
                pass

    def get(self):
        if self.path == "/health":
            self.send(200, {"ok": True, "urls": URLS})
        elif self.path == "/api/inbox":
            self.send(200, inbox())
        elif self.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "inbox.html"), "rb") as f:
                self.send(200, f.read(), "text/html; charset=utf-8")
        else:
            self.send(404, {"error": "not found"})

    def post(self):
        try:
            body = self.read_json()
        except ValueError:
            self.send(400, {"error": "bad json"})
            return
        if self.path.startswith("/hook/") and not self.server.loopback and not same_tailnet_user(self.client_address[0]):
            log("askqd", "hook-forbidden", path=self.path, peer=self.client_address[0])
            self.send(403, {"error": "hook endpoints need loopback or a peer owned by this tailnet user"})
            return
        if self.path.startswith("/hook/"):
            last_seen[body.get("session_id") or "unknown"] = time.time()
        if self.path == "/hook/pre-ask":
            ask_id = enqueue(body)
            self.send(200, deny_output(ask_label(ask_id)))
        elif self.path == "/hook/wait":
            rows = wait_for_answers(body.get("session_id") or "unknown", self.connection)
            if rows == "again":
                self.send(202, {"again": True})
                return
            if rows == "superseded":
                # Not 204: the client must keep its outstanding marker, since
                # the session's asks are still open.
                self.send(409, {"superseded": True})
                return
            if not rows:
                self.send(204)
                return
            ids = ",".join(ask_label(r["id"]) for r in rows)
            try:
                self.send(200, format_wake(rows), "text/plain; charset=utf-8")
                log("askqd", "delivered", ids=ids, session=short(body.get("session_id")))
            except OSError as e:
                # The hook died before reading; put the answers back.
                log("askqd", "deliver-failed-requeued", ids=ids, session=short(body.get("session_id")), error=e)
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
    try:
        init_db()
        servers = [make_server(HOST, True)]
    except Exception as e:
        log("askqd", "start-failed", port=PORT, db=DB_PATH, error=repr(e), trace=traceback.format_exc())
        raise
    ts = tailnet_ip()
    if ts:
        try:
            servers.append(make_server(ts, False))
        except OSError as e:
            sys.stderr.write("askqd: cannot bind tailnet %s: %s\n" % (ts, e))
            log("askqd", "tailnet-bind-failed", ip=ts, port=PORT, error=e)
    URLS.extend("http://%s:%d/" % (s.server_address[0], PORT) for s in servers)
    if "--daemon" in sys.argv:
        daemonize()
    for url in URLS:
        sys.stderr.write("askqd listening on %s\n" % url)
    log("askqd", "started", python=sys.executable, urls=" ".join(URLS), code=HERE)
    for s in servers[1:]:
        threading.Thread(target=s.serve_forever, daemon=True).start()
    servers[0].serve_forever()


if __name__ == "__main__":
    main()
