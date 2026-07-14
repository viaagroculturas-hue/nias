"""
Google Earth Engine — NDVI por município da América do Sul.
Requer: service account + gee_key.json
Documentação: https://developers.google.com/earth-engine/guides/service_account
"""
import logging
import json
from datetime import date, timedelta
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_ee_inicializado = False


def _init_gee() -> bool:
    global _ee_inicializado
    if _ee_inicializado:
        return True
    try:
        import ee
        credentials = ee.ServiceAccountCredentials(
            settings.gee_service_account,
            settings.gee_key_file,
        )
        ee.Initialize(credentials)
        _ee_inicializado = True
        logger.info("Google Earth Engine inicializado")
        return True
    except ImportError:
        logger.warning("earthengine-api não instalado — pip install earthengine-api")
        return False
    except Exception as e:
        logger.error(f"GEE init erro: {e}")
        return False


def calcular_ndvi_municipio(
    lat: float,
    lon: float,
    buffer_km: float = 10.0,
    dias_atras: int = 10,
) -> dict | None:
    """
    NDVI médio de um ponto + buffer usando Sentinel-2 ou Landsat-9.
    Retorna NDVI médio, fase estimada e anomalia z-score.
    """
    if not _init_gee():
        return _ndvi_simulado(lat, lon)

    try:
        import ee
        ponto = ee.Geometry.Point([lon, lat])
        area = ponto.buffer(buffer_km * 1000)

        data_fim = date.today()
        data_ini = data_fim - timedelta(days=dias_atras)

        # Sentinel-2 SR — resolução 10m, cobertura SA completa
        colecao = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(area)
            .filterDate(data_ini.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
            .sort("system:time_start", False)
        )

        contagem = colecao.size().getInfo()
        if contagem == 0:
            # Fallback para Landsat-9
            colecao = (
                ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
                .filterBounds(area)
                .filterDate(data_ini.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d"))
                .filter(ee.Filter.lt("CLOUD_COVER", 20))
            )
            contagem = colecao.size().getInfo()
            if contagem == 0:
                logger.warning(f"GEE: sem imagens para ({lat},{lon})")
                return None

            def add_ndvi_landsat(img):
                nir = img.select("SR_B5").multiply(0.0000275).add(-0.2)
                red = img.select("SR_B4").multiply(0.0000275).add(-0.2)
                return img.addBands(nir.subtract(red).divide(nir.add(red)).rename("NDVI"))

            colecao = colecao.map(add_ndvi_landsat)
            satelite = "Landsat-9"
        else:
            def add_ndvi_s2(img):
                nir = img.select("B8").divide(10000)
                red = img.select("B4").divide(10000)
                return img.addBands(nir.subtract(red).divide(nir.add(red)).rename("NDVI"))

            colecao = colecao.map(add_ndvi_s2)
            satelite = "Sentinel-2"

        # Mediana composta para reduzir ruído de nuvens
        composta = colecao.median()
        ndvi_stats = composta.select("NDVI").reduceRegion(
            reducer=ee.Reducer.mean().combine(ee.Reducer.stdDev(), sharedInputs=True),
            geometry=area,
            scale=30,
            maxPixels=1e8,
        ).getInfo()

        ndvi_medio = ndvi_stats.get("NDVI_mean")
        ndvi_std   = ndvi_stats.get("NDVI_stdDev")

        if ndvi_medio is None:
            return None

        return {
            "ndvi_medio": round(float(ndvi_medio), 4),
            "ndvi_std":   round(float(ndvi_std), 4) if ndvi_std else None,
            "fase_estimada": _classificar_fase(float(ndvi_medio)),
            "satelite": satelite,
            "imagens_usadas": contagem,
            "periodo_dias": dias_atras,
            "anomalia_detectada": False,  # z-score calculado no verificacao_service
        }

    except Exception as e:
        logger.error(f"GEE NDVI ({lat},{lon}) erro: {e}")
        return None


def calcular_ndvi_regiao(
    geom_geojson: dict,
    dias_atras: int = 15,
) -> dict | None:
    """NDVI para um polígono GeoJSON (talhão ou município)."""
    if not _init_gee():
        return None

    try:
        import ee
        area = ee.Geometry(geom_geojson)
        data_fim = date.today()
        data_ini = data_fim - timedelta(days=dias_atras)

        colecao = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(area)
            .filterDate(data_ini.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d"))
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 15))
        )

        def add_ndvi(img):
            nir = img.select("B8").divide(10000)
            red = img.select("B4").divide(10000)
            return img.addBands(nir.subtract(red).divide(nir.add(red)).rename("NDVI"))

        composta = colecao.map(add_ndvi).median()
        stats = composta.select("NDVI").reduceRegion(
            reducer=ee.Reducer.mean().combine(
                ee.Reducer.min().combine(ee.Reducer.max(), sharedInputs=True),
                sharedInputs=True,
            ),
            geometry=area,
            scale=10,
            maxPixels=1e9,
        ).getInfo()

        return {
            "ndvi_medio": round(float(stats.get("NDVI_mean", 0)), 4),
            "ndvi_min":   round(float(stats.get("NDVI_min", 0)), 4),
            "ndvi_max":   round(float(stats.get("NDVI_max", 0)), 4),
            "fase_estimada": _classificar_fase(float(stats.get("NDVI_mean", 0))),
            "satelite": "Sentinel-2",
        }
    except Exception as e:
        logger.error(f"GEE NDVI região erro: {e}")
        return None


def _classificar_fase(ndvi: float) -> str:
    """
    Interpretação do NDVI por cultura genérica.
    Valores calibrados para soja/milho — culturas predominantes.
    """
    if ndvi < 0.1:   return "solo_exposto"
    if ndvi < 0.2:   return "plantio_emergencia"
    if ndvi < 0.4:   return "vegetativo_inicial"
    if ndvi < 0.55:  return "vegetativo_pleno"
    if ndvi < 0.65:  return "florescimento"
    if ndvi < 0.75:  return "granacao"
    if ndvi < 0.5:   return "maturacao"
    return "vegetativo_avancado"


def _ndvi_simulado(lat: float, lon: float) -> dict:
    """
    Retorna NDVI simulado quando GEE não está configurado.
    Usado em desenvolvimento sem service account.
    """
    import hashlib
    seed = int(hashlib.md5(f"{lat:.3f}{lon:.3f}".encode()).hexdigest()[:8], 16)
    ndvi = 0.3 + (seed % 500) / 1000.0   # 0.30 – 0.80
    return {
        "ndvi_medio": round(ndvi, 4),
        "ndvi_std": 0.05,
        "fase_estimada": _classificar_fase(ndvi),
        "satelite": "simulado",
        "imagens_usadas": 0,
        "periodo_dias": 15,
        "anomalia_detectada": False,
        "simulado": True,
    }
