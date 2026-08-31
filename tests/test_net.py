"""The outbound-network layer: pacing, thread safety, retries.

`PacingGate` takes `clock` and `sleeper` as parameters precisely so a test can
prove an interval without a suite that really sleeps three seconds per request.
Everything here drives a fake clock; nothing here touches a socket.
"""

from __future__ import annotations

import threading

import httpx
import pytest

# `from conftest import ...`, not `tests.conftest`: a transitive dependency ships
# a top-level `tests` package that shadows this repo's.
from conftest import offline_settings
from just_dna_enricher.net import PacingGate
from tenacity import Future, RetryCallState

from just_module_creator import net
from just_module_creator.net import (
    HttpService,
    ServiceGate,
    ServiceUnavailable,
    _retry_after_seconds,
    _Throttled,
    _wait_honouring_retry_after,
    build_services,
)
from just_module_creator.settings import Settings


class FakeClock:
    """A monotonic clock that only advances when something sleeps on it."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_the_gate_spaces_requests_by_its_interval() -> None:
    clock = FakeClock()
    gate = ServiceGate(interval=3.0, clock=clock, sleeper=clock.sleep)

    for _ in range(3):
        gate.wait()

    # The first call is free; each later one waits the full interval, because
    # nothing else advanced the clock in between.
    assert clock.sleeps == [3.0, 3.0]
    assert clock.now == pytest.approx(6.0)


def test_the_gate_does_not_sleep_when_the_interval_already_elapsed() -> None:
    clock = FakeClock()
    gate = ServiceGate(interval=1.0, clock=clock, sleeper=clock.sleep)

    gate.wait()
    clock.now += 5.0  # the caller spent five seconds doing real work
    gate.wait()

    assert clock.sleeps == []


def _peak_overlap(gate: PacingGate, workers: int = 4) -> int:
    """How many threads are ever inside `wait()` at once.

    A pacing gate that spaces requests must release them one at a time — if two
    threads are sleeping out the same interval concurrently, they resume together
    and two requests hit the wire at the same instant, which is exactly the 3/s
    budget becoming 6/s.
    """
    inside = 0
    peak = 0
    bookkeeping = threading.Lock()
    start = threading.Barrier(workers)

    def sleeper(seconds: float) -> None:
        nonlocal inside, peak
        with bookkeeping:
            inside += 1
            peak = max(peak, inside)
        # Long enough that a genuinely concurrent pair overlaps here.
        threading.Event().wait(0.02)
        with bookkeeping:
            inside -= 1

    gate.sleeper = sleeper
    gate.wait()  # prime `last` so every worker races the same elapsed check

    def worker() -> None:
        start.wait()
        gate.wait()

    threads = [threading.Thread(target=worker) for _ in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return peak


def test_the_unlocked_gate_lets_requests_overlap_and_ours_does_not() -> None:
    """The defect `ServiceGate` exists for, demonstrated on the base class first.

    Every tool here runs its blocking work through `anyio.to_thread.run_sync`, so
    several worker threads sharing one gate is the real arrangement, not a
    contrived one. Upstream's CLI is single-threaded, which is why this never bit
    them and does bite us.
    """
    # A clock frozen in the past: the interval has provably not elapsed, so every
    # worker must be paced.
    plain = PacingGate(interval=10.0, clock=lambda: 0.0)
    assert _peak_overlap(plain) > 1, "expected the unlocked gate to release concurrently"

    guarded = ServiceGate(interval=10.0, clock=lambda: 0.0)
    assert _peak_overlap(guarded) == 1, "ServiceGate must serialize the wait"


def test_retry_after_is_honoured_and_capped() -> None:
    def response(value: str | None) -> httpx.Response:
        headers = {"Retry-After": value} if value is not None else {}
        return httpx.Response(429, headers=headers)

    assert _retry_after_seconds(response("7")) == 7.0
    # A service asking us to wait ten minutes is telling us to go away; blocking a
    # tool call that long is worse than reporting the source could not answer.
    assert _retry_after_seconds(response("600")) == 30.0
    assert _retry_after_seconds(response(None)) is None
    # The HTTP-date form is legal but rare here; ignoring it falls back to our own
    # backoff, which is never *less* polite than what was asked.
    assert _retry_after_seconds(response("Wed, 21 Oct 2026 07:28:00 GMT")) is None


def test_the_servers_retry_after_beats_our_backoff_curve() -> None:
    """A service that says when to come back knows better than an exponential guess.

    Pure function, so the assertion costs nothing and needs no sleeping.
    """
    state = RetryCallState(None, None, (), {})  # type: ignore[arg-type]
    state.outcome = Future.construct(
        1, _Throttled(httpx.Response(429, headers={"Retry-After": "7"})), True
    )
    assert _wait_honouring_retry_after(state) == 7.0

    # No header: fall back to jitter, which is bounded but not a fixed number.
    state.outcome = Future.construct(1, _Throttled(httpx.Response(503)), True)
    assert 0 <= _wait_honouring_retry_after(state) <= 10.0


def _service(handler: httpx.MockTransport, monkeypatch) -> HttpService:
    # Zero the backoff curve so the retry tests do not really sleep. The pacing
    # gate is separately proven above; what these assert is control flow.
    monkeypatch.setattr(net, "_JITTER", lambda _state: 0.0)
    gate = ServiceGate(interval=0.0)
    service = HttpService(name="fake", base_url="https://example.invalid", gate=gate)
    service._client = httpx.Client(transport=handler, base_url="https://example.invalid")
    return service


def test_a_rate_limited_service_retries_then_reports_unavailable(monkeypatch) -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "0"})

    service = _service(httpx.MockTransport(handler), monkeypatch)

    with pytest.raises(ServiceUnavailable) as excinfo:
        service.get("search", {"q": "lactase"})

    assert attempts["n"] > 1, "a 429 must be retried"
    assert excinfo.value.rate_limited is True
    assert "429" in excinfo.value.reason


def test_a_client_error_is_not_retried(monkeypatch) -> None:
    """Repeating a request the server called malformed only spends someone's budget."""
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(400)

    service = _service(httpx.MockTransport(handler), monkeypatch)

    with pytest.raises(ServiceUnavailable) as excinfo:
        service.get("search")

    assert attempts["n"] == 1
    assert excinfo.value.rate_limited is False
    assert "400" in excinfo.value.reason


