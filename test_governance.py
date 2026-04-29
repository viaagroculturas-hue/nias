import os
import sqlite3
import tempfile
import unittest

from flv.governance import (
    canonical_source,
    filter_elite_feeds,
    has_south_america_focus,
    require_elite_source,
    south_america_scope,
    SourcePolicyError,
)


class GovernancePolicyTest(unittest.TestCase):
    def test_source_aliases_are_canonicalized(self):
        self.assertEqual(canonical_source("Reuters"), "Reuters")
        self.assertEqual(canonical_source("sidra-pam"), "IBGE")
        self.assertEqual(canonical_source("BCB/SGS"), "Banco Central")
        self.assertIsNone(canonical_source("NoticiasAgricolas"))

    def test_require_elite_source_fails_closed(self):
        with self.assertRaises(SourcePolicyError):
            require_elite_source("CONAB")
        with self.assertRaises(SourcePolicyError):
            require_elite_source(None)

    def test_feed_filter_rejects_non_elite_sources(self):
        approved, rejected = filter_elite_feeds(
            [
                ("Reuters", "https://example.test/reuters.rss"),
                ("NoticiasAgricolas", "https://example.test/agro.rss"),
            ]
        )

        self.assertEqual(approved, [("Reuters", "https://example.test/reuters.rss")])
        self.assertEqual(rejected, [("NoticiasAgricolas", "https://example.test/agro.rss")])

    def test_geographic_scope_ignores_user_location(self):
        scope = south_america_scope(user_location="Lisboa")

        self.assertEqual(scope["scope"], "south_america")
        self.assertIn("BR", scope["countries"])
        self.assertIn("AR", scope["countries"])
        self.assertTrue(scope["user_location_ignored"])

    def test_south_america_focus_detection(self):
        self.assertTrue(has_south_america_focus("Drought risk rises across Argentina"))
        self.assertTrue(has_south_america_focus("Market update", "https://news.test/south-america/soy"))
        self.assertFalse(has_south_america_focus("Wheat exports rise in Europe"))


class AdministrativeMemoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()

        from flv.collectors import crisis_watch

        self.crisis_watch = crisis_watch
        self.original_db_path = crisis_watch.DB_PATH
        crisis_watch.DB_PATH = self.tmp.name

        conn = sqlite3.connect(self.tmp.name)
        conn.execute(
            """
            CREATE TABLE flv_corporate_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_cnpj TEXT NOT NULL,
                company_name TEXT,
                change_type TEXT,
                change_subtype TEXT,
                old_value TEXT,
                new_value TEXT,
                change_date TEXT NOT NULL,
                source TEXT,
                confidence_score REAL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO flv_corporate_changes
            (company_cnpj, company_name, change_type, change_subtype, old_value, new_value, change_date, source, confidence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("123", "Agro Teste", "administrador", "saida", "A", "B", "2022-01-01", "junta_comercial", 0.9),
                ("123", "Agro Teste", "administrador", "entrada", "B", "C", "2023-01-01", "junta_comercial", 0.9),
                ("123", "Agro Teste", "sede", "alteracao", "SP", "GO", "2024-01-01", "diario_oficial", 0.8),
                ("123", "Agro Teste", "sede", "alteracao", "GO", "MT", "2025-01-01", "diario_oficial", 0.8),
                ("123", "Agro Teste", "objeto_social", "alteracao", "X", "Y", "2026-01-01", "junta_comercial", 0.7),
            ],
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.crisis_watch.DB_PATH = self.original_db_path
        os.unlink(self.tmp.name)

    def test_admin_history_is_retained_for_risk_patterns(self):
        watcher = self.crisis_watch.CrisisWatch()
        patterns = watcher._get_administrative_risk_patterns("123")

        self.assertEqual(patterns["total_changes_retained"], 5)
        self.assertEqual(patterns["type_counts"]["administrador"], 2)
        self.assertEqual(patterns["type_counts"]["sede"], 2)
        self.assertIn("rotatividade_de_gestao", patterns["fraud_or_mismanagement_flags"])
        self.assertIn("mudanca_recorrente_de_sede", patterns["fraud_or_mismanagement_flags"])
        self.assertLess(patterns["score_penalty"], 0)


if __name__ == "__main__":
    unittest.main()
