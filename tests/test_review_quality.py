import unittest

from review_quality import filter_useful_reviews, is_useful_review


class TestReviewQuality(unittest.TestCase):
    def test_useful_filter_generic_short(self):
        raw_reviews = [
            "맛있어요",
            "맛있어요",
            "좋아요",
            "굿",
            "최고예요",
            "친절해요",
            "또 갈게요",
            "맛집",
            "좋습니다",
            "재방문할게요",
        ]
        out = filter_useful_reviews(raw_reviews)
        self.assertIn("reviewPatternStats", out)
        self.assertLessEqual(out["usefulReviewCount"], 1)
        self.assertGreaterEqual(out["droppedReviewCount"], 8)
        self.assertLess(out["reviewPatternStats"]["usefulReviewRatio"], 0.3)

    def test_useful_filter_concrete_all_keep(self):
        raw_reviews = [
            "삼겹살은 맛있는데 웨이팅이 길고 가격은 조금 비싸요",
            "분위기는 조용해서 데이트하기 좋고 주차는 힘들어요",
            "라멘 국물이 진하고 면 식감은 좋은데 점심 웨이팅이 길어요",
            "가격은 비싼 편이지만 양이 많고 고기가 부드러워요",
            "직원 응대는 친절했지만 주문 누락이 있었어요",
            "매장이 시끄러워서 조용한 대화는 어렵습니다",
        ]
        out = filter_useful_reviews(raw_reviews)
        self.assertEqual(out["usefulReviewCount"], 6)
        self.assertEqual(out["droppedReviewCount"], 0)

    def test_dict_review_preserved(self):
        raw_reviews = [
            {
                "text": "맛있어요",
                "date": "2026.04.01",
                "rating": 5.0,
                "reviewerReviewCount": 200,
                "reviewerAverageRating": 3.5,
            },
            {
                "text": "라멘 국물이 진하고 면 식감은 좋은데 점심 웨이팅이 길어요",
                "date": "2026.04.02",
                "rating": 4.0,
                "reviewerReviewCount": 50,
                "reviewerAverageRating": 3.8,
            },
        ]
        out = filter_useful_reviews(raw_reviews)
        self.assertEqual(out["usefulReviewCount"], 1)
        self.assertEqual(out["droppedReviewCount"], 1)

        useful = out["useful_reviews"][0]
        self.assertIsInstance(useful, dict)
        # meta preserved
        self.assertEqual(useful.get("date"), "2026.04.02")
        self.assertEqual(useful.get("rating"), 4.0)
        self.assertEqual(useful.get("reviewerReviewCount"), 50)
        self.assertEqual(useful.get("reviewerAverageRating"), 3.8)

    def test_no_concrete_when_only_standalone_digits(self):
        self.assertFalse(is_useful_review("999 12 44"))
        self.assertFalse(is_useful_review("2026.03.03. 555 777"))

    def test_concrete_when_number_with_meaningful_unit(self):
        self.assertTrue(is_useful_review("웨이팅 40분이라 좀 빡세지만 고기 자체는 괜찮았음"))
        self.assertTrue(is_useful_review("인당 15000 원 정도예요 적당히 맛있어요 여기가"))


if __name__ == "__main__":
    unittest.main()

