import unittest

from analysis_utils import sanitize_ai_result


class TestSanitize(unittest.TestCase):
    def test_sanitize_deep_shape_and_clamps(self):
        raw = {
            "realScore": "999",
            "eventProbability": "300",
            "details": {"taste": "good", "value": 0, "service": "4.2"},
            "mustTryMenus": "삼겹살",
            "vibeTags": None,
            "riskFlags": "Long Wait",
            "practicalInfo": "parking good",
        }
        out = sanitize_ai_result(raw, "deep")

        self.assertLessEqual(out["realScore"], 5.0)
        self.assertGreaterEqual(out["realScore"], 1.0)
        self.assertLessEqual(out["eventProbability"], 100)
        self.assertGreaterEqual(out["eventProbability"], 0)

        details = out["details"]
        for k in ("taste", "value", "service", "time", "hygiene"):
            self.assertIn(k, details)
            self.assertIsInstance(details[k], float)
            self.assertGreaterEqual(details[k], 1.0)
            self.assertLessEqual(details[k], 5.0)

        self.assertIsInstance(out["mustTryMenus"], list)
        self.assertIsInstance(out["vibeTags"], list)
        self.assertIsInstance(out["riskFlags"], list)

        self.assertIsInstance(out["practicalInfo"], dict)
        for k in ("parking", "waiting", "bestTime", "foreignerAccess"):
            self.assertIn(k, out["practicalInfo"])
            self.assertIsInstance(out["practicalInfo"][k], str)
            self.assertTrue(out["practicalInfo"][k])


if __name__ == "__main__":
    unittest.main()

