from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: str
    error: str = ""

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300 and not self.error


class HttpClient:
    """HTTP client with unified timeout, retry and error handling."""

    def __init__(self, timeout: int = 10, retries: int = 1, retry_interval: float = 0.5):
        self.timeout = timeout
        self.retries = max(0, retries)
        self.retry_interval = max(0.0, retry_interval)

    def post_json(
        self,
        url: str,
        payload: dict,
        proxy_url: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req_headers: dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": "StarRailAssistant/1.0",
        }
        if headers:
            req_headers.update(dict(headers))
        request = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
        return self._open(request, proxy_url=proxy_url)

    def post_multipart(
        self,
        url: str,
        body: bytes,
        boundary: str,
        proxy_url: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpResponse:
        req_headers: dict[str, str] = {
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "User-Agent": "StarRailAssistant/1.0",
        }
        if headers:
            req_headers.update(dict(headers))
        request = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
        return self._open(request, proxy_url=proxy_url)

    def _open(self, request: urllib.request.Request, proxy_url: str | None = None) -> HttpResponse:
        opener = self._build_opener(proxy_url)
        last_response = HttpResponse(0, "", "unknown error")
        attempts = self.retries + 1

        for attempt in range(attempts):
            try:
                with opener.open(request, timeout=self.timeout) as resp:
                    return HttpResponse(resp.status, resp.read().decode("utf-8", errors="replace"))
            except urllib.error.HTTPError as err:
                body = err.read().decode("utf-8", errors="replace")
                last_response = HttpResponse(err.code, body, "http error")
                if not self._should_retry(err.code, attempt, attempts):
                    return last_response
            except urllib.error.URLError as err:
                reason = str(err.reason)
                last_response = HttpResponse(0, "", "url error: " + reason)
                if not self._should_retry(None, attempt, attempts):
                    return last_response
            except socket.timeout:
                last_response = HttpResponse(0, "", "timeout")
                if not self._should_retry(None, attempt, attempts):
                    return last_response
            except Exception as err:  # pragma: no cover - defensive path
                last_response = HttpResponse(0, "", "unexpected error: " + str(err))
                if not self._should_retry(None, attempt, attempts):
                    return last_response

            if attempt + 1 < attempts:
                time.sleep(self.retry_interval * (attempt + 1))

        return last_response

    @staticmethod
    def _build_opener(proxy_url: str | None) -> urllib.request.OpenerDirector:
        if proxy_url:
            handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
            return urllib.request.build_opener(handler)
        return urllib.request.build_opener()

    @staticmethod
    def _should_retry(status_code: int | None, attempt: int, attempts: int) -> bool:
        if attempt + 1 >= attempts:
            return False
        if status_code is None:
            return True
        return status_code >= 500

