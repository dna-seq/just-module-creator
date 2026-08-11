"""Outbound network. The only module in this package permitted to open a socket.

Everything here exists so that pacing, identity and the shared NCBI budget cannot
drift between clients. Two rules, both in CLAUDE.md §2:

* **No socket outside this module.** ``discovery.py`` composes ``HttpService``
  instances; the tool modules call those. Nobody constructs an ``httpx.Client``
  anywhere else.
* **No private upstream API.** Everything we need from ``just-dna-enricher`` is
  public — ``EutilsSettings.identity_params()``, ``PacingGate``, the injectable
  ``LookupClients``. We never reach for ``EutilsClient._get``.

The interesting part is ``ServiceGate``. Upstream's ``PacingGate`` is correct for
a single-threaded CLI and read-modify-writes ``last`` with no lock. Every tool
here runs its blocking work through ``anyio.to_thread.run_sync``, so two workers
can both observe the interval as elapsed and fire together — which is how a 3/s
budget becomes a 429. Serializing the wait fixes it without touching upstream.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

import httpx
from just_dna_enricher.eutils import EutilsClient, EutilsSettings
from just_dna_enricher.literature import CrossrefClient, EuropePmcClient
from just_dna_enricher.lookup import LookupClients
from just_dna_enricher.net import PacingGate, attempt_floor
from tenacity import RetryCallState, retry, retry_if_exception_type, wait_exponential_jitter

from just_module_creator.settings import DEFAULT_CONTACT_EMAIL, Settings

log = logging.getLogger(__name__)

#: Cap on a server-supplied ``Retry-After``. A service asking us to wait ten
#: minutes is telling us to go away, and blocking a tool call that long is worse
#: than reporting that the source could not answer.
MAX_RETRY_AFTER = 30.0

#: The backoff curve, used whenever the server did not name its own delay.
#: Same shape as the enricher's clients, so one deployment behaves consistently.
_JITTER = wait_exponential_jitter(initial=1.0, max=10.0)


@dataclass
class ServiceGate(PacingGate):
    """A ``PacingGate`` that stays correct when shared across worker threads.

    Upstream's ``wait()`` reads ``last``, sleeps, then writes it — safe under one
    thread and not under several. Holding a lock across the whole wait also gives
    us the property we actually want from a courtesy budget: one in-flight request
    per service at a time, spaced by ``interval``.

    ``clock`` and ``sleeper`` stay injectable, because that is how a test proves a
    3 s interval without taking 3 s.
    """

    lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def wait(self) -> None:
        with self.lock:
            super().wait()


def _retry_after_seconds(response: httpx.Response) -> float | None:
    """The server's own ``Retry-After``, in seconds, when it gave a usable one.

    Only the delta-seconds form is honoured. The HTTP-date form is legal but rare
    on these APIs, and parsing it wrong would be worse than ignoring it — we fall
    back to the caller's own backoff, which is never *less* polite.
    """
    raw = response.headers.get("Retry-After")
    if not raw or not raw.strip().isdigit():
        return None
    return min(float(raw.strip()), MAX_RETRY_AFTER)


class ServiceUnavailable(RuntimeError):
    """A source could not answer. Carries the reason, never a false negative.

    Raised rather than returned because every caller turns it into the same
    thing: a ``SourceStatus`` with ``results=None``. What must never happen is
    a source that failed being rendered as a source that found nothing.
    """

    def __init__(self, source: str, reason: str, *, rate_limited: bool = False) -> None:
        super().__init__(f"{source}: {reason}")
        self.source = source
        self.reason = reason
        self.rate_limited = rate_limited


class _Throttled(Exception):
    """A 429 or 5xx: worth retrying, and it may carry the server's own delay.

    An exception rather than a return value because tenacity retries on
    exceptions, and reusing its machinery is the point.
    """

    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"HTTP {response.status_code}")
        self.status_code = response.status_code
        self.retry_after = _retry_after_seconds(response)


def _wait_honouring_retry_after(retry_state: RetryCallState) -> float:
    """Exponential jitter, overridden by the server's own ``Retry-After``.

    A service that tells us when to come back knows better than our backoff curve,
    and ignoring it is how a polite-pool guest becomes a blocked one.
    """
    outcome = retry_state.outcome
    exc = outcome.exception() if outcome is not None else None
    if isinstance(exc, _Throttled) and exc.retry_after is not None:
        return exc.retry_after
    return _JITTER(retry_state)


@dataclass
class HttpService:
    """One outbound service: base URL, pacing gate, and a reused connection pool.

    Built by ``discovery.py`` from a ``SourceSpec``; the gate is passed in rather
    than created here so that two services sharing a budget (our PubMed search and
    the enricher's ``EutilsClient``) can share one gate.
    """

    name: str
    base_url: str
    gate: ServiceGate
    timeout: float = 30.0
    headers: dict[str, str] = field(default_factory=dict)
    _client: httpx.Client | None = field(default=None, repr=False)

    def _http(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout, follow_redirects=True, headers=self.headers
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        """One paced GET. Raises ``ServiceUnavailable`` rather than an httpx error.

        Callers turn that into a ``SourceStatus`` with ``results=None``, which is
        the whole point: a source that failed must never render as a source that
        found nothing.
        """
        try:
            return self._get(path, params)
        except _Throttled as exc:
            raise ServiceUnavailable(
                self.name, f"HTTP {exc.status_code}", rate_limited=exc.status_code == 429
            ) from exc
        except httpx.HTTPStatusError as exc:
            # A 4xx that is not 429: the request was wrong. Not retried, because
            # repeating it only spends someone else's budget.
            raise ServiceUnavailable(self.name, f"HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise ServiceUnavailable(self.name, f"{type(exc).__name__}: {exc}") from exc

    @retry(
        stop=attempt_floor(3),
        wait=_wait_honouring_retry_after,
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException, _Throttled)),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any] | None) -> httpx.Response:
        """The retried attempt. Same shape as the enricher's own clients.

        `attempt_floor` rather than `stop_after_attempt` so a deployment can raise
        the count with the same variable that governs upstream's nine clients —
        safe because the gate paces *before* each retry, so an extra attempt
        spends a slot of the budget rather than bursting past it.
        """
        url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}" if path else self.base_url
        self.gate.wait()
        response = self._http().get(url, params=params)
        if response.status_code == 429 or response.status_code >= 500:
            raise _Throttled(response)
        response.raise_for_status()
        return response


@dataclass
class NetworkServices:
    """The shared client set, built once per server and closed at shutdown.

    Upstream's ``LookupClients`` docstring is explicit that a fresh set per
    question "discards the rate-limit state that keeps gnomAD from refusing us"
    and reopens a connection for a single request — so it is held here and passed
    into every upstream call rather than defaulted.

    The NCBI gate is shared between the enricher's ``EutilsClient`` and our own
    PubMed search service. That sharing is the whole point: two independently
    correct 3/s clients against one IP is a 6/s client.
    """

    settings: Settings
    ncbi_gate: ServiceGate
    lookup_clients: LookupClients
    eutils_settings: EutilsSettings
    _extra: list[HttpService] = field(default_factory=list, repr=False)

    def register(self, service: HttpService) -> HttpService:
        """Track a service so shutdown closes its pool."""
        self._extra.append(service)
        return service

    def contact_email(self) -> str:
        """The polite-pool contact. Always set — see ``build_services``.

        Resolved once at build time as ``JMC_USER_EMAIL`` → the enricher's
        ``JUST_DNA_CONTACT_EMAIL`` → :data:`~just_module_creator.settings.\
DEFAULT_CONTACT_EMAIL`, so a source needing a contact can no longer report itself
        unavailable for want of one.

        **Still never an invented address.** The rule was never "prefer None" — it
        is that an address we made up misattributes our traffic to a real person.
        The default is the project's own, supplied by its owner. What it costs is
        attribution: unset means everyone shares one identity, and both the rate
        limit and any abuse report land there, which is why ``JMC_USER_EMAIL`` goes
        first and ``.env.template`` asks for it.
        """
        return self.eutils_settings.email or DEFAULT_CONTACT_EMAIL

    def close(self) -> None:
        for service in self._extra:
            service.close()
        self._extra.clear()
        self.lookup_clients.close()


def build_services(settings: Settings) -> NetworkServices:
    """Construct the shared client set. Opens no connection until first use.

    Safe to call at server build time: every client here is lazy, so importing or
    constructing the server still touches no network.
    """
    # Ours first, then upstream's, then the project default. Passing `None` when
    # JMC_USER_EMAIL is unset is the load-bearing part: `__post_init__` only reads
    # JUST_DNA_CONTACT_EMAIL when `email is None`, so upstream's precedence is
    # inherited rather than restated here, and the default lands last.
    eutils_settings = EutilsSettings(email=(settings.user_email or "").strip() or None)
    if not eutils_settings.email:
        eutils_settings.email = DEFAULT_CONTACT_EMAIL
    # `min_request_interval` is derived in EutilsSettings.__post_init__ from
    # whether NCBI_API_KEY is present (1/3 s unkeyed, 1/10 s keyed). Read it
    # rather than restating the numbers, so upstream owns the policy.
    interval = eutils_settings.min_request_interval or 0.34
    ncbi_gate = ServiceGate(interval=interval)

    clients = LookupClients(
        eutils=EutilsClient(settings=eutils_settings, gate=ncbi_gate),
        europepmc=EuropePmcClient(),
        crossref=CrossrefClient(),
    )
    # Log which step supplied the contact, not merely that one exists: "default"
    # is the state an operator wants to notice, because it means their traffic is
    # pooled with everyone else's.
    contact_origin = (
        "JMC_USER_EMAIL"
        if (settings.user_email or "").strip()
        else "project default"
        if eutils_settings.email == DEFAULT_CONTACT_EMAIL
        else "JUST_DNA_CONTACT_EMAIL"
    )
    log.debug(
        "Network services built (ncbi interval=%.3fs, contact from %s, s2 key=%s)",
        interval,
        contact_origin,
        "set" if settings.semantic_scholar_key() else "unset",
    )
    return NetworkServices(
        settings=settings,
        ncbi_gate=ncbi_gate,
        lookup_clients=clients,
        eutils_settings=eutils_settings,
    )
