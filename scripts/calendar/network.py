"""Bounded public HTTPS fetches using the machine's existing proxy configuration.

Direct HTTPS connections retain the pilot's validated-IP pinning and TLS hostname
checks. A configured HTTPS proxy may resolve an explicitly approved hostname if
local DNS is unavailable; this never falls back to a direct connection.
"""

import http.client
import ipaddress
import re
import socket
import ssl
import time
import urllib.error
import urllib.request
import zlib
from urllib.parse import urljoin, urlsplit, urlunsplit

from core import (MAX_PAGE_BYTES, Page, PinnedHTTPSConnection, SafeHTTP, Stopped,
                  Target, ValidationError, now, validate_source_url)


def _approved_hostname(value):
    if not isinstance(value, str) or not value or any(c in value for c in "/:@\\%"):
        raise ValidationError("Approved hosts must be exact public DNS hostnames.")
    try:
        host = value.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValidationError("Invalid approved hostname.") from exc
    if ("." not in host or len(host) > 253 or not re.fullmatch(r"[a-z0-9.-]+", host)
            or any(not p or len(p) > 63 or p.startswith("-") or p.endswith("-") for p in host.split("."))
            or host.endswith((".localhost", ".local", ".internal", ".lan", ".home", ".test", ".invalid", ".example"))):
        raise ValidationError("Approved hosts must be exact public DNS hostnames.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return host
    raise ValidationError("IP addresses cannot be approved for proxy DNS fallback.")


def approved_hosts_from_urls(urls):
    """Build an exact set from trusted source URLs, including bare/www variants."""
    result = set()
    for url in urls:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.username is not None or parts.password is not None
                or parts.port not in (None, 443) or not parts.hostname):
            raise ValidationError("Approved source URLs must use HTTPS on port 443 without credentials.")
        host = _approved_hostname(parts.hostname)
        result.add(host)
        result.add(host[4:] if host.startswith("www.") else "www." + host)
    return result


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # Fetch validates every redirect before another request is sent.


class _PinnedOrProxyHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, target, direct_factory):
        super().__init__(context=ssl.create_default_context())
        self.target = target
        self.direct_factory = direct_factory

    def https_open(self, req):
        if getattr(req, "_tunnel_host", None):
            # Standard ProxyHandler chose this tunnel. Keep its proxy routing,
            # proxy authentication and TLS verification without a direct retry.
            return self.do_open(http.client.HTTPSConnection, req, context=self._context)
        if not self.target.ips:
            raise ValidationError("Proxy routing is unavailable; no direct connection was attempted.")

        def direct_connection(host, timeout, **kwargs):
            return self.direct_factory(self.target, timeout)

        return self.do_open(direct_connection, req)


