"""Transport configuration tests (kwargs / env resolution, no network)."""
from pyerowid import _transport as t


def test_truthy():
    assert t._truthy("1") and t._truthy("true") and t._truthy("YES")
    assert not t._truthy("") and not t._truthy("0") and not t._truthy(None)


def _clear_env(monkeypatch):
    for k in ("PYEROWID_TRANSPORT", "PYEROWID_FLARESOLVERR_URL",
              "PYEROWID_WAYBACK_FALLBACK"):
        monkeypatch.delenv(k, raising=False)


def test_transport_mode_from_kwargs(monkeypatch):
    _clear_env(monkeypatch)
    assert t.Transport()._resolved_mode() == "curl_cffi"
    assert t.Transport(mode="wayback")._resolved_mode() == "wayback"
    assert t.Transport(flaresolverr_url="http://x:8191")._resolved_mode() == "flaresolverr"


def test_transport_kwarg_beats_env(monkeypatch):
    monkeypatch.setenv("PYEROWID_TRANSPORT", "requests")
    assert t.Transport(mode="wayback")._resolved_mode() == "wayback"   # explicit wins
    assert t.Transport()._resolved_mode() == "requests"                # falls back to env


def test_transport_rejects_bad_mode():
    import pytest
    with pytest.raises(ValueError):
        t.Transport(mode="nonsense")


def test_transport_base_is_erowid():
    assert t.BASE == "https://erowid.org"


def test_session_is_cloudflare_session(monkeypatch):
    _clear_env(monkeypatch)
    from unblock_requests import CloudflareSession
    s = t.Transport(mode="wayback").session()
    assert isinstance(s, CloudflareSession)
    assert s.env_prefix == "PYEROWID"


def test_client_kwargs(monkeypatch):
    _clear_env(monkeypatch)
    import pyerowid
    assert pyerowid.Erowid(wayback=True).transport._resolved_mode() == "wayback"
    c = pyerowid.Erowid(flaresolverr_url="http://localhost:8191")
    assert c.transport._resolved_mode() == "flaresolverr"
    assert c.transport._fs_url() == "http://localhost:8191"


def test_block_page_detection():
    from pyerowid._transport import _is_block_page
    block = ('<html><head><title>The Vaults of Erowid : 403 - Blocked'
             '</title></head><body>403 Forbidden</body></html>')
    assert _is_block_page(block) is True
    assert _is_block_page('<html><body><a href="/pharms/x/x.shtml">x</a></body></html>') is False


class _FakeResp:
    def __init__(self, text): self.text = text
    def raise_for_status(self): pass


class _FakeSession:
    """Returns the block page for the first N calls, then a real page."""
    def __init__(self, block_times, good="<html>real erowid content</html>"):
        self.block_times = block_times
        self.good = good
        self.calls = 0
    def get(self, url, **kw):
        self.calls += 1
        if self.calls <= self.block_times:
            return _FakeResp("<html><title>The Vaults of Erowid : 403 - Blocked</title></html>")
        return _FakeResp(self.good)


def test_softblock_backoff_retries_then_recovers(monkeypatch):
    monkeypatch.setattr(t.time, "sleep", lambda *_: None)  # no real waiting
    tr = t.Transport(mode="curl_cffi", delay=0.0)
    tr._block_backoff = 0.01
    fake = _FakeSession(block_times=2)            # blocked twice, then OK
    monkeypatch.setattr(tr, "session", lambda: fake)
    base = tr._min_delay
    html = tr.get_html("/pharms/")
    assert "real erowid content" in html          # retry recovered live
    assert fake.calls == 3                          # 2 blocks + 1 success
    assert tr._min_delay > base                      # backed off the request rate


def test_softblock_persists_falls_back_to_wayback(monkeypatch):
    monkeypatch.setattr(t.time, "sleep", lambda *_: None)
    tr = t.Transport(mode="curl_cffi", delay=0.0)
    tr._block_retries = 2
    tr._block_backoff = 0.01
    fake = _FakeSession(block_times=99)            # always blocked
    monkeypatch.setattr(tr, "session", lambda: fake)
    import unblock_requests
    monkeypatch.setattr(unblock_requests, "wayback_html",
                        lambda url, **kw: "<html>archived erowid snapshot</html>")
    html = tr.get_html("/pharms/")
    assert "archived erowid snapshot" in html       # fell back to Wayback
    assert fake.calls == 3                            # retries+1 live attempts
