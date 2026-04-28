"""Conector CEPEA para indicadores agropecuarios."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any

from .base import APIConnector


class _TableTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_cell = False
        self._current: list[str] = []
        self.cells: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in {"td", "th"}:
            self._in_cell = True
            self._current = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"td", "th"} and self._in_cell:
            text = " ".join(part.strip() for part in self._current if part.strip())
            if text:
                self.cells.append(text)
            self._in_cell = False


class CEPEAConnector(APIConnector):
    """Consulta paginas publicas de indicadores CEPEA/ESALQ."""

    indicator_url = "https://cepea.org.br/br/indicador/{indicator}.aspx"

    DEFAULT_INDICATORS = {
        "soja": {"path": "soja", "unit": "R$/sc 60kg"},
        "milho": {"path": "milho", "unit": "R$/sc 60kg"},
        "boi": {"path": "boi-gordo", "unit": "R$/@"},
        "cafe": {"path": "cafe", "unit": "R$/sc 60kg"},
        "citros": {"path": "citros", "unit": "R$/cx 40.8kg"},
        "tomate": {"path": "tomate", "unit": "R$/cx 25kg"},
        "batata": {"path": "batata", "unit": "R$/sc 50kg"},
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("cepea", "https://cepea.org.br/br/indicador", *args, **kwargs)

    def latest_indicator(self, indicator: str) -> dict[str, Any]:
        info = self.DEFAULT_INDICATORS.get(indicator, {"path": indicator, "unit": None})
        path = info["path"]
        url = self.indicator_url.format(indicator=path)
        return self.get(
            url,
            cache_key=f"indicator:{indicator}",
            parser=lambda raw: self._parse_indicator(raw, indicator, info.get("unit"), url),
            headers={"Accept": "text/html,application/xhtml+xml,*/*"},
        )

    def latest_many(self, indicators: list[str] | None = None) -> dict[str, Any]:
        names = indicators or list(self.DEFAULT_INDICATORS)
        result: dict[str, Any] = {}
        for indicator in names:
            result[indicator] = self.latest_indicator(indicator)
        return {
            "source": "CEPEA/ESALQ",
            "indicators": result,
        }

    def indicators(self, indicators: list[str] | None = None) -> dict[str, Any]:
        """Alias semantico para uso pela camada core."""

        return self.latest_many(indicators)

    def _parse_indicator(
        self,
        raw: bytes,
        indicator: str,
        unit: str | None,
        url: str,
    ) -> dict[str, Any]:
        html = raw.decode("utf-8", errors="ignore")
        parser = _TableTextParser()
        parser.feed(html)

        price = None
        date = None
        change_pct = None

        for idx, cell in enumerate(parser.cells):
            parsed_price = self._parse_brazilian_number(cell)
            if parsed_price is not None and price is None:
                price = parsed_price
                if idx > 0:
                    date = parser.cells[idx - 1]
                if idx + 1 < len(parser.cells):
                    change_pct = self._parse_brazilian_number(parser.cells[idx + 1])
                break

        if price is None:
            matches = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d{3})*,\d{2})(?!\d)", html)
            if matches:
                price = self._parse_brazilian_number(matches[0])

        if price is None:
            raise ValueError(f"Nao foi possivel localizar cotacao CEPEA para {indicator}")

        return {
            "indicator": indicator,
            "price": price,
            "unit": unit,
            "change_pct": change_pct,
            "date": date,
            "source": "CEPEA/ESALQ",
            "source_url": url,
        }

    @staticmethod
    def _parse_brazilian_number(value: str) -> float | None:
        match = re.search(r"[-+]?\d{1,3}(?:\.\d{3})*,\d+|[-+]?\d+,\d+", value)
        if not match:
            return None
        try:
            return float(match.group(0).replace(".", "").replace(",", "."))
        except ValueError:
            return None


def latest_cepea_prices(indicators: list[str] | None = None) -> dict[str, Any]:
    """Atalho para buscar indicadores CEPEA com fallback local."""

    return CEPEAConnector().latest_many(indicators)
