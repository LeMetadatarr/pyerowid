# Advanced usage

## Transport

Every fetch routes through the org HTTP transport
[`unblock_requests`](../../../utils/unblock_requests). Its `CloudflareSession`
is a drop-in `requests.Session` subclass that picks how a page is fetched and
can fall back to the Internet Archive. `pyerowid._transport.Transport` wraps it
with the `PYEROWID_*` env namespace and `BASE = https://erowid.org`.

### Transport modes

`PYEROWID_TRANSPORT` selects how pages are fetched:

| Value | Behavior |
|---|---|
| *(unset)* / `curl_cffi` | Live fetch with Chrome TLS impersonation. This is the default and needs the `stealth` extra. |
| `requests` | Live fetch with plain `requests`. |
| `wayback` | **Do not touch the live site.** Fetch the latest snapshot from the Internet Archive. |
| `flaresolverr` | Fetch through a FlareSolverr proxy (a headless browser) and return **live** HTML. |

```bash
export PYEROWID_TRANSPORT=requests   # or: curl_cffi (default), wayback, flaresolverr
```

### Configure in code (no env vars)

Every knob is also a constructor kwarg on the `Erowid` client (and on
`Transport`). Explicit kwargs always win over the environment:

```python
import pyerowid

# FlareSolverr (live): setting the URL selects the flaresolverr transport
client = pyerowid.Erowid(flaresolverr_url="http://localhost:8191")

# Force the Internet Archive
archived = pyerowid.Erowid(wayback=True)            # == transport="wayback"

# Try live first, fall back to the archive
resilient = pyerowid.Erowid(wayback_fallback=True)

# Or build a Transport yourself and pass it to the functions
from pyerowid import Transport
t = Transport(mode="flaresolverr", flaresolverr_url="http://localhost:8191",
              flaresolverr_timeout_ms=90000)
pyerowid.get_experience(1, transport=t)
```

Env fallbacks (prefix `PYEROWID`): `PYEROWID_TRANSPORT`,
`PYEROWID_FLARESOLVERR_URL`, `PYEROWID_FLARESOLVERR_TIMEOUT` (ms),
`PYEROWID_WAYBACK_FALLBACK`.

## Politeness

Erowid is a small, donation-funded harm-reduction nonprofit. Be a good guest.
Reuse one session (the default transport, or one `Erowid` client) and throttle:

```python
import time, pyerowid
client = pyerowid.Erowid()
for exp_id in range(1, 50):
    exp = client.get_experience(exp_id)
    if exp:
        ...
    time.sleep(1)
```

The corpus dumper (`pyerowid.dataset`) already reuses one transport and sleeps
`delay` seconds between fetches. See [dataset.md](dataset.md).

## Parsing offline

The functions in `pyerowid.parse` take a raw HTML string and need no network,
so you can fetch the HTML however you like and parse it:

```python
from pyerowid.parse import parse_experience, parse_search, parse_substance_list, parse_page
exp     = parse_experience(open("exp.html").read(), 1)
reports = parse_search(open("search.html").read())
pharms  = parse_substance_list(open("pharms.html").read(), "https://erowid.org/pharms/")
info    = parse_page(open("acetaminophen.html").read(),
                     "https://erowid.org/pharms/acetaminophen/acetaminophen.shtml")
```

---
[← API reference](api.md) · [Home](../README.md) · [Dataset →](dataset.md)
