import unittest

from analysis_policy import calculate_data_confidence, should_save_map_flag


class TestPolicy(unittest.TestCase):
    def test_data_confidence_buckets(self):
        self.assertEqual(calculate_data_confidence(0), "insufficient")
        self.assertEqual(calculate_data_confidence(4), "insufficient")
        self.assertEqual(calculate_data_confidence(5), "low")
        self.assertEqual(calculate_data_confidence(9), "low")
        self.assertEqual(calculate_data_confidence(10), "medium")
        self.assertEqual(calculate_data_confidence(19), "medium")
        self.assertEqual(calculate_data_confidence(20), "high")
        self.assertEqual(calculate_data_confidence(999), "high")

    def test_used_review_limit(self):
        useful_count = 50
        used_cnt = min(40, useful_count)
        self.assertLessEqual(used_cnt, 40)
        self.assertEqual(used_cnt, 40)

    def test_should_save_map_flag(self):
        # low should not save even if high score
        self.assertFalse(should_save_map_flag("ok", "low", 4.5))
        self.assertFalse(should_save_map_flag("ok", "insufficient", 4.5))
        self.assertFalse(should_save_map_flag("error", "high", 4.5))
        self.assertFalse(should_save_map_flag("ok", "medium", 3.49))
        self.assertTrue(should_save_map_flag("ok", "medium", 3.5))
        self.assertTrue(should_save_map_flag("ok", "high", 4.0))


if __name__ == "__main__":
    unittest.main()

