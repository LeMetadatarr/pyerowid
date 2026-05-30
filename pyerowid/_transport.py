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
``PYEROWID_WAYBACK_FALLBACK``, ``PYEROWID_DELAY`` (base seconds between
requests), ``PYEROWID_BLOCK_RETRIES``, ``PYEROWID_BLOCK_BACKOFF`` (base
seconds for the exponential retry sleep on a soft block).

The parsing layer (``parse.py``) is independent of how the HTML was fetched.
"""
from __future__ import annotations

import os
import time
from typing import Any, Optional
from urllib.parse import urlencode

from unblock_requests import CloudflareSession

# Defer to shared block detection when available, fall back to erowid markers
try:
    from unblock_requests import is_blocked as _shared_is_blocked
except Exception:
    _shared_is_blocked = None

BASE = "https://erowid.org"

_ENV_PREFIX = "PYEROWID"
_VALID_MODES = {"requests", "curl_cffi", "wayback", "flaresolverr"}

# Politeness: Erowid is a small harm-reduction non-profit. Keep a base delay
# between requests and, when a block is seen, slow down adaptively rather than
# hammering. Tunable via env (PYEROWID_DELAY / _BLOCK_RETRIES / _BLOCK_BACKOFF).
_DEFAULT_DELAY = 2.0      # seconds between requests
_MAX_DELAY = 30.0         # ceiling for the adaptive back-off
_DEFAULT_BLOCK_RETRIES = 3
_DEFAULT_BLOCK_BACKOFF = 5.0   # base seconds for exponential retry sleep

# Erowid serves an IP block as an HTTP 200 body titled "403 - Blocked" rather
# than a real error status or a Cloudflare challenge, so neither raise_for_status
# nor the session's challenge heuristic catches it. Detect it by content; on a
# persistent block, recover from the Internet Archive.
_BLOCK_MARKERS = ("Vaults of Erowid : 403", "403 - Blocked")


def _is_block_page(text: str) -> bool:
    if _shared_is_blocked is not None and _shared_is_blocked(text):
        return True
    head = text[:1500]
    return any(marker in head for marker in _BLOCK_MARKERS)


def _truthy(value: Optional[str]) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_float(suffix: str, default: float) -> float:
    try:
        return float(os.environ.get(f"{_ENV_PREFIX}_{suffix}", "").strip() or default)
    except ValueError:
        return default


def _env_int(suffix: str, default: int) -> int:
    try:
        return int(os.environ.get(f"{_ENV_PREFIX}_{suffix}", "").strip() or default)
    except ValueError:
        return default


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
                 wayback_fallback: Optional[bool] = None,
                 delay: Optional[float] = None) -> None:
        if mode is not None and mode.lower() not in _VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(_VALID_MODES)} or None, got {mode!r}")
        self.mode = mode.lower() if mode else None
        self.flaresolverr_url = flaresolverr_url
        self.flaresolverr_timeout_ms = flaresolverr_timeout_ms
        self.wayback_fallback = wayback_fallback
        self._session: Optional[CloudflareSession] = None
        # politeness / adaptive back-off
        self._min_delay = delay if delay is not None else _env_float("DELAY", _DEFAULT_DELAY)
        self._block_retries = _env_int("BLOCK_RETRIES", _DEFAULT_BLOCK_RETRIES)
        self._block_backoff = _env_float("BLOCK_BACKOFF", _DEFAULT_BLOCK_BACKOFF)
        self._last_request = 0.0

    def set_delay(self, seconds: float) -> None:
        """Set the minimum delay (seconds) enforced between requests."""
        self._min_delay = max(0.0, float(seconds))

    def _throttle(self) -> None:
        wait = self._min_delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()

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

    def _fetch(self, url: str) -> str:
        r = self.session().get(url, timeout=30)
        r.raise_for_status()
        return r.text

    def get_html(self, path: str, **params: Any) -> str:
        """GET ``{BASE}{path}`` (with query *params*) and return the HTML.

        Requests are throttled to a polite base delay. If the live site answers
        with its IP-block page, the transport **backs off** — it widens the
        inter-request delay (so the rest of the run runs slower) and retries
        live with exponential sleep. Only when the block persists does it fall
        back to the latest Internet Archive snapshot, so the catalog stays
        readable from blocked exit IPs.
        """
        url = path if path.startswith("http") else f"{BASE}{path}"
        if params:
            url = f"{url}?{urlencode(params)}"

        if self._resolved_mode() == "wayback":
            self._throttle()
            return self._fetch(url)

        text = ""
        for attempt in range(self._block_retries + 1):
            self._throttle()
            text = self._fetch(url)
            if not _is_block_page(text):
                return text
            # blocked → slow every subsequent request (adaptive, capped) and
            # wait, with exponential growth, before retrying this one live.
            self._min_delay = min(_MAX_DELAY, max(self._min_delay, _DEFAULT_DELAY) * 2.0)
            if attempt < self._block_retries:
                time.sleep(self._block_backoff * (2 ** attempt))

        # persistent block → Internet Archive
        from unblock_requests import wayback_html
        snapshot = wayback_html(url)
        if snapshot and not _is_block_page(snapshot):
            return snapshot
        return text


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


def set_delay(seconds: float) -> None:
    """Set the minimum delay (seconds) between requests on the shared transport."""
    default_transport().set_delay(seconds)
