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
            "decision": {
                "label": "go",
                "visitSafetyScore": "4.9",
                "oneLine": "Test line",
                "shortReason": "Because reviews",
            },
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
        self.assertTrue(all(isinstance(x, dict) for x in out["riskFlags"]))

        self.assertIsInstance(out["practicalInfo"], dict)
        for k in (
            "parking",
            "waiting",
            "soloFriendly",
            "groupFriendly",
            "dateFriendly",
            "foreignerAccess",
            "orderingDifficulty",
            "englishMenu",
            "bestTimeToVisit",
        ):
            self.assertIn(k, out["practicalInfo"])
            self.assertIsInstance(out["practicalInfo"][k], str)
            self.assertTrue(out["practicalInfo"][k])

        self.assertIn("decision", out)
        self.assertEqual(out["decision"]["label"], "GO")
        self.assertIn("confidence", out)

    def test_fast_score_meaning_normalized(self):
        out = sanitize_ai_result({"scoreMeaning": "wrong"}, "fast")
        self.assertEqual(out["scoreMeaning"], "review_risk_screening")

    def test_deep_insufficient_allows_null_visit_safety(self):
        raw = {
            "realScore": 3.0,
            "details": {"taste": 3, "value": 3, "service": 3, "time": 3, "hygiene": 3},
            "decision": {
                "label": "INSUFFICIENT_DATA",
                "visitSafetyScore": None,
                "oneLine": "x",
                "shortReason": "y",
            },
        }
        out = sanitize_ai_result(raw, "deep")
        self.assertIsNone(out["decision"]["visitSafetyScore"])


if __name__ == "__main__":
    unittest.main()
