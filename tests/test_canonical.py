import unittest

from canonical import make_canonical_key, upsert_aliases, find_existing_doc


class FakeColl:
    def __init__(self, *, name_doc=None, key_doc=None):
        self._name_doc = name_doc
        self._key_doc = key_doc

    def find_one(self, filt: dict):
        if "name" in filt:
            d = self._name_doc
            return d if isinstance(d, dict) and d.get("name") == filt["name"] else None
        if "canonical_key" in filt:
            d = self._key_doc
            return d if isinstance(d, dict) and d.get("canonical_key") == filt["canonical_key"] else None
        return None


class TestCanonical(unittest.TestCase):
    def test_make_canonical_key_normalizes(self):
        k1 = make_canonical_key("가제", "서울 성동구  어딘가  1")
        k2 = make_canonical_key(" 가제 ", "서울 성동구 어딘가 1")
        self.assertEqual(k1, k2)
        self.assertIn("|", k1)
        self.assertLessEqual(len(k1), 240)

    def test_upsert_aliases_dedup_case_insensitive(self):
        existing = {"aliases": ["성수 감자탕", "가제"]}
        merged = upsert_aliases(existing, ["성수 감자탕", "가제 성수점", "가제"])
        self.assertIn("성수 감자탕", merged)
        self.assertIn("가제", merged)
        self.assertIn("가제 성수점", merged)
        self.assertEqual(len(merged), 3)

    def test_find_existing_doc_name_first(self):
        coll = FakeColl(
            name_doc={"name": "가제", "canonical_key": "k1"},
            key_doc={"name": "옛이름", "canonical_key": "k2"},
        )
        doc, fb = find_existing_doc(coll, "가제", "k2")
        self.assertFalse(fb)
        self.assertEqual(doc.get("name"), "가제")

    def test_find_existing_doc_fallback_key(self):
        coll = FakeColl(
            name_doc=None,
            key_doc={"name": "옛이름", "canonical_key": "k2"},
        )
        doc, fb = find_existing_doc(coll, "가제", "k2")
        self.assertTrue(fb)
        self.assertEqual(doc.get("canonical_key"), "k2")


if __name__ == "__main__":
    unittest.main()

