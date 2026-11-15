"""Scope checks precede every adapter. This is an allowlist, not an OS sandbox."""
from pathlib import Path
import hashlib
from urllib.parse import urlsplit


class Scope:
    def __init__(self, spec):
        if not spec.get("authorization") or not spec.get("roots"):
            raise ValueError("explicit authorization and roots required")
        self.spec = spec
        self.roots = [Path(p).resolve(strict=True) for p in spec["roots"]]
        if any(not p.is_dir() or str(p) == "/" for p in self.roots):
            raise ValueError("scope must name project directories")

    def path(self, value, exists=True):
        p = Path(value)
        if not p.is_absolute():
            p = self.roots[0] / p
        p = p.resolve(strict=exists)
        if not any(p == root or root in p.parents for root in self.roots):
            raise ValueError("path outside authorized scope")
        return p

    def adapter(self, name):
        if name not in self.spec.get("adapters", []):
            raise ValueError("adapter outside authorized scope")

    def url(self, value):
        u = urlsplit(value)
        if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password:
            raise ValueError("invalid scoped URL")
        origin = (u.scheme, u.hostname.lower(), u.port or (443 if u.scheme == "https" else 80))
        allowed = []
        for entry in self.spec.get("origins", []):
            a = urlsplit(entry)
            allowed.append((a.scheme, a.hostname, a.port or (443 if a.scheme == "https" else 80)))
        if origin not in allowed:
            raise ValueError("origin outside authorized scope")
        return value

    def fingerprint(self, args):
        """Input paths are explicit; directory contents are bounded and hashed."""
        files = {}
        for key in ("path", "before", "after", "script", "binary", "corpus", "manifest"):
            if key not in args:
                continue
            path = self.path(args[key])
            candidates = sorted(path.rglob("*")) if path.is_dir() else [path]
            if len(candidates) > 2000:
                raise ValueError("input snapshot too large")
            for file in candidates:
                if file.is_file():
                    resolved = self.path(file)
                    if resolved.stat().st_size > 32 * 1024 * 1024:
                        raise ValueError("input file too large")
                    files[str(resolved)] = hashlib.sha256(resolved.read_bytes()).hexdigest()
        return files
