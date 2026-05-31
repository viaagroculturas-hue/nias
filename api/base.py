"""Infraestrutura comum dos conectores externos do NIA$ v6.0."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from api.cache import CacheMiss, LocalJSONCache


DEFAULT_TIMEOUT = 30
DEFAULT_USER_AGENT = "NIAS-v6.0/1.0"
Parser = Callable[[bytes], Any]


class ConnectorError(RuntimeError):
    """Erro de API externa quando nao ha fallback local disponivel."""


@dataclass(slots=True)
class APIConnector:
    """Cliente HTTP com fallback automatico para a ultima leitura valida."""

    name: str
    base_url: str
    cache: LocalJSONCache = field(default_factory=LocalJSONCache)
    timeout: int = DEFAULT_TIMEOUT
    headers: dict[str, str] = field(default_factory=dict)

    def get_json(
        self,
        path: str = "",
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Executa GET JSON e retorna fallback local quando a API falhar."""

        return self.get(
            path=path,
            params=params,
            cache_key=cache_key,
            headers=headers,
            parser=lambda raw: json.loads(raw.decode("utf-8", errors="ignore")),
        )

    def get_text(
        self,
        path: str = "",
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        headers: dict[str, str] | None = None,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Executa GET de texto e retorna fallback local quando a API falhar."""

        return self.get(
            path=path,
            params=params,
            cache_key=cache_key,
            headers=headers,
            parser=lambda raw: raw.decode(encoding, errors="ignore"),
        )

    def get_csv(
        self,
        path: str = "",
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        headers: dict[str, str] | None = None,
        encoding: str = "utf-8",
    ) -> dict[str, Any]:
        """Executa GET CSV e retorna uma lista de linhas dict com fallback local."""

        import csv
        from io import StringIO

        def parse_csv(raw: bytes) -> list[dict[str, str]]:
            text = raw.decode(encoding, errors="ignore")
            return [dict(row) for row in csv.DictReader(StringIO(text))]

        return self.get(
            path=path,
            params=params,
            cache_key=cache_key,
            headers=headers,
            parser=parse_csv,
        )

    def fetch_raw(
        self,
        path: str = "",
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        headers: dict[str, str] | None = None,
        parser: Parser | None = None,
    ) -> dict[str, Any]:
        """Alias explicito para conectores que precisam parsear bytes brutos."""

        return self.get(
            path=path,
            params=params,
            cache_key=cache_key,
            headers=headers,
            parser=parser,
        )

    def get(
        self,
        path: str = "",
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        headers: dict[str, str] | None = None,
        parser: Parser | None = None,
    ) -> dict[str, Any]:
        """Executa GET e encapsula resposta com metadados live/fallback."""

        url = self._build_url(path, params)
        key = cache_key or url

        try:
            raw = self._request(url, headers=headers)
            payload = parser(raw) if parser else raw.decode("utf-8", errors="ignore")
        except Exception as exc:
            try:
                cached = self.cache.load(self.name, key)
            except CacheMiss as cache_exc:
                raise ConnectorError(
                    f"{self.name}: falha na API e nenhum cache local foi encontrado"
                ) from cache_exc

            return {
                "data": cached["payload"],
                "meta": {
                    "source": self.name,
                    "mode": "fallback",
                    "cache_key": key,
                    "cached_at": cached.get("cached_at"),
                    "source_url": cached.get("source_url"),
                    "error": str(exc),
                },
            }

        self.cache.save(self.name, key, payload, source_url=url)
        return {
            "data": payload,
            "meta": {
                "source": self.name,
                "mode": "live",
                "cache_key": key,
                "source_url": url,
            },
        }

    def _build_url(self, path: str, params: dict[str, Any] | None) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{self.base_url.rstrip('/')}/{path.lstrip('/')}" if path else self.base_url

        if not params:
            return url

        clean_params = {
            key: value
            for key, value in params.items()
            if value is not None and value != ""
        }
        separator = "&" if urllib.parse.urlparse(url).query else "?"
        return f"{url}{separator}{urllib.parse.urlencode(clean_params, doseq=True)}"

    def _request(self, url: str, headers: dict[str, str] | None = None) -> bytes:
        request_headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            **self.headers,
            **(headers or {}),
        }
        req = urllib.request.Request(url, headers=request_headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise ConnectorError(f"{self.name}: HTTP {exc.code} em {url}") from exc
        except urllib.error.URLError as exc:
            raise ConnectorError(f"{self.name}: erro de rede em {url}: {exc.reason}") from exc
