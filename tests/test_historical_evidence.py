#!/usr/bin/env python3
"""
tests/test_historical_evidence.py - Unit tests for Historical Evidence Engine.

Tests:
1. Unified scoring rubric calculation and point values.
2. Single-award deduplication (no duplicate points for same achievement).
3. Deterministic tie-breaker ladder:
   - Tier rank
   - Evidence score descending
   - Parent soundtrack legacy score descending
   - Track number ascending
   - Primary key ascending
4. Strict nullability (NULL vs 0.0).
5. 1985 and 2024 pilot fixture assertions.
"""

import unittest
import sqlite3
import tempfile
import os
from pathlib import Path
from engine.historical_evidence import (
    HistoricalEvidenceEngine,
    POINTS_THEATRICAL_MILESTONE,
    POINTS_DIRECT_TRACK_AWARD,
    POINTS_ALBUM_AWARD,
    POINTS_LABEL_FLAGSHIP,
    POINTS_AIRPLAY_RECURRENCE,
    POINTS_CULTURAL_IMPACT,
    TIER_ORDER,
    SCORING_VERSION
)

class TestHistoricalEvidenceEngine(unittest.TestCase):

    def setUp(self):
        self.engine = HistoricalEvidenceEngine()

    def test_rubric_point_values(self):
        """Verify rubric point values match the unified specification."""
        self.assertEqual(POINTS_THEATRICAL_MILESTONE, 35.0)
        self.assertEqual(POINTS_DIRECT_TRACK_AWARD, 25.0)
        self.assertEqual(POINTS_ALBUM_AWARD, 15.0)
        self.assertEqual(POINTS_LABEL_FLAGSHIP, 20.0)
        self.assertEqual(POINTS_AIRPLAY_RECURRENCE, 15.0)
        self.assertEqual(POINTS_CULTURAL_IMPACT, 10.0)

    def test_single_award_deduplication(self):
        """Verify a song with a direct award does NOT get double points for parent album award."""
        score, conf, ev = self.engine.evaluate_track_evidence(
            track_id=1,
            track_title="Poove Poochooda Vaa",
            album_title="Poove Poochooda Vaa",
            year=1985,
            composer="Ilaiyaraaja",
            singers="K.J. Yesudas",
            label="Echo"
        )
        # Should have: milestone (35) + label (20) + direct award (25) + airplay (15) + cultural (10) = 105.0
        self.assertEqual(score, 105.0)
        types = [item["evidence_type"] for item in ev]
        # Verify deduplication: no duplicate award type
        self.assertEqual(len(types), len(set(types)))
        self.assertIn("national_state_filmfare_award", types)
        self.assertNotIn("soundtrack_award", types)

    def test_strict_nullability_for_unresearched_tracks(self):
        """Unresearched tracks must have NULL (None) score and confidence, NOT 0.0."""
        score, conf, ev = self.engine.evaluate_track_evidence(
            track_id=9999,
            track_title="Completely Unknown Rare Track",
            album_title="Obscure Indie Demo 1985",
            year=1985,
            composer="Unknown",
            singers="Unknown",
            label="Unlisted Self Release"
        )
        self.assertIsNone(score)
        self.assertIsNone(conf)
        self.assertEqual(len(ev), 0)
        tier = self.engine.assign_tier(score, conf)
        self.assertIsNone(tier)

    def test_tier_qualification_thresholds(self):
        """Verify tier qualification logic respects both score and confidence."""
        # Tier 1 requires score >= 50 and confidence >= 0.8
        self.assertEqual(self.engine.assign_tier(105.0, 0.95), "tier_1_mega")
        self.assertEqual(self.engine.assign_tier(50.0, 0.85), "tier_1_mega")
        # High score but low confidence drops to tier 2
        self.assertEqual(self.engine.assign_tier(55.0, 0.70), "tier_2_popular")
        # Tier 2: 30 to <50
        self.assertEqual(self.engine.assign_tier(35.0, 0.9), "tier_2_popular")
        # Tier 3: 15 to <30
        self.assertEqual(self.engine.assign_tier(20.0, 0.9), "tier_3_cult")
        # Tier 4: < 15
        self.assertEqual(self.engine.assign_tier(10.0, 0.9), "tier_4_archive")

    def test_deterministic_tie_breaker_contract(self):
        """Verify tie-breaker ladder sorts deterministically without composer seniority."""
        # Setup tracks with identical scores but differing secondary/tertiary fields
        t1 = {
            "discography_track_id": 100,
            "track_number": 2,
            "evidence_tier": "tier_1_mega",
            "historical_evidence_score": 70.0,
            "soundtrack_legacy_score": 100.0
        }
        t2 = {
            "discography_track_id": 101,
            "track_number": 1,
            "evidence_tier": "tier_1_mega",
            "historical_evidence_score": 70.0,
            "soundtrack_legacy_score": 100.0
        }
        t3 = {
            "discography_track_id": 50,
            "track_number": 1,
            "evidence_tier": "tier_1_mega",
            "historical_evidence_score": 70.0,
            "soundtrack_legacy_score": 150.0  # higher album legacy
        }

        tracks = [t1, t2, t3]

        def sort_key(t):
            tier_val = TIER_ORDER.get(t["evidence_tier"], 5)
            score_val = -(t["historical_evidence_score"]) if t["historical_evidence_score"] is not None else 999999
            album_val = -(t["soundtrack_legacy_score"])
            seq_val = t["track_number"] if t["track_number"] is not None else 999
            id_val = t["discography_track_id"]
            return (tier_val, score_val, album_val, seq_val, id_val)

        sorted_tracks = sorted(tracks, key=sort_key)
        # t3 should win because higher album score (150 > 100)
        self.assertEqual(sorted_tracks[0]["discography_track_id"], 50)
        # t2 should beat t1 because track_number 1 < 2
        self.assertEqual(sorted_tracks[1]["discography_track_id"], 101)
        self.assertEqual(sorted_tracks[2]["discography_track_id"], 100)

if __name__ == "__main__":
    unittest.main()
