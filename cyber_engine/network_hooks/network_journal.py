#!/usr/bin/env python3
"""Local metadata journal for Claude Code tool hooks; Python stdlib only.

Never execute tool input, read transcripts, or save raw commands/responses.
This is an intent journal, not a packet capture or a permission gate.
"""

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import stat
import sys
from urllib.parse import urlsplit


EVENTS = {"PreToolUse", "PostToolUse", "PostToolUseFailure"}
NETWORK_TOOLS = {
    "curl", "wget", "http", "https", "httpie", "ssh", "scp", "sftp",
    "rsync", "dig", "host", "nslookup", "ping", "ping6", "traceroute",
    "nmap", "nc", "netcat", "socat", "openssl", "ffuf", "httpx",
    "nikto", "nuclei", "sqlmap", "gobuster", "feroxbuster", "masscan",
}
URL_RE = re.compile(r"(?:https?|wss?|ftp|ssh|git)://[^\s\"'<>`]+", re.I)
MCP_NET_RE = re.compile(r"browser|chrome|firecrawl|searx|fetch|search|http|navigate|network|darknet", re.I)
PRIVATE_OPTIONS = {
    "-H", "--header", "--proxy-header", "-d", "--data", "--data-raw",
    "--data-binary", "--data-urlencode", "--json", "-F", "--form",
    "--form-string", "-u", "--user", "--proxy-user", "--oauth2-bearer",
    "-b", "--cookie", "-e", "--referer", "--password", "--post-data",
}
MAX_INPUT = 4 * 1024 * 1024
MAX_LOG = 5 * 1024 * 1024
BACKUPS = 3
DEFAULT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs" / "network"


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def input_strings(value, depth=0):
    """Only inspect request destinations, never headers, bodies, or prompts."""
    if depth > 6:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"url", "uri", "target_url", "endpoint", "website", "urls"}:
                if isinstance(child, str):
                    yield child
                elif isinstance(child, list):
                    yield from (x for x in child[:64] if isinstance(x, str))
            elif key in {"requests", "open", "arguments", "params", "input"}:
                yield from input_strings(child, depth + 1)
    elif isinstance(value, list):
        for child in value[:64]:
            yield from input_strings(child, depth + 1)


def origins(texts):
    result = set()
    for text in texts:
        for match in URL_RE.finditer(text):
            try:
                parts = urlsplit(match.group(0).rstrip(");,]}"))
                host = parts.hostname
                if not host or len(host) > 253 or not re.fullmatch(r"[A-Za-z0-9.:%_-]+", host):
                    continue
                # Drop IPv6 scope identifiers as well as userinfo, path, query, fragment.
                host = host.split("%", 1)[0].lower()
                host = "[" + host + "]" if ":" in host else host
                port = parts.port
                result.add(parts.scheme.lower() + "://" + host + (":" + str(port) if port else ""))
                if len(result) >= 64:
                    return sorted(result)
            except ValueError:
                continue
    return sorted(result)


def classify(tool, data):
    if not isinstance(data, dict):
        return None
    if tool in {"Bash", "PowerShell"}:
        command = data.get("command", "")
        if not isinstance(command, str):
            return None
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        names = {Path(token).name.lower() for token in tokens}
        hints = sorted(names & NETWORK_TOOLS)
        if "git" in names and names & {"clone", "fetch", "pull", "push", "ls-remote"}:
            hints.append("git")
        if names & {"pip", "pip3", "npm", "pnpm", "yarn", "brew", "cargo", "go", "uv"}:
            if names & {"install", "add", "update", "upgrade", "download", "fetch", "get"}:
                hints.append("package-manager")
        # Discard sensitive option arguments before finding URL origins.
        public_tokens = []
        skip = False
        for token in tokens:
            if skip:
                skip = False
                continue
            if token in PRIVATE_OPTIONS:
                skip = True
                continue
            if any(token.startswith(option + "=") for option in PRIVATE_OPTIONS):
                continue
            if any(len(option) == 2 and token.startswith(option) and token != option
                   for option in PRIVATE_OPTIONS):
                continue
            public_tokens.append(token)
        endpoints = origins(public_tokens)
        if not hints and not endpoints:
            return None
        return "shell_network_hint", hints, endpoints, digest(command)
    endpoints = origins(input_strings(data))
    if tool in {"WebFetch", "WebSearch"}:
        return "web_tool", [], endpoints, None
    if tool.startswith("mcp__") and (endpoints or MCP_NET_RE.search(tool)):
        return "mcp_network_hint", [], endpoints, None
    return None


