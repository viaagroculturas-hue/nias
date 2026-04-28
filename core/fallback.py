"""Orquestracao de leituras externas com Modo Fallback."""

from __future__ import annotations

from typing import Any

from api import CEPEAConnector, IBGEConnector, NASAFIRMSConnector, OpenMeteoConnector


class NIADataHub:
    """Fachada central para conectores NIA$ v6.0."""

    def __init__(
        self,
        nasa_firms: NASAFIRMSConnector | None = None,
        open_meteo: OpenMeteoConnector | None = None,
        ibge: IBGEConnector | None = None,
        cepea: CEPEAConnector | None = None,
    ) -> None:
        self.nasa_firms = nasa_firms or NASAFIRMSConnector()
        self.open_meteo = open_meteo or OpenMeteoConnector()
        self.ibge = ibge or IBGEConnector()
        self.cepea = cepea or CEPEAConnector()

    def snapshot(
        self,
        *,
        latitude: float = -15.78,
        longitude: float = -47.93,
        firms_area: str = "-74,-34,-34,6",
        ibge_product_code: str = "0133",
    ) -> dict[str, Any]:
        """Coleta uma leitura consolidada; cada fonte aplica fallback isoladamente."""

        return {
            "nasa_firms": self.nasa_firms.active_fires(area=firms_area),
            "open_meteo": self.open_meteo.forecast(latitude=latitude, longitude=longitude),
            "ibge": self.ibge.pam_production(product_code=ibge_product_code),
            "cepea": self.cepea.indicators(),
        }
