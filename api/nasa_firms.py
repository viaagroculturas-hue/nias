"""Conector NASA FIRMS para alertas de fogo do NIA$ v6.0."""

from __future__ import annotations

import csv
import os
from io import StringIO
from typing import Any

from .base import APIConnector


class NASAFIRMSConnector(APIConnector):
    """Consulta focos de calor FIRMS com suporte a fallback local."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            name="nasa_firms",
            base_url="https://firms.modaps.eosdis.nasa.gov/api/area/csv",
            **kwargs,
        )

    def fetch_fires(
        self,
        area: str = "-74,-34,-34,6",
        days: int = 1,
        source: str = "VIIRS_SNPP_NRT",
        map_key: str | None = None,
    ) -> dict[str, Any]:
        """Busca focos por bounding box: west,south,east,north.

        A chave pode ser enviada por parametro ou via NASA_FIRMS_MAP_KEY.
        Sem chave, a NASA FIRMS retorna erro e o modo fallback sera acionado
        se houver leitura anterior valida.
        """

        key = map_key or os.environ.get("NASA_FIRMS_MAP_KEY", "MAP_KEY")
        cache_key = f"{source}:{area}:{int(days)}"
        return self.get_text(
            f"{key}/{source}/{area}/{int(days)}",
            cache_key=cache_key,
            headers={"Accept": "text/csv,*/*"},
            encoding="utf-8",
        )

    def active_fires(self, **kwargs: Any) -> dict[str, Any]:
        """Alias semantico para uso pela camada core."""

        return self.fetch_fires(**kwargs)

    @staticmethod
    def parse_csv(text: str) -> list[dict[str, str]]:
        reader = csv.DictReader(StringIO(text))
        return [dict(row) for row in reader]


def fetch_fires(**kwargs: Any) -> dict[str, Any]:
    """Atalho funcional para uso simples em jobs e scripts."""

    return NASAFIRMSConnector().fetch_fires(**kwargs)
