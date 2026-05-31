"""Conectores externos do NIA$ v6.0."""

from .base import APIConnector, ConnectorError
from .cepea import CEPEAConnector
from .ibge import IBGEConnector
from .nasa_firms import NASAFIRMSConnector
from .open_meteo import OpenMeteoConnector

__all__ = [
    "APIConnector",
    "CEPEAConnector",
    "ConnectorError",
    "IBGEConnector",
    "NASAFIRMSConnector",
    "OpenMeteoConnector",
]
