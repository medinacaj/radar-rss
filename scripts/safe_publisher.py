#!/usr/bin/env python3
"""Shared, fail-closed public HTTPS transport for untrusted AUTO publishers."""
from __future__ import annotations

import http.client
import ipaddress
import os
from queue import Empty, Queue
import re
import socket
import ssl
from threading import Event, Lock, Thread, Timer
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

AGENT = "Mozilla/5.0 (compatible; RadarRSS/1.1; +https://github.com/medinacaj/radar-rss)"
MAX_REQUESTS = 100
MAX_SECONDS = 180
MAX_BYTES = 1_000_000


class FetchError(ValueError):
    """Unavailable or disallowed public endpoint; do not bypass/retry."""
    def __init__(self, message: str, *, reason: str = 'network'):
        super().__init__(message)
        self.reason = reason


class UnsafeURL(FetchError):
    """A URL or DNS answer is outside the permitted public publisher boundary."""


class BudgetExceeded(FetchError):
    """The cycle has exhausted its time or request budget."""


def publisher_key(host: str) -> str:
    return host.lower().removeprefix('www.')


def checked_url(url: str, publisher: str | None = None) -> str:
    """Strict syntactic boundary; DNS is checked separately when connecting."""
    try:
        if not isinstance(url, str) or len(url) > 2048 or re.search(r'[\s\\\x00-\x1f\x7f]', url):
            raise ValueError('invalid characters')
        parsed = urlsplit(url)
        host = parsed.hostname or ''
        if (parsed.scheme != 'https' or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443) or not host or '.' not in host
                or host.endswith('.') or re.search(r'[^a-zA-Z0-9.-]', host)
                or host.lower().endswith(('.local', '.internal', '.localhost', '.test', '.invalid'))):
            raise ValueError('invalid public HTTPS URL')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError('literal addresses are not publisher domains')
        if publisher is not None and publisher_key(host) != publisher_key(publisher):
            raise ValueError('different publisher')
        return urlunsplit(('https', host.lower(), parsed.path or '/', parsed.query, ''))
    except (ValueError, TypeError) as exc:
        raise UnsafeURL('URL fuera del dominio público autorizado') from exc


