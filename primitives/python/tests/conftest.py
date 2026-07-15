"""Secure the stdlib `http` package before our sibling `http.py` can shadow it.

`python -m pytest` (run from primitives/python) puts that directory on sys.path
as '' (cwd). Our adapter module is named `http.py`, so a bare `import http.client`
— done internally by requests/httpx — would resolve `http` to our plain module
and fail with "'http' is not a package". Evict any such shadow and cache the real
stdlib http/http.client once, here, before any test module imports requests/httpx."""
import os
import sys

_PYDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # primitives/python
_saved = sys.path[:]
sys.path = [p for p in sys.path if os.path.abspath(p or os.getcwd()) != _PYDIR]
sys.modules.pop("http", None)
sys.modules.pop("http.client", None)
import http.client  # noqa: E402,F401 — stdlib; now cached in sys.modules
sys.path = _saved
