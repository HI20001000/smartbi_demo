import unittest
from datetime import datetime

from src.normalization import normalize_input


class NormalizeInputTests(unittest.TestCase):
    def setUp(self):
        self.user_context = {
            "user_id": "u-1",
            "role": "analyst",
            "data_scope": ["AGGREGATED_ONLY"],
            "allowed_regions": ["澳門半島"],
        }
        self.request_context = {
            "request_id": "req-1",
            "request_ts": "2026-02-11T10:00:00+08:00",
            "timezone": "Asia/Macau",
            "channel": "api",
        }

    def test_normalize_yesterday_balance(self):
        out = normalize_input(
            "昨天澳門半島存款餘額",
            self.user_context,
            self.request_context,
            now=datetime.fromisoformat("2026-02-11T10:00:00+08:00"),
        )
        self.assertEqual(out["schema_version"], "1.0")
        self.assertEqual(out["query_context"]["intent"], "kpi_query")
        self.assertEqual(out["time_context"]["resolved"]["type"], "single_date")
        self.assertIn("metric.deposit.total_end_balance", out["metric_hints"])

    def test_normalize_detail_request_sets_risk(self):
        out = normalize_input(
            "列出每個account_no的明細",
            self.user_context,
            self.request_context,
            now=datetime.fromisoformat("2026-02-11T10:00:00+08:00"),
        )
        self.assertTrue(out["risk_context"]["contains_sensitive_terms"])
        self.assertIn("pii_requested", out["risk_context"]["risk_flags"])


if __name__ == "__main__":
    unittest.main()
