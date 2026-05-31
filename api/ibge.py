"""Conector IBGE/SIDRA para dados agropecuarios municipais."""

from __future__ import annotations

from typing import Any

from .base import APIConnector


class IBGEConnector(APIConnector):
    """Consulta a API SIDRA do IBGE com fallback local."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__("ibge_sidra", "https://apisidra.ibge.gov.br", *args, **kwargs)

    def sidra_values(
        self,
        table: str = "1612",
        territorial_level: str = "n6",
        territories: str = "all",
        variables: str = "214",
        period: str = "last",
        classification: str | None = None,
        *,
        cache_key: str | None = None,
    ) -> dict[str, Any]:
        """Consulta valores SIDRA parametrizados.

        Exemplo de `classification`: "c81/0133" para produto tomate na tabela PAM 1612.
        """
        path = f"/values/t/{table}/{territorial_level}/{territories}/v/{variables}/p/{period}"
        if classification:
            path = f"{path}/{classification.strip('/')}"
        key = cache_key or "|".join([table, territorial_level, territories, variables, period, classification or ""])
        return self.get_json(path, cache_key=key)

    def municipal_agricultural_production(
        self,
        product_code: str,
        *,
        variable: str = "214",
        period: str = "last",
    ) -> dict[str, Any]:
        """Consulta Producao Agricola Municipal por codigo de produto SIDRA."""
        return self.sidra_values(
            table="1612",
            territorial_level="n6",
            territories="all",
            variables=variable,
            period=period,
            classification=f"c81/{product_code}/d/v{variable}%200",
            cache_key=f"pam:{product_code}:{variable}:{period}",
        )

    def pam_production(self, product_code: str, **kwargs: Any) -> dict[str, Any]:
        """Alias semantico para producao agricola municipal."""

        return self.municipal_agricultural_production(product_code, **kwargs)

