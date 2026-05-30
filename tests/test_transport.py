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