def test_a_transient_failure_recovers_on_the_second_attempt(monkeypatch) -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    service = _service(httpx.MockTransport(handler), monkeypatch)

    assert service.get("search").json() == {"ok": True}
    assert attempts["n"] == 2


def test_a_transport_error_becomes_unavailable_not_a_negative_answer(monkeypatch) -> None:
    """The distinction the whole result model rests on: failed != found nothing."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route to host")

    service = _service(httpx.MockTransport(handler), monkeypatch)

    with pytest.raises(ServiceUnavailable) as excinfo:
        service.get("search")

    assert "ConnectError" in excinfo.value.reason


def test_building_services_opens_no_connection() -> None:
    """`build_server` calls this, so it must stay safe to construct at import time."""
    services = build_services(offline_settings())
    try:
        assert services.lookup_clients.eutils is not None
        # The NCBI gate is shared with our own PubMed service on purpose: two
        # independently correct 3/s clients against one IP make a 6/s client.
        assert services.lookup_clients.eutils.gate is services.ncbi_gate
        assert services.ncbi_gate.interval > 0
    finally:
        services.close()


def test_a_contact_address_is_never_invented(monkeypatch) -> None:
    """The rule that survived gaining a default.

    This used to assert `contact_email() is None` with nothing configured. A
    project default now fills that slot, so the invariant is narrower and still
    worth pinning: the resolved contact is either something an operator configured
    or the *documented constant* — never a value synthesised from anything else.
    That is what forbids a future "helpful" default built from a hostname, a git
    `user.email` or a registry account name, which is the thing that would really
    misattribute traffic to a real person.

    `setenv(..., "")` rather than `delenv`: `load_dotenv(override=False)` skips a
    key that is merely present, so a deleted var can be refilled from a developer's
    `.env` and the test would stop meaning "no contact address".
    """
    monkeypatch.setenv("JUST_DNA_CONTACT_EMAIL", "")
    monkeypatch.setenv("NCBI_API_KEY", "")
    services = build_services(Settings(_env_file=None, user_email=None))  # type: ignore[call-arg]
    try:
        assert services.contact_email() == net.DEFAULT_CONTACT_EMAIL
        # Pinned as a literal on purpose: a derived default would pass an
        # equality-against-the-constant check while still being synthesised.
        assert net.DEFAULT_CONTACT_EMAIL == "contact@example.org"
    finally:
        services.close()


# --------------------------------------------------------------------------- #
# The polite-pool contact chain: JMC_USER_EMAIL -> JUST_DNA_CONTACT_EMAIL ->
# DEFAULT_CONTACT_EMAIL. Every "unset" below is `setenv(VAR, "")` rather than
# `delenv`, because a key that is merely *present* is skipped by
# `load_dotenv(override=False)` — so an empty value is what "no value" has to
# mean here, and `delenv` would leave a developer's real environment showing
# through.
# --------------------------------------------------------------------------- #


def _blank_contact_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUST_DNA_CONTACT_EMAIL", "")
    monkeypatch.setenv("NCBI_API_KEY", "")


def test_our_variable_wins_over_the_enrichers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUST_DNA_CONTACT_EMAIL", "upstream@example.org")
    services = build_services(offline_settings(user_email="mine@example.org"))
    assert services.contact_email() == "mine@example.org"


def test_the_enrichers_variable_is_inherited_not_reimplemented(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Step 2 must come from `EutilsSettings.__post_init__`, not from our own read.

    Proven by construction: we pass `email=None` when ours is unset, so the only
    thing that can supply this value is upstream's own resolution.
    """
    monkeypatch.setenv("JUST_DNA_CONTACT_EMAIL", "upstream@example.org")
    services = build_services(offline_settings(user_email=None))
    assert services.contact_email() == "upstream@example.org"
    assert services.eutils_settings.email == "upstream@example.org"


def test_an_empty_user_email_is_unset_not_a_contact(monkeypatch: pytest.MonkeyPatch) -> None:
    """`JMC_USER_EMAIL=""` means "I set nothing", and must not become the contact."""
    _blank_contact_env(monkeypatch)
    services = build_services(offline_settings(user_email="   "))
    assert services.contact_email() == net.DEFAULT_CONTACT_EMAIL


def test_the_contact_is_never_none_so_unpaywall_is_always_askable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reason the `if not email:` guard could be deleted rather than left dead.

    Unpaywall was the one source that reported itself unavailable on a fresh
    checkout; with a default it can always be asked, which is exactly why setting
    JMC_USER_EMAIL matters — the address is now always somebody's.
    """
    _blank_contact_env(monkeypatch)
    services = build_services(offline_settings(user_email=None))
    email = services.contact_email()
    assert email and "@" in email
