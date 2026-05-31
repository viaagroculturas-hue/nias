import tempfile
import unittest

from api.base import APIConnector, ConnectorError
from api.cache import LocalJSONCache
from core.fallback import NIADataHub


class FailingConnector(APIConnector):
    def __init__(self, cache):
        super().__init__("failing", "https://example.invalid", cache=cache)

    def _request(self, url, headers=None):
        raise RuntimeError("API indisponivel")


class ConnectorFallbackTest(unittest.TestCase):
    def test_data_hub_imports_all_default_connectors(self):
        hub = NIADataHub()

        self.assertEqual(hub.nasa_firms.name, "nasa_firms")
        self.assertEqual(hub.open_meteo.name, "open_meteo")
        self.assertEqual(hub.ibge.name, "ibge_sidra")
        self.assertEqual(hub.cepea.name, "cepea")

    def test_connector_uses_last_valid_cache_on_api_failure(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            cache = LocalJSONCache(tmp_path)
            cache.save("failing", "last-reading", {"ok": True}, source_url="https://example.invalid/data")

            result = FailingConnector(cache).get_json("data", cache_key="last-reading")

        self.assertEqual(result["data"], {"ok": True})
        self.assertEqual(result["meta"]["mode"], "fallback")
        self.assertTrue(result["meta"]["cached_at"])
        self.assertIn("API indisponivel", result["meta"]["error"])

    def test_connector_raises_when_api_fails_without_cache(self):
        with tempfile.TemporaryDirectory() as tmp_path:
            with self.assertRaises(ConnectorError):
                FailingConnector(LocalJSONCache(tmp_path)).get_json("data", cache_key="missing")


if __name__ == "__main__":
    unittest.main()
