"""Guards for keyword_cluster.py tokenization + similarity (GitHub issue #11).

The tokenizer was [a-z0-9]+ — every non-ASCII letter split the word, so
"bürohaftpflicht" tokenized as ["rohaftpflicht"] and German keyword sets fell
apart before clustering even started. And exact-token Jaccard scored related
German compounds ("betriebshaftpflichtversicherung" vs "betriebshaftpflicht")
at 0.00, leaving the cannibalisation gate and the internal link map blind in
compounding languages. These tests pin the Unicode tokenizer and the
compound-aware similarity — including that English behaviour is unchanged.
"""
from __future__ import annotations

import unittest

from _helpers import import_script

kc = import_script("keyword_cluster.py")


class TestUnicodeTokenizer(unittest.TestCase):
    def test_umlauts_do_not_split_words(self):
        self.assertEqual(kc._tokenize("bürohaftpflicht"), {"bürohaftpflicht"})
        self.assertEqual(kc._tokenize("vermögensschaden"), {"vermögensschaden"})

    def test_accents_and_cyrillic_survive(self):
        self.assertEqual(kc._tokenize("assurance qualité"),
                         {"assurance", "qualité"})
        self.assertEqual(kc._tokenize("страхование бизнеса"),
                         {"страхование", "бизнеса"})

    def test_english_tokenization_unchanged(self):
        self.assertEqual(kc._tokenize("business liability insurance"),
                         {"business", "liability", "insurance"})

    def test_stopwords_and_short_tokens_still_dropped(self):
        self.assertEqual(kc._tokenize("the best insurance"), {"insurance"})


class TestCompoundAwareSimilarity(unittest.TestCase):
    def test_german_compound_pair_scores_high(self):
        # The issue's example: exact Jaccard was 0.00 for this pair.
        a = kc._tokenize("betriebshaftpflichtversicherung")
        b = kc._tokenize("betriebshaftpflicht")
        self.assertGreaterEqual(kc._lexical_similarity(a, b), 0.6,
                                "compound stem and its extension must score "
                                "at least at the cannibalisation threshold")

    def test_english_equivalent_parity(self):
        # "business liability insurance" vs "business liability" — the English
        # phrasing of the same relationship scores 2/3; German must not score 0.
        en = kc._lexical_similarity(
            kc._tokenize("business liability insurance"),
            kc._tokenize("business liability"))
        de = kc._lexical_similarity(
            kc._tokenize("betriebshaftpflichtversicherung"),
            kc._tokenize("betriebshaftpflicht"))
        self.assertGreater(en, 0.6)
        self.assertGreaterEqual(de, en - 0.1,
                                "German compounds must not score materially "
                                "below the equivalent English phrase")

    def test_no_containment_means_plain_jaccard(self):
        a = kc._tokenize("email marketing automation")
        b = kc._tokenize("email marketing software")
        self.assertEqual(kc._lexical_similarity(a, b), kc._jaccard(a, b),
                         "English sets without containment pairs must score "
                         "exactly as before the fix")

    def test_short_token_containment_is_not_a_match(self):
        # "preis" (5 chars) is inside "preisvergleich", but below the compound
        # floor — matching it would make "top" ~ "topology"-class noise.
        self.assertFalse(kc._tokens_match("preis", "preisvergleich"))
        self.assertTrue(kc._tokens_match("kosten", "unkosten"))

    def test_serp_url_overlap_still_uses_pure_jaccard(self):
        # URL sets are exact identities — containment matching would be wrong
        # there. Guard that _jaccard survives unchanged for that call site.
        urls_a = {"https://a.example/page", "https://b.example/page"}
        urls_b = {"https://a.example/page"}
        self.assertAlmostEqual(kc._jaccard(urls_a, urls_b), 0.5)


if __name__ == "__main__":
    unittest.main()