def resolve_public(host: str, timeout: float = 3) -> str:
    # libc DNS has no per-call timeout. A daemon worker cannot hold up the build.
    answers = Queue(maxsize=1)
    def lookup():
        try:
            answers.put((True, socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)))
        except OSError as exc:
            answers.put((False, exc))
    Thread(target=lookup, daemon=True).start()
    try:
        ok, addresses = answers.get(timeout=timeout)
        if not ok:
            raise FetchError('DNS no disponible')
        if not addresses or not all(ipaddress.ip_address(row[4][0]).is_global for row in addresses):
            raise UnsafeURL('DNS privado o no público')
        return addresses[0][4][0]
    except (Empty, OSError, ValueError) as exc:
        if isinstance(exc, UnsafeURL):
            raise
        raise FetchError('DNS no disponible') from exc


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Vetted IP, verified domain TLS, and a socket that a watchdog can abort."""
    def __init__(self, host: str, address: str, timeout: float, context: ssl.SSLContext):
        super().__init__(host, timeout=timeout, context=context)
        self.address = address
        self._socket_lock = Lock()
        self._aborted = Event()
        self._connecting = None
        self._transport_socket = None

    def abort(self):
        self._aborted.set()
        with self._socket_lock:
            sock = self._transport_socket if self._transport_socket is not None else self.sock
            if sock is None:
                sock = self._connecting
        if sock is not None:
            # close() alone does not interrupt a buffered response.makefile().
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass

    def connect(self):
        family = socket.AF_INET6 if ':' in self.address else socket.AF_INET
        raw = socket.socket(family, socket.SOCK_STREAM)
        raw.settimeout(self.timeout)
        try:
            with self._socket_lock:
                self._connecting = raw
                if self._aborted.is_set():
                    raise TimeoutError('Conexión cancelada')
            raw.connect((self.address, 443))
            # Publish the TLS socket before its potentially blocking handshake.
            wrapped = self._context.wrap_socket(raw, server_hostname=self.host,
                                                 do_handshake_on_connect=False)
            with self._socket_lock:
                self.sock = wrapped
                self._transport_socket = wrapped
                self._connecting = None
                if self._aborted.is_set():
                    wrapped.close()
                    raise TimeoutError('Conexión cancelada')
            wrapped.do_handshake()
        except Exception:
            raw.close()
            raise


def configured_proxy() -> bool:
    return any(os.environ.get(key) for key in
               ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'http_proxy', 'https_proxy', 'all_proxy'))


class SafeFetcher:
    def __init__(self, *, seconds=MAX_SECONDS, max_requests=MAX_REQUESTS, exchange_seconds=8):
        self.proxy_configured = configured_proxy()
        self.requests_left = min(MAX_REQUESTS, max_requests)
        self.deadline = time.monotonic() + min(MAX_SECONDS, seconds)
        self.exchange_seconds = exchange_seconds
        self.robots: dict[str, RobotFileParser] = {}
        self.last_requested: dict[str, float] = {}
        self.context = ssl.create_default_context()

    def _budget(self):
        if self.proxy_configured or configured_proxy():
            self.proxy_configured = True
            # Direct pinned TLS cannot safely honor an inherited proxy. Never
            # bypass it, disable it or expose its potentially secret URL.
            raise FetchError('Proxy configurado: transporte de descubrimiento no disponible')
        if self.requests_left <= 0 or time.monotonic() >= self.deadline:
            raise BudgetExceeded('Límite de solicitudes o tiempo alcanzado')

    def _request(self, url: str, limit: int) -> tuple[int, dict, bytes]:
        self._budget()
        self.requests_left -= 1
        parsed = urlsplit(checked_url(url))
        address = resolve_public(parsed.hostname, timeout=min(3, max(.01, self.deadline-time.monotonic())))
        self._budget_time()
        connection = PinnedHTTPSConnection(parsed.hostname, address,
                                           min(5, max(.1, self.deadline-time.monotonic())), self.context)
        end = min(self.deadline, time.monotonic() + self.exchange_seconds)
        expired = Event()
        def abort_exchange():
            expired.set()
            connection.abort()
        watchdog = Timer(max(.001, end-time.monotonic()), abort_exchange)
        watchdog.daemon = True
        watchdog.start()
        try:
            target = urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
            connection.request('GET', target, headers={'User-Agent': AGENT, 'Accept-Encoding': 'identity',
                                                       'Accept-Language': 'es', 'Accept': '*/*'})
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            if headers.get('content-encoding', 'identity').lower() not in ('identity', ''):
                raise FetchError('Respuesta comprimida no admitida')
            length = headers.get('content-length')
            if length is not None and int(length) > limit:
                raise FetchError('Documento demasiado grande')
            chunks, size = [], 0
            while True:
                remaining = end - time.monotonic()
                if remaining <= 0:
                    raise FetchError('Tiempo de descarga agotado')
                if connection.sock:
                    connection.sock.settimeout(min(3, remaining))
                # read1 returns after one socket read, so a drip-fed body cannot
                # keep resetting socket timeouts inside an unbounded read(n).
                chunk = response.read1(min(16_384, limit-size+1))
                size += len(chunk)
                if size > limit:
                    raise FetchError('Documento demasiado grande')
                if not chunk:
                    break
                chunks.append(chunk)
            if expired.is_set() or time.monotonic() >= end:
                raise FetchError('Plazo absoluto de descarga agotado')
            return response.status, headers, b''.join(chunks)
        except (OSError, http.client.HTTPException, ValueError) as exc:
            if isinstance(exc, FetchError):
                raise
            raise FetchError('Endpoint público no disponible') from exc
        finally:
            watchdog.cancel()
            connection.close()

    def verify_article_host(self, host: str):
        self._budget()
        resolve_public(host, timeout=min(3, max(.01, self.deadline-time.monotonic())))
        self.check_time()

    def check_time(self):
        self._budget_time()

    def _budget_time(self):
        if time.monotonic() >= self.deadline:
            raise BudgetExceeded('Tiempo de revisión agotado')

    def _allowed(self, url: str):
        parsed = urlsplit(url)
        origin = f'https://{parsed.hostname}'
        if origin not in self.robots:
            status, _, raw = self._read(origin+'/robots.txt', parsed.hostname, 64_000, robots=False)
            parser = RobotFileParser()
            if status == 404:
                parser.parse([])
            elif status == 200:
                parser.parse(raw.decode('utf-8', errors='replace').splitlines())
            else:
                raise FetchError('robots.txt no disponible o acceso denegado', reason='robots')
            self.robots[origin] = parser
        parser = self.robots[origin]
        delay = 0
        for agent in ('RadarRSS', AGENT):
            if not parser.can_fetch(agent, url):
                raise FetchError('robots.txt no permite la consulta', reason='robots')
            delay = max(delay, parser.crawl_delay(agent) or 0)
            rate = parser.request_rate(agent)
            if rate and rate.requests > 0:
                delay = max(delay, rate.seconds / rate.requests)
        if time.monotonic() < self.last_requested.get(origin, 0)+delay:
            # Skip instead of waiting or defeating the publisher's crawl policy.
            raise FetchError('robots.txt exige más tiempo entre consultas', reason='robots')

    def _read(self, url: str, publisher: str | None, limit: int, *, robots: bool = True):
        for _ in range(4):
            self._budget()
            url = checked_url(url, publisher)
            if robots:
                self._allowed(url)
            status, headers, raw = self._request(url, limit)
            if robots:
                self.last_requested[f'https://{urlsplit(url).hostname}'] = time.monotonic()
            if status in (301, 302, 303, 307, 308):
                location = headers.get('location')
                if not location:
                    raise FetchError('Redirección sin destino')
                url = urljoin(url, location)
                continue
            return status, headers, raw
        raise FetchError('Demasiadas redirecciones')

    def get(self, url: str, *, publisher: str | None = None, limit: int = MAX_BYTES) -> bytes:
        status, _, raw = self._read(url, publisher, min(limit, MAX_BYTES))
        if status != 200:
            raise FetchError(f'HTTP {status}; no se reintenta ni se sortea el bloqueo', reason=f'http_{status}')
        return raw
