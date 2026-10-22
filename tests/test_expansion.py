import unittest


class ExpansionTests(unittest.TestCase):
    def media(self, identifier, title, country="CN", **overrides):
        return {
            "id": identifier,
            "idMal": identifier + 100,
            "title": {"english": title},
            "synonyms": [],
            "countryOfOrigin": country,
            "averageScore": 80,
            "popularity": 1000,
            "duration": 20,
            "episodes": 12,
            "format": "ONA",
            "status": "FINISHED",
            "relations": {"edges": []},
            **overrides,
        }

    def test_selects_distinct_new_titles_and_does_not_count_episodes(self):
        from subtitle_api.expansion import plan_expansion

        existing = [{"slug": "existing", "title": {"romaji": "Known Anime"}, "id": 5}]
        candidates = [
            self.media(1, "Known Anime!"),
            self.media(2, "Another Anime", synonyms=["Known Anime"]),
            self.media(3, "New Donghua", episodes=500),
            self.media(3, "New Donghua", episodes=500),
            self.media(4, "New Japanese", "JP"),
        ]
        result = plan_expansion(existing, candidates, chinese=1, other=1)
        self.assertEqual(
            [item["anime_id"] for item in result["targets"]], ["anilist:3", "anilist:4"]
        )
        self.assertEqual(result["selected_distinct_anime"], 2)
        self.assertEqual(result["translated_distinct_anime"], 0)
        self.assertEqual(result["targets"][0]["status"], "source_required")

    def test_skips_sequels_prequels_and_shared_franchises(self):
        from subtitle_api.expansion import plan_expansion

        sequel = self.media(
            2,
            "Sequel",
            relations={
                "edges": [
                    {
                        "relationType": "PREQUEL",
                        "node": {
                            "id": 1,
                            "type": "ANIME",
                            "title": {"english": "Original"},
                        },
                    }
                ]
            },
        )
        prequel = self.media(
            3,
            "Earlier Story",
            relations={
                "edges": [
                    {
                        "relationType": "SEQUEL",
                        "node": {
                            "id": 1,
                            "type": "ANIME",
                            "title": {"english": "Original"},
                        },
                    }
                ]
            },
        )
        result = plan_expansion(
            [],
            [self.media(1, "Original"), sequel, prequel, self.media(4, "Independent")],
            chinese=2,
            other=0,
        )
        self.assertEqual({item["anilist_id"] for item in result["targets"]}, {1, 4})

    def test_keeps_shortfall_explicit_instead_of_padding_or_promising_quality(self):
        from subtitle_api.expansion import plan_expansion

        result = plan_expansion(
            [], [self.media(1, "Only One", averageScore=60)], chinese=300, other=200
        )
        self.assertEqual(result["shortfall"], {"CN": 299, "other": 200})
        self.assertFalse(result["ready_to_translate"])
        self.assertEqual(result["targets"][0]["ranking"]["score"], 60)

    def test_excludes_franchise_already_in_catalog_by_related_title(self):
        from subtitle_api.expansion import plan_expansion

        candidate = self.media(
            1,
            "New Name",
            relations={
                "edges": [
                    {
                        "relationType": "SEQUEL",
                        "node": {
                            "id": 99,
                            "type": "ANIME",
                            "title": {"english": "Existing Season"},
                        },
                    }
                ]
            },
        )
        result = plan_expansion(
            [{"slug": "exists", "title": {"english": "Existing Season"}}],
            [candidate],
            chinese=1,
            other=0,
        )
        self.assertEqual(result["selected_distinct_anime"], 0)

    def test_rank_is_deterministic_and_rejects_missing_identity(self):
        from subtitle_api.expansion import plan_expansion

        rows = [
            self.media(2, "Second", averageScore=75),
            self.media(1, "First", averageScore=95),
        ]
        first = plan_expansion([], rows, chinese=1, other=0)
        self.assertEqual(
            first, plan_expansion([], list(reversed(rows)), chinese=1, other=0)
        )
        self.assertEqual(first["targets"][0]["anilist_id"], 1)
        invalid = self.media(1, "Bad")
        invalid["id"] = None
        with self.assertRaises(ValueError):
            plan_expansion([], [invalid], chinese=1, other=0)

    def test_other_anime_relations_remain_unresolved_without_merging_works(self):
        from subtitle_api.expansion import plan_expansion

        related = self.media(
            1,
            "Independent Work",
            relations={
                "edges": [
                    {
                        "relationType": "OTHER",
                        "node": {
                            "id": 2,
                            "type": "ANIME",
                            "title": {"english": "Related Work"},
                        },
                    },
                    {
                        "relationType": "OTHER",
                        "node": {"id": 3, "type": "MANGA"},
                    },
                ]
            },
        )
        result = plan_expansion(
            [], [related, self.media(2, "Related Work")], chinese=2, other=0
        )
        self.assertEqual(result["selected_distinct_anime"], 2)
        self.assertEqual(
            result["counting_unit"],
            "distinct_anilist_works_with_conservative_franchise_screening",
        )
        self.assertFalse(result["franchise_identity_verified"])
        self.assertEqual(
            result["targets"][0]["relation_review_links"],
            [
                {
                    "relation": "OTHER",
                    "anilist_id": 2,
                    "source_url": "https://anilist.co/anime/2",
                    "status": "unresolved_franchise_identity",
                }
            ],
        )
        self.assertEqual(result["targets"][1]["relation_review_links"], [])
        self.assertIn("OTHER", result["quality_caveat"])


if __name__ == "__main__":
    unittest.main()
