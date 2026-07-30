"""Example 07 — configuring the transport.

All HTTP routes through the org transport (unblock_requests' CloudflareSession).
Pick how pages are fetched with constructor kwargs on the ``Erowid`` client or
with environment variables (``PYEROWID_TRANSPORT`` etc.).

Run::

    python examples/07_transport.py
"""
import pyerowid


def main() -> None:
    # 1. Solve any challenge live via a FlareSolverr instance.
    live = pyerowid.Erowid(flaresolverr_url="http://localhost:8191")
    print("transport:", live.transport._resolved_mode())

    # 2. Force the Internet Archive explicitly — no live request.
    archived = pyerowid.Erowid(wayback=True)
    print("transport:", archived.transport._resolved_mode())

    # 3. Try live first, fall back to the archive on failure.
    resilient = pyerowid.Erowid(wayback_fallback=True)
    print("transport:", resilient.transport._resolved_mode(), "(+ wayback fallback)")


if __name__ == "__main__":
    main()
