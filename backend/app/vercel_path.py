"""Gives Marshie's API the right web address when it runs on Vercel.

vercel.json sends every /api/... request to the one function that runs Marshie, and Vercel may hand that function only the
rewrite target (/api/index) instead of the address the browser asked for (/api/admin/login). Nothing then matches and the
Teacher login fails with "Method Not Allowed". So the rewrite also passes the real address as ?__p=admin/login, and this
middleware (switched on only on Vercel, see main.py) puts it back before FastAPI picks a route. When Vercel already passes
the real address the same value comes back, so nothing changes.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode

KEY = "__p"                                           # what vercel.json fills in with the real address
ALSO = "rest"                                         # the name vercel.json gives the captured part; Vercel may add it too
SAFE = re.compile(r"^[A-Za-z0-9._~%/\-]*$")           # an address, not a leftover ":rest*" or anything odd
TARGETS = ("/api/index", "/api/index.py", "/api", "/")


class VercelPath:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            pairs = parse_qsl((scope.get("query_string") or b"").decode("latin-1"), keep_blank_values=True)
            given = dict(reversed(pairs))             # the first value wins
            real = given.get(KEY)
            if real is None or not SAFE.match(real):
                # No usable ?__p=. Fall back to the captured part only when the function was handed the rewrite target.
                alt = given.get(ALSO)
                real = alt if alt and SAFE.match(alt) and scope.get("path", "").rstrip("/") in TARGETS else None
            if real is not None:
                rest = [(k, v) for k, v in pairs if k not in (KEY, ALSO)]
                path = "/api/" + real.strip("/")
                scope = {**scope, "path": path, "raw_path": path.encode("latin-1", "ignore"),
                         "query_string": urlencode(rest).encode("latin-1")}
        await self.app(scope, receive, send)