class LocalNetworkHTTP(SafeHTTP):
    def __init__(self, approved_hosts=None, resolver=None,
                 connection_factory=PinnedHTTPSConnection, page_limit=MAX_PAGE_BYTES,
                 compressed_limit=None, request_timeout=12, total_timeout=30,
                 accepted_content_types=None, proxy_reader=None, opener_factory=None):
        super().__init__(resolver=resolver, connection_factory=connection_factory,
                         page_limit=page_limit, request_timeout=request_timeout,
                         total_timeout=total_timeout)
        if isinstance(approved_hosts, str):
            raise ValidationError("approved_hosts must be a collection of exact hostnames.")
        self.approved_hosts = frozenset(_approved_hostname(h) for h in (approved_hosts or ()))
        self.compressed_limit = page_limit if compressed_limit is None else compressed_limit
        if (not isinstance(page_limit, int) or not isinstance(self.compressed_limit, int)
                or page_limit <= 0 or self.compressed_limit <= 0
                or request_timeout <= 0 or total_timeout <= 0):
            raise ValidationError("Positive response-size and timeout limits are required.")
        types = {"text/html", "application/xhtml+xml"} if accepted_content_types is None else accepted_content_types
        if isinstance(types, str) or not types or not all(isinstance(t, str) and "/" in t for t in types):
            raise ValidationError("accepted_content_types must list explicit MIME types.")
        self.accepted_content_types = frozenset(t.split(";", 1)[0].strip().lower() for t in types)
        self.proxy_reader = proxy_reader or urllib.request.getproxies
        self.opener_factory = opener_factory or urllib.request.build_opener

    @staticmethod
    def _uses_https_proxy(proxies, host):
        return bool(proxies.get("https")) and not urllib.request.proxy_bypass(host)

    def _target(self, url, proxies):
        try:
            return validate_source_url(url, self.resolver)
        except ValidationError as exc:
            # Only a DNS lookup failure may use the proxy's resolver. Syntax,
            # credentials, schemes, ports, and private/mixed DNS results retain
            # their original hard failures from validate_source_url.
            if str(exc) != "Could not resolve the source hostname.":
                raise
            parts = urlsplit(url)
            host = parts.hostname.rstrip(".").encode("idna").decode("ascii").lower()
            if host not in self.approved_hosts or not self._uses_https_proxy(proxies, host):
                raise
            clean = urlunsplit(("https", host, parts.path or "/", parts.query, ""))
            path = urlunsplit(("", "", parts.path or "/", parts.query, ""))
            return Target(clean, host, (), path)

    def _remaining(self, deadline, stop_event):
        if stop_event.is_set():
            raise Stopped()
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValidationError("Source request exceeded its time limit.")
        return min(self.request_timeout, remaining)

    @staticmethod
    def _read_timeout(response, timeout):
        # urllib's HTTPResponse retains the socket through its buffered file.
        raw = getattr(getattr(response, "fp", None), "raw", None)
        sock = getattr(raw, "_sock", None)
        if sock is not None:
            sock.settimeout(timeout)

    def _decode_gzip(self, body, deadline, stop_event):
        pieces, decoded_size, members = [], 0, 0
        while body:
            self._remaining(deadline, stop_event)
            members += 1
            if members > 32:
                raise ValidationError("Gzip response contains too many members.")
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
            try:
                piece = decoder.decompress(body, self.page_limit - decoded_size + 1)
            except zlib.error as exc:
                raise ValidationError("Source returned invalid gzip data.") from exc
            decoded_size += len(piece)
            if decoded_size > self.page_limit:
                raise ValidationError("Decoded source page exceeds the byte limit.")
            if not decoder.eof:
                raise ValidationError("Source returned incomplete gzip data.")
            pieces.append(piece)
            body = decoder.unused_data
        self._remaining(deadline, stop_event)
        return b"".join(pieces)

    def _body(self, response, deadline, stop_event):
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in self.accepted_content_types:
            raise ValidationError("Source returned an unsupported content type: " + (content_type or "missing") + ".")
        encoding = response.headers.get("Content-Encoding", "identity").strip().lower()
        if encoding not in ("", "identity", "gzip", "x-gzip"):
            raise ValidationError("Source returned an unsupported content encoding.")
        wire_limit = self.compressed_limit if encoding in ("gzip", "x-gzip") else min(self.compressed_limit, self.page_limit)
        length = response.headers.get("Content-Length")
        if length is not None:
            try:
                declared = int(length)
            except ValueError as exc:
                raise ValidationError("Invalid source Content-Length.") from exc
            if declared < 0 or declared > wire_limit:
                raise ValidationError("Source response exceeds the transfer byte limit.")
        chunks, size = [], 0
        read = getattr(response, "read1", response.read)
        while True:
            timeout = self._remaining(deadline, stop_event)
            self._read_timeout(response, timeout)
            chunk = read(min(65536, wire_limit + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > wire_limit:
                raise ValidationError("Source response exceeds the transfer byte limit.")
            chunks.append(chunk)
        body = b"".join(chunks)
        if encoding in ("gzip", "x-gzip"):
            if not body:
                raise ValidationError("Source returned empty gzip data.")
            body = self._decode_gzip(body, deadline, stop_event)
        self._remaining(deadline, stop_event)
        return body

    def fetch(self, url, stop_event, public_headers=None):
        deadline = time.monotonic() + self.total_timeout
        proxies = self.proxy_reader()
        original_host = urlsplit(url).hostname
        public_headers = public_headers or {}
        if any(k.lower() not in ("x-api-key", "x-typesense-api-key", "apikey") or not isinstance(v, str)
               or len(v) > 512 or "\r" in v or "\n" in v for k, v in public_headers.items()):
            raise ValidationError("Only explicitly observed public calendar widget headers are supported.")
        if any(k.lower() == 'apikey' for k in public_headers):
            parts = urlsplit(url)
            if (parts.hostname != 'pggdjlwzqcnvjmmajjuj.supabase.co'
                    or parts.path != '/rest/v1/events'):
                raise ValidationError('Anonymous calendar key is restricted to the observed Royale feed.')
        for hop in range(4):
            self._remaining(deadline, stop_event)
            target = self._target(url, proxies)
            opener = self.opener_factory(urllib.request.ProxyHandler(proxies),
                                         _PinnedOrProxyHTTPSHandler(target, self.connection_factory),
                                         _NoRedirect())
            headers = {
                "User-Agent": "BostonRamblerManualPilot/0.4",
                "Accept": ", ".join(sorted(self.accepted_content_types)),
                "Accept-Encoding": "gzip, identity", "Connection": "close",
            }
            if target.host == original_host:
                headers.update(public_headers)
            request = urllib.request.Request(target.url, headers=headers)
            response = None
            try:
                try:
                    response = opener.open(request, timeout=self._remaining(deadline, stop_event))
                except urllib.error.HTTPError as exc:
                    response = exc  # Inspect status, then close without retrying.
                except (urllib.error.URLError, OSError) as exc:
                    reason = getattr(exc, "reason", exc)
                    tunnel = re.search(r"Tunnel connection failed:\s*(\d{3})", str(reason))
                    if tunnel:
                        message = "Configured proxy rejected the tunnel with HTTP " + tunnel.group(1) + "."
                    elif isinstance(reason, (TimeoutError, socket.timeout)):
                        message = "Source request timed out."
                    elif isinstance(reason, ssl.SSLError):
                        message = "Source TLS verification or handshake failed."
                    else:
                        message = "Source HTTPS request failed (" + type(reason).__name__ + ")."
                    raise ValidationError(message) from exc
                status = response.status
                if status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location or hop == 3:
                        raise ValidationError("Missing redirect target or too many redirects.")
                    url = urljoin(target.url, location)
                    continue
                if status != 200:
                    raise ValidationError("Source returned HTTP " + str(status) + ".")
                body = self._body(response, deadline, stop_event)
                page = Page(body, target.url, status, now())
                page.content_type = response.headers.get("Content-Type", "")
                return page
            finally:
                if response is not None:
                    response.close()
        raise ValidationError("Too many redirects.")
