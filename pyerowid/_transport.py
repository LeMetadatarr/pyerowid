"""HTTP transport for pyerowid.

All fetches route through the org transport :mod:`unblock_requests` — its
:class:`~unblock_requests.CloudflareSession` is a drop-in ``requests.Session``
subclass that transparently picks how a page is fetched and (optionally) falls
back to the Internet Archive. Transport is configurable two ways — **constructor
kwargs** on :class:`Transport` (or the high-level :class:`pyerowid.Erowid`
client), or **environment variables** as fallback defaults. Explicit kwargs
always win over the environment.

Modes:

- ``curl_cffi`` *(default)* — live fetch with Chrome TLS impersonation when
  available (install the ``stealth`` extra), else plain ``requests``.
- ``requests`` — live fetch with plain ``requests``.
- ``wayback`` — never touch the live site; fetch the latest Internet Archive
  (Wayback Machine) snapshot. Stale but dependency-free.
- ``flaresolverr`` — fetch through a FlareSolverr proxy (a headless browser
  that clears any challenge) and return **live** HTML.

Environment fallbacks (prefix ``PYEROWID``): ``PYEROWID_TRANSPORT``,
``PYEROWID_FLARESOLVERR_URL``, ``PYEROWID_FLARESOLVERR_TIMEOUT`` (ms),
``PYEROWID_WAYBACK_FALLBACK``.

The parsing layer (``parse.py``) is independent of how the HTML was fetched.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from urllib.parse import urlencode

from unblock_requests import CloudflareSession

BASE = "https://erowid.org"

_ENV_PREFIX = "PYEROWID"
_VALID_MODES = {"requests", "curl_cffi", "wayback", "flaresolverr"}


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


class Transport:
    """Resolves *how* a page is fetched, from explicit kwargs with environment
    fallbacks. Wraps :class:`unblock_requests.CloudflareSession`.

    Args:
        mode:                 ``"requests"`` / ``"curl_cffi"`` / ``"wayback"`` /
                              ``"flaresolverr"``. ``None`` → resolve from the
                              environment, then auto (FlareSolverr if a URL is
                              configured, else curl_cffi).
        flaresolverr_url:     FlareSolverr base URL, e.g.
                              ``"http://localhost:8191"``. Setting this
                              alone selects the ``flaresolverr`` mode.
        flaresolverr_timeout_ms: per-request solve budget (default 60000).
        wayback_fallback:     fall back to the Wayback Machine on any live
                              failure. ``None`` → read the env flag.

    Example::

        from pyerowid import Transport
        t = Transport(flaresolverr_url="http://localhost:8191")
        t = Transport(mode="wayback")          # force the Internet Archive
    """

    def __init__(self, *, mode: Optional[str] = None,
                 flaresolverr_url: Optional[str] = None,
                 flaresolverr_timeout_ms: Optional[int] = None,
                 wayback_fallback: Optional[bool] = None) -> None:
        if mode is not None and mode.lower() not in _VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(_VALID_MODES)} or None, got {mode!r}")
        self.mode = mode.lower() if mode else None
        self.flaresolverr_url = flaresolverr_url
        self.flaresolverr_timeout_ms = flaresolverr_timeout_ms
        self.wayback_fallback = wayback_fallback
        self._session: Optional[CloudflareSession] = None

    # -- resolution (explicit kwarg > env > default) -----------------------

    def _fs_url(self) -> str:
        return (self.flaresolverr_url
                or os.environ.get(f"{_ENV_PREFIX}_FLARESOLVERR_URL", "").strip())

    def _resolved_mode(self) -> str:
        if self.mode:
            return self.mode
        env = os.environ.get(f"{_ENV_PREFIX}_TRANSPORT", "").strip().lower()
        if env:
            return env
        if self._fs_url():
            return "flaresolverr"
        return "curl_cffi"

    def _wayback_fallback(self) -> bool:
        if self.wayback_fallback is not None:
            return self.wayback_fallback
        return _truthy(os.environ.get(f"{_ENV_PREFIX}_WAYBACK_FALLBACK"))

    def session(self) -> CloudflareSession:
        """The lazily-built, configured :class:`CloudflareSession` (reused)."""
        if self._session is None:
            self._session = CloudflareSession(
                mode=self.mode,
                flaresolverr_url=self.flaresolverr_url,
                flaresolverr_timeout_ms=self.flaresolverr_timeout_ms,
                wayback_fallback=self.wayback_fallback,
                env_prefix=_ENV_PREFIX,
            )
        return self._session

    # -- fetch -------------------------------------------------------------

    def get_html(self, path: str, **params: Any) -> str:
        """GET ``{BASE}{path}`` (with query *params*) and return the HTML."""
        url = path if path.startswith("http") else f"{BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"
        r = self.session().get(url, timeout=30)
        r.raise_for_status()
        return r.text


_DEFAULT_TRANSPORT: Optional[Transport] = None


def default_transport() -> Transport:
    """Return the shared, environment-driven :class:`Transport`."""
    global _DEFAULT_TRANSPORT
    if _DEFAULT_TRANSPORT is None:
        _DEFAULT_TRANSPORT = Transport()
    return _DEFAULT_TRANSPORT


def get_html(path: str, **params: Any) -> str:
    """Module-level fetch using the shared env-driven transport."""
    return default_transport().get_html(path, **params)
