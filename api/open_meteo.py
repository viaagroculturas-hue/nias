"""Conector Open-Meteo para clima atual e previsoes."""

from __future__ import annotations

from typing import Any

from .base import APIConnector


class OpenMeteoConnector(APIConnector):
    """Consulta previsoes e historico recente com suporte a fallback local."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("open_meteo", "https://api.open-meteo.com/v1/forecast", *args, **kwargs)

    def forecast(
        self,
        latitude: float,
        longitude: float,
        daily: list[str] | None = None,
        hourly: list[str] | None = None,
        timezone: str = "America/Sao_Paulo",
        past_days: int = 1,
        forecast_days: int = 7,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "past_days": past_days,
            "forecast_days": forecast_days,
        }
        if daily is None:
            daily = [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "relative_humidity_2m_mean",
                "wind_speed_10m_max",
            ]
        if daily:
            params["daily"] = ",".join(daily)
        if hourly:
            params["hourly"] = ",".join(hourly)

        cache_key = "|".join(
            [
                f"{latitude:.4f}",
                f"{longitude:.4f}",
                ",".join(daily or []),
                ",".join(hourly or []),
                timezone,
                str(past_days),
                str(forecast_days),
            ]
        )
        return self.get_json(params=params, cache_key=f"forecast:{cache_key}")


def fetch_forecast(latitude: float, longitude: float, **kwargs: Any) -> dict[str, Any]:
    """Atalho funcional para obter previsao Open-Meteo com fallback local."""
    return OpenMeteoConnector().forecast(latitude, longitude, **kwargs)