def make_record(payload):
    if not isinstance(payload, dict) or payload.get("hook_event_name") not in EVENTS:
        return None
    tool = payload.get("tool_name")
    if not isinstance(tool, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,200}", tool):
        return None
    identified = classify(tool, payload.get("tool_input", {}))
    if identified is None:
        return None
    kind, hints, endpoints, command_hash = identified
    event = payload["hook_event_name"]
    record = {
        "schema": 1,
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
        "tool": tool,
        "classification": kind,
        "network_observed": False,
        "origins": endpoints,
        "program_hints": hints,
        "outcome": {
            "PreToolUse": "requested",
            "PostToolUse": "tool_returned",
            "PostToolUseFailure": "tool_failed",
        }[event],
    }
    for key in ("session_id", "tool_use_id", "cwd"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            record[key + "_sha256"] = digest(value)
    if command_hash:
        record["command_sha256"] = command_hash
    duration = payload.get("duration_ms")
    if type(duration) in (int, float) and math.isfinite(duration) and duration >= 0:
        record["duration_ms"] = duration
    if type(payload.get("is_interrupt")) is bool:
        record["is_interrupt"] = payload["is_interrupt"]
    response = payload.get("tool_response")
    if isinstance(response, dict):
        for key in ("exit_code", "exitCode"):
            if type(response.get(key)) is int:
                record["exit_code"] = response[key]
                break
    if event == "PostToolUseFailure" and "exit_code" not in record:
        error = payload.get("error")
        if isinstance(error, str):
            match = re.match(r"\AExit code (-?\d+)\b", error)
            if match:
                record["exit_code"] = int(match[1])
    return record


def private_open(path, flags):
    fd = os.open(path, flags | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
        os.close(fd)
        raise OSError("journal destination is not a private regular file")
    os.fchmod(fd, 0o600)
    return fd


def append_record(record, directory, max_bytes=MAX_LOG):
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if directory.is_symlink() or directory.stat().st_uid != os.getuid():
        raise OSError("invalid journal directory")
    directory.chmod(0o700)
    encoded = (json.dumps(record, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    with os.fdopen(private_open(directory / ".lock", os.O_RDWR), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = directory / "network.jsonl"
        with os.fdopen(private_open(target, os.O_WRONLY | os.O_APPEND), "ab") as stream:
            size = os.fstat(stream.fileno()).st_size
            if size + len(encoded) <= max_bytes or size == 0:
                stream.write(encoded)
                return
        for number in range(1, BACKUPS + 1):
            candidate = directory / ("network.jsonl." + str(number))
            if candidate.is_symlink():
                raise OSError("invalid rotation destination")
        for number in range(BACKUPS - 1, 0, -1):
            old = directory / ("network.jsonl." + str(number))
            if old.exists():
                os.replace(old, directory / ("network.jsonl." + str(number + 1)))
        os.replace(target, directory / "network.jsonl.1")
        with os.fdopen(private_open(target, os.O_WRONLY | os.O_APPEND), "ab") as stream:
            stream.write(encoded)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR,
                        help="Local destination; never taken from hook input")
    args = parser.parse_args()
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("hook input exceeds limit")
        payload = json.loads(raw)
        record = make_record(payload)
        if record is not None:
            append_record(record, args.log_dir)
    except Exception as exc:
        # Do not include exception messages: JSON/parser errors can contain secrets.
        print("network-journal: evenement non journalise (" + type(exc).__name__ + ")", file=sys.stderr)
        return 1  # Claude Code non-blocking error; never return a permission decision.
    return 0


if __name__ == "__main__":
    sys.exit(main())
