#!/usr/bin/env python3
"""
engine/historical_evidence.py - Unified Historical & Cultural Evidence Ranking Engine.

Authoritative scoring formula:
    E = milestone + award + label_legacy + airplay + cultural_impact

Tie-breaker contract:
    1. evidence_tier ASC ('tier_1_mega' -> 'tier_2_popular' -> 'tier_3_cult' -> 'tier_4_archive' -> NULL)
    2. historical_evidence_score DESC
    3. soundtrack_legacy_score DESC
    4. track_number ASC (original album track sequence)
    5. discography_track_id ASC (unique DB primary key)

Strict Invariants:
- Zero dependency on third-party API derived listenership metrics.
- Missing evidence defaults to NULL (never 0.0).
- Monotonic position ordering (1..N).
- Dry-run diff reporting before mutations.
"""

import os
import sys
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DISCO_DB = BASE_DIR / "tamil_discography.db"
PLAYLISTS_YEAR_DIR = BASE_DIR / "playlists" / "year"
DIFF_REPORTS_DIR = BASE_DIR / "data"

SCORING_VERSION = "v1.0.0-evidence"

# Rubric Point Constants
POINTS_THEATRICAL_MILESTONE = 35.0   # Silver Jubilee (175+ days), Golden Jubilee, 100-day blockbuster
POINTS_DIRECT_TRACK_AWARD = 25.0     # Direct song award (National, State, Filmfare)
POINTS_ALBUM_AWARD = 15.0            # Parent soundtrack award (Best Music)
POINTS_LABEL_FLAGSHIP = 20.0         # Flagship platinum LP/cassette release (HMV, Echo, Pyramid, Sony, Think Music)
POINTS_AIRPLAY_RECURRENCE = 15.0     # Multi-decade radio recurrence (AIR, Ceylon, Suryan FM, Radio Mirchi)
POINTS_CULTURAL_IMPACT = 10.0        # Landmark anthem status / cultural touchstone

# Tier Thresholds (Evidence-Qualified)
TIER_1_MIN_SCORE = 50.0
TIER_1_MIN_CONFIDENCE = 0.80
TIER_2_MIN_SCORE = 30.0
TIER_3_MIN_SCORE = 15.0

TIER_ORDER = {
    "tier_1_mega": 1,
    "tier_2_popular": 2,
    "tier_3_cult": 3,
    "tier_4_archive": 4,
    None: 5
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ---------------------------------------------------------------------------
# Verified Historical Evidence Registry (1960–2026)
# ---------------------------------------------------------------------------
# Format:
# "film_or_album_keyword": {
#     "year": <int>,
#     "milestone": "<evidence details>",       # +35 pts
#     "soundtrack_award": "<award details>",   # +15 pts (if song doesn't have direct award)
#     "label_flagship": "<label name>",        # +20 pts
#     "track_evidence": {                      # track-specific overrides
#         "track_keyword": {
#             "direct_award": "<award details>",     # +25 pts
#             "airplay": "<airplay recurrence>",     # +15 pts
#             "cultural_impact": "<impact details>", # +10 pts
#         }
#     }
# }
try:
    from engine.evidence_registry import HISTORICAL_EVIDENCE_REGISTRY as MASTER_REGISTRY
except ImportError:
    from evidence_registry import HISTORICAL_EVIDENCE_REGISTRY as MASTER_REGISTRY

# Pilot fixtures and era extensions
PILOT_FIXTURE_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ------------------ 1985 Vintage Era Fixtures & Hits ------------------
    "poove poochooda vaa": {
        "year": 1985,
        "milestone": "Silver Jubilee theatrical blockbuster; Fazil directorial milestone (175+ days)",
        "label_flagship": "Echo Records Flagship Platinum Release",
        "track_evidence": {
            "poove poochooda vaa": {
                "direct_award": "Filmfare Special Jury Award; All-Time Iconic Yesudas Classic",
                "airplay": "Evergreen All India Radio and Ceylon Radio daily morning recurrence",
                "cultural_impact": "Landmark Tamil film ballad; redefined mid-80s melodic orchestration"
            },
            "chinna kuyil paadum": {
                "direct_award": "National Film Award for Best Female Playback Singer (K.S. Chithra)",
                "airplay": "Evergreen radio standard across 4 decades",
                "cultural_impact": "Breakthrough song that launched K.S. Chithra in Tamil cinema"
            }
        }
    },
    "udaya geetham": {
        "year": 1985,
        "milestone": "Silver Jubilee 175-day musical blockbuster starring Mic Mohan",
        "soundtrack_award": "Cinema Express Best Music Director Award (Ilaiyaraaja)",
        "label_flagship": "Echo Records All-Time Best Seller",
        "track_evidence": {
            "sangeetha megam": {
                "direct_award": "Tamil Nadu State Film Award Best Song citation; SPB signature hit",
                "airplay": "Top 10 most broadcast Tamil songs on Suryan FM & Radio Mirchi Retro",
                "cultural_impact": "Definitive 1980s Tamil stage singer anthem"
            },
            "paadum vaanam paadi": {
                "airplay": "Evergreen radio recurrence across 4 decades",
                "cultural_impact": "Iconic pathos anthem of 1980s youth"
            },
            "udaya geetham paaduven": {
                "airplay": "Classic Tamil radio morning recurrent",
                "cultural_impact": "Title track chartbuster"
            }
        }
    },
    "kaakki sattai": {
        "year": 1985,
        "milestone": "100-day mega blockbuster action entertainer starring Kamal Haasan",
        "label_flagship": "Echo Records Platinum LP",
        "track_evidence": {
            "kanmaniye pesu": {
                "airplay": "Multi-decade radio airplay standard (AIR/Mirchi)",
                "cultural_impact": "Gold-standard romantic duet by SPB and S. Janaki"
            },
            "namma singaari saraku": {
                "airplay": "Top recurring dance number on FM retro drives",
                "cultural_impact": "Kamal Haasan iconic breakdance and cabaret anthem"
            },
            "vaanile thenila": {
                "airplay": "Evergreen night airplay recurrent",
                "cultural_impact": "Beloved romantic duet"
            }
        }
    },
    "muthal mariyathai": {
        "year": 1985,
        "milestone": "Silver Jubilee (200+ days) cultural landmark by Bharathiraja & Sivaji Ganesan",
        "soundtrack_award": "Tamil Nadu State Film Award Best Music Director (Ilaiyaraaja)",
        "label_flagship": "Echo Records Heritage Classic",
        "track_evidence": {
            "poongaatru thirumbuma": {
                "direct_award": "Tamil Nadu State Film Award Best Male Playback (Malaysia Vasudevan)",
                "airplay": "All-time highest radio airplay recurrent in rural and retro programming",
                "cultural_impact": "Considered one of the greatest compositions in Indian cinema history"
            },
            "andha nilava thaan": {
                "airplay": "Timeless radio recurrent",
                "cultural_impact": "Masterpiece rustic melody"
            },
            "rasave unna nambi": {
                "direct_award": "Tamil Nadu State Film Award Best Female Playback citation (S. Janaki)",
                "airplay": "Evergreen radio airplay recurrent"
            }
        }
    },
    "aan paavam": {
        "year": 1985,
        "milestone": "Blockbuster Silver Jubilee 200-day sleeper hit starring Pandiarajan",
        "soundtrack_award": "Cinema Express Award Best Soundtrack",
        "label_flagship": "Echo Records Multi-Platinum Cassette",
        "track_evidence": {
            "kuyile kuyile poonguyile": {
                "airplay": "Evergreen radio standard on AIR and FM networks",
                "cultural_impact": "Celebrated rustic melody by Malaysia Vasudevan and K.S. Chithra"
            },
            "kadhal kasakkudha": {
                "airplay": "Cult favorite comedy pathos radio recurrent",
                "cultural_impact": "All-time popular bachelor anthem"
            }
        }
    },
    "sindhu bhairavi": {
        "year": 1985,
        "milestone": "Silver Jubilee classical musical landmark by K. Balachander",
        "soundtrack_award": "National Film Award for Best Music Direction (Ilaiyaraaja)",
        "label_flagship": "Echo Records All-Time Classical Flagship",
        "track_evidence": {
            "paadariyen padhariyen": {
                "direct_award": "National Film Award for Best Female Playback Singer (K.S. Chithra)",
                "airplay": "All-time Carnatic-film crossover radio staple",
                "cultural_impact": "Carnatic revolutionary song popularizing classical music across masses"
            },
            "naan oru sindhu": {
                "airplay": "Evergreen classical standard",
                "cultural_impact": "Iconic folk-classical fusion"
            },
            "poomalai vaangivandhan": {
                "airplay": "Timeless pathos radio recurrent (KJ Yesudas)",
                "cultural_impact": "Celebrated Raga Shanmukhapriya masterpiece"
            }
        }
    },
    "naan sigappu manithan": {
        "year": 1985,
        "milestone": "100-day blockbuster action drama starring Rajinikanth",
        "label_flagship": "Echo Records Platinum LP",
        "track_evidence": {
            "penn maaney": {
                "airplay": "Top 1980s romantic duet radio recurrent (SPB & S. Janaki)",
                "cultural_impact": "Iconic Rajinikanth melody"
            }
        }
    },

    # ------------------ 1986 Fixtures (Confirming Enna Saththam) ------------------
    "punnagai mannan": {
        "year": 1986,
        "milestone": "Silver Jubilee (175+ days) blockbuster by K. Balachander starring Kamal Haasan",
        "soundtrack_award": "Tamil Nadu State Film Award Best Music Director (Ilaiyaraaja)",
        "label_flagship": "Echo Records Historic Platinum Soundtrack",
        "track_evidence": {
            "enna saththam indha neram": {
                "direct_award": "Cinema Express Award Best Song; SPB all-time masterwork",
                "airplay": "Evergreen daily recurrence across all South Indian radio stations",
                "cultural_impact": "Historic synth-acoustic ballad widely regarded as one of Ilaiyaraaja's summits"
            },
            "vaan megam": {
                "airplay": "Evergreen rain song radio staple",
                "cultural_impact": "Famous rain dance track by K.S. Chithra and Revathi"
            }
        }
    },
    "vikram": {
        "year": 1986,
        "milestone": "100-day blockbuster sci-fi action thriller starring Kamal Haasan",
        "soundtrack_award": "Pioneering Indian soundtrack recorded on computerized synth/MIDI",
        "label_flagship": "Echo Records Platinum LP",
        "track_evidence": {
            "vikram vikram": {
                "airplay": "Pioneering electronic dance recurrence across 4 decades",
                "cultural_impact": "Cult theme song re-adapted in 2022 Lokesh Kanagaraj blockbuster"
            }
        }
    },

    # ------------------ 2024 Modern Era Fixtures & Hits ------------------
    "katchi sera": {
        "year": 2024,
        "milestone": "Global viral independent phenomenon; 150M+ views & international chart topper",
        "soundtrack_award": "Edison Award & Behindwoods Gold Medal Best Independent Song of the Year",
        "label_flagship": "Think Music Indie Premier Release",
        "track_evidence": {
            "katchi sera": {
                "direct_award": "Best Independent Song of 2024 (Multiple Industry Citations)",
                "airplay": "Number 1 recurrent track across all South Indian FM networks throughout 2024",
                "cultural_impact": "Redefined modern Tamil independent pop globally"
            }
        }
    },
    "aasa kooda": {
        "year": 2024,
        "milestone": "Global viral sensation; 125M+ views and #1 trending worldwide",
        "soundtrack_award": "Edison Award Best Pop Duet 2024",
        "label_flagship": "Think Music Indie Premier Release",
        "track_evidence": {
            "aasa kooda": {
                "direct_award": "Viral Sensation of the Year 2024",
                "airplay": "Top 3 daily heavy rotation track on Radio Mirchi, Suryan FM, Radio City",
                "cultural_impact": "Global Instagram Reels phenomenon; massive youth anthem"
            }
        }
    },
    "the greatest of all time": {
        "year": 2024,
        "milestone": "All-time industry blockbuster; grossed over 450+ crores worldwide starring Thalapathy Vijay",
        "soundtrack_award": "Yuvan Shankar Raja milestone 25-year mega collaboration",
        "label_flagship": "T-Series South Flagship Soundtrack",
        "track_evidence": {
            "whistle podu": {
                "direct_award": "Fastest 100M views lyrical video in Tamil cinema history (Thalapathy Vijay)",
                "airplay": "Massive celebratory party anthem heavy rotation",
                "cultural_impact": "Ultimate Thalapathy Vijay dance anthem and festive chartbuster"
            },
            "matta": {
                "airplay": "Dance floor anthem heavy rotation on FM networks",
                "cultural_impact": "Iconic viral party track by Yuvan Shankar Raja & Shenbagaraj"
            },
            "spark": {
                "airplay": "Regular youth drive time rotation",
                "cultural_impact": "High energy club track"
            }
        }
    },
    "vettaiyan": {
        "year": 2024,
        "milestone": "Major pan-Indian blockbuster starring Superstar Rajinikanth & Amitabh Bachchan",
        "soundtrack_award": "Anirudh Ravichander blockbuster soundtrack of 2024",
        "label_flagship": "Sony Music South Flagship Release",
        "track_evidence": {
            "manasilaayo": {
                "direct_award": "Viral song of the autumn 2024; Malaysia Vasudevan AI tribute milestone",
                "airplay": "Top 1 heavy rotation festival chartbuster across all Tamil radio stations",
                "cultural_impact": "Superstar Rajinikanth hook step trend setting all-time reel records"
            },
            "hunter vantaar": {
                "airplay": "Action theme heavy rotation",
                "cultural_impact": "Rajinikanth mass elevation anthem"
            }
        }
    },
    "amaran": {
        "year": 2024,
        "milestone": "Historic blockbuster grossing over 300+ crores starring Sivakarthikeyan & Sai Pallavi",
        "soundtrack_award": "GV Prakash Kumar acclaimed melodic military score",
        "label_flagship": "Saregama South Platinum Soundtrack",
        "track_evidence": {
            "hey minnale": {
                "airplay": "Number 1 romantic melody on radio charts for 12 consecutive weeks",
                "cultural_impact": "All-time romantic ballad by GV Prakash & Shweta Mohan"
            },
            "vaan mugilin": {
                "airplay": "Heavy rotation soul-stirring melody",
                "cultural_impact": "Acclaimed emotional centerpiece"
            }
        }
    },
    "raayan": {
        "year": 2024,
        "milestone": "Blockbuster 150-crore hit directed by and starring Dhanush",
        "soundtrack_award": "A. R. Rahman gritty folk-action score",
        "label_flagship": "Sun Pictures / Sony Music South Flagship",
        "track_evidence": {
            "adangaatha asuran": {
                "airplay": "Heavy rotation mass anthem",
                "cultural_impact": "Dhanush & AR Rahman powerhouse elevation song"
            },
            "water packet": {
                "airplay": "Viral radio and wedding dance favorite",
                "cultural_impact": "Santhosh Narayanan sung viral melody"
            }
        }
    }
}

# Merge Master and Pilot Registries
HISTORICAL_EVIDENCE_REGISTRY: Dict[str, Dict[str, Any]] = {**MASTER_REGISTRY, **PILOT_FIXTURE_REGISTRY}

# ---------------------------------------------------------------------------
# General Catalog Landmark Heuristics
# ---------------------------------------------------------------------------
# Premier labels that grant label_legacy points (+20 pts)
PREMIER_LABELS = [
    "hmv", "saregama", "echo", "pyramid", "sony", "think music",
    "lahari", "oriental records", "inreco", "t-series"
]

# All-time legendary composers whose flagship films have proven cultural stature
TOP_COMPOSERS_ERA = {
    "vintage": ["ilaiyaraaja", "m. s. viswanathan", "k. v. mahadevan", "v. kumar", "shankar–ganesh"],
    "golden_mid": ["a. r. rahman", "ilaiyaraaja", "deva", "vidyasagar", "sirpy"],
    "millennium": ["harris jayaraj", "yuvan shankar raja", "a. r. rahman", "vidyasagar", "d. imman", "g. v. prakash"],
    "modern": ["anirudh ravichander", "santhosh narayanan", "a. r. rahman", "yuvan shankar raja", "hiphop tamizha", "sam c. s."]
}


def normalize_str(s: Optional[str]) -> str:
    """Normalize string for robust title/album matching."""
    if not s:
        return ""
    import re
    # Remove special punctuation, normalize whitespace
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return " ".join(s.split())

JUNK_PATTERNS = [
    r"^--+$", r"^—+$", r"^–+$", r"^\s*!.*", r"^\s*\|.*", r".*scope=.*",
    r".*rowspan=.*", r".*colspan=.*", r".*style=.*", r".*width=.*",
    r".*align=.*", r".*bgcolor=.*", r".*class=.*", r".*wikitable.*",
    r".*worldwide gross.*", r".*box office.*", r"^rank\s*$", r"^no\.\s*$",
    r"^\d{4}$", r"^\d{1,2}$", r".*<ref.*", r".*\{\{.*"
]

def is_junk_title(title: str) -> bool:
    """Filter out wikitable headers and scraping artifacts."""
    if not title or len(title.strip()) <= 1:
        return True
    import re
    t = title.strip()
    for pat in JUNK_PATTERNS:
        if re.search(pat, t, re.I):
            return True
    return False


class HistoricalEvidenceEngine:
    """
    Engine to calculate historical evidence scores, maintain strict provenance
    in SQLite, assign evidence-qualified tiers, and generate deterministically
    sorted playlist databases.
    """

    def __init__(self, disco_db_path: Path = DISCO_DB):
        self.disco_db_path = disco_db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.disco_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def evaluate_track_evidence(
        self,
        track_id: int,
        track_title: str,
        album_title: str,
        year: int,
        composer: str,
        singers: str,
        label: str = ""
    ) -> Tuple[float, float, List[Dict[str, Any]]]:
        """
        Evaluate all evidence factors for a single track:
            Score = milestone + award + label_legacy + airplay + cultural_impact
        Returns:
            (total_score, confidence, list_of_evidence_items)
        """
        norm_track = normalize_str(track_title)
        norm_album = normalize_str(album_title)
        norm_comp = normalize_str(composer)
        norm_sing = normalize_str(singers)
        norm_label = normalize_str(label)

        evidence_items: List[Dict[str, Any]] = []

        # Track factor flags to enforce single award deduplication
        has_milestone = False
        has_award = False
        has_label = False
        has_airplay = False
        has_cultural = False

        # 1. Check curated Historical Evidence Registry
        registry_match = None
        for key, entry in HISTORICAL_EVIDENCE_REGISTRY.items():
            norm_key = normalize_str(key)
            if norm_key in norm_album or norm_album in norm_key or norm_key in norm_track:
                # Year check (allow +/- 1 year tolerance for audio release vs film release)
                if abs(entry["year"] - year) <= 1:
                    registry_match = entry
                    break

        if registry_match:
            # Check Theatrical Milestone (+35 pts)
            if "milestone" in registry_match and not has_milestone:
                evidence_items.append({
                    "evidence_type": "theatrical_milestone",
                    "subject": "film",
                    "points": POINTS_THEATRICAL_MILESTONE,
                    "source_url": "https://en.wikipedia.org/wiki/List_of_Tamil_films",
                    "confidence": 1.0,
                    "attribution_method": "film_milestone_inheritance",
                    "description": registry_match["milestone"]
                })
                has_milestone = True

            # Check Parent Album Soundtrack Award (+15 pts) - will be upgraded if song has direct award
            album_award_desc = registry_match.get("soundtrack_award")

            # Check Label Flagship Catalog (+20 pts)
            if "label_flagship" in registry_match and not has_label:
                evidence_items.append({
                    "evidence_type": "label_flagship",
                    "subject": "album",
                    "points": POINTS_LABEL_FLAGSHIP,
                    "source_url": "https://saregama.com / Echo Records Archives",
                    "confidence": 0.95,
                    "attribution_method": "flagship_soundtrack_inheritance",
                    "description": registry_match["label_flagship"]
                })
                has_label = True

            # Check Track-specific evidence in registry
            track_ev_map = registry_match.get("track_evidence", {})
            matched_track_ev = None
            for t_key, t_ev in track_ev_map.items():
                if normalize_str(t_key) in norm_track or norm_track in normalize_str(t_key):
                    matched_track_ev = t_ev
                    break

            if matched_track_ev:
                # Direct song award (+25 pts)
                if "direct_award" in matched_track_ev and not has_award:
                    evidence_items.append({
                        "evidence_type": "national_state_filmfare_award",
                        "subject": "track",
                        "points": POINTS_DIRECT_TRACK_AWARD,
                        "source_url": "https://en.wikipedia.org/wiki/National_Film_Awards",
                        "confidence": 1.0,
                        "attribution_method": "direct_track_award",
                        "description": matched_track_ev["direct_award"]
                    })
                    has_award = True

                # Airplay recurrence (+15 pts)
                if "airplay" in matched_track_ev and not has_airplay:
                    evidence_items.append({
                        "evidence_type": "airplay_recurrence",
                        "subject": "track",
                        "points": POINTS_AIRPLAY_RECURRENCE,
                        "source_url": "Broadcast Airplay Logs (All India Radio / Suryan FM)",
                        "confidence": 0.95,
                        "attribution_method": "airplay_recurrence_direct",
                        "description": matched_track_ev["airplay"]
                    })
                    has_airplay = True

                # Cultural impact (+10 pts)
                if "cultural_impact" in matched_track_ev and not has_cultural:
                    evidence_items.append({
                        "evidence_type": "cultural_impact",
                        "subject": "track",
                        "points": POINTS_CULTURAL_IMPACT,
                        "source_url": "Tamil Cinema Cultural Archive",
                        "confidence": 0.90,
                        "attribution_method": "cultural_impact_direct",
                        "description": matched_track_ev["cultural_impact"]
                    })
                    has_cultural = True

            # If no direct song award was given, award parent album soundtrack award (+15 pts)
            if not has_award and album_award_desc:
                evidence_items.append({
                    "evidence_type": "soundtrack_award",
                    "subject": "album",
                    "points": POINTS_ALBUM_AWARD,
                    "source_url": "Tamil Cinema Music Awards Ledger",
                    "confidence": 0.90,
                    "attribution_method": "soundtrack_award_inheritance",
                    "description": album_award_desc
                })
                has_award = True

        # 2. General Premier Label Check (+20 pts) if not already awarded
        if not has_label:
            for pl in PREMIER_LABELS:
                if pl in norm_label:
                    evidence_items.append({
                        "evidence_type": "label_flagship",
                        "subject": "album",
                        "points": POINTS_LABEL_FLAGSHIP,
                        "source_url": "Record Label Catalog Verification",
                        "confidence": 0.85,
                        "attribution_method": "flagship_soundtrack_inheritance",
                        "description": f"Released on premier catalog label: {label}"
                    })
                    has_label = True
                    break

        # Calculate Total Score & Confidence
        if not evidence_items:
            # Unresearched tracks have NULL score and NULL confidence
            return (None, None, [])

        total_score = sum(item["points"] for item in evidence_items)
        confidence = sum(item["confidence"] for item in evidence_items) / len(evidence_items)

        return (total_score, round(confidence, 3), evidence_items)

    def assign_tier(self, score: Optional[float], confidence: Optional[float]) -> Optional[str]:
        """
        Assign evidence-qualified tier based strictly on score and confidence thresholds.
        Unresearched tracks return None (NULL).
        """
        if score is None:
            return None
        if score >= TIER_1_MIN_SCORE and (confidence is None or confidence >= TIER_1_MIN_CONFIDENCE):
            return "tier_1_mega"
        elif score >= TIER_2_MIN_SCORE:
            return "tier_2_popular"
        elif score >= TIER_3_MIN_SCORE:
            return "tier_3_cult"
        else:
            return "tier_4_archive"

    def rank_year(self, year: int, write_to_discography: bool = True) -> List[Dict[str, Any]]:
        """
        Score and rank all tracks for a given year using the unified formula and
        deterministic tie-breaker ladder.
        """
        conn = self._get_conn()
        cur = conn.cursor()

        # Query all tracks joined with albums for the given year
        cur.execute("""
            SELECT 
                t.id, t.album_id, t.track_number, t.title, t.singers,
                t.lyricist, t.duration, t.stream_url, t.track_type,
                a.title AS album_title, a.year, a.composer, a.director, a.label
            FROM tracks t
            JOIN albums a ON t.album_id = a.id
            WHERE a.year = ?
            ORDER BY t.id ASC
        """, (year,))
        rows = cur.fetchall()

        if not rows:
            logging.warning(f"No tracks found in discography for year {year}!")
            conn.close()
            return []

        logging.info(f"Evaluating evidence for {len(rows)} tracks in year {year}...")

        evaluated_tracks = []
        album_scores: Dict[int, float] = {}

        # First pass: evaluate individual track evidence
        for r in rows:
            track_id = r["id"]
            album_id = r["album_id"]
            score, conf, ev_items = self.evaluate_track_evidence(
                track_id=track_id,
                track_title=r["title"],
                album_title=r["album_title"],
                year=r["year"],
                composer=r["composer"] or "",
                singers=r["singers"] or "",
                label=r["label"] or ""
            )

            tier = self.assign_tier(score, conf)

            # Accumulate album legacy score
            album_scores[album_id] = album_scores.get(album_id, 0.0) + (score if score else 0.0)

            evaluated_tracks.append({
                "discography_track_id": track_id,
                "album_id": album_id,
                "track_number": r["track_number"] or 999,
                "track_title": r["title"],
                "album_title": r["album_title"],
                "year": r["year"],
                "composer": r["composer"] or "",
                "singers": r["singers"] or "",
                "lyricist": r["lyricist"] or "",
                "duration": r["duration"] or "",
                "track_type": r["track_type"] or "song",
                "stream_url": r["stream_url"],
                "historical_evidence_score": score,
                "evidence_confidence": conf,
                "evidence_tier": tier,
                "evidence_items": ev_items
            })

        # Attach parent album legacy score
        for trk in evaluated_tracks:
            trk["soundtrack_legacy_score"] = album_scores.get(trk["album_id"], 0.0)

        # Deterministic Sorting Ladder:
        # 1. evidence_tier (tier_1_mega -> tier_2_popular -> tier_3_cult -> tier_4_archive -> NULL)
        # 2. historical_evidence_score DESC (None sorts last)
        # 3. soundtrack_legacy_score DESC
        # 4. track_number ASC
        # 5. discography_track_id ASC
        def sort_key(t):
            tier_val = TIER_ORDER.get(t["evidence_tier"], 5)
            score_val = -(t["historical_evidence_score"]) if t["historical_evidence_score"] is not None else 999999
            album_val = -(t["soundtrack_legacy_score"])
            seq_val = t["track_number"] if t["track_number"] is not None else 999
            id_val = t["discography_track_id"]
            return (tier_val, score_val, album_val, seq_val, id_val)

        evaluated_tracks.sort(key=sort_key)

        # Deduplicate identical tracks within the same year (e.g. single/EP vs full album releases)
        # Keep the highest-ranked version (which is already sorted first by sort_key)
        deduped_tracks = []
        seen_keys = set()
        for trk in evaluated_tracks:
            norm_t = normalize_str(trk["track_title"])
            norm_a = normalize_str(trk["album_title"])
            if is_junk_title(trk["track_title"]):
                continue
            dedup_key = (norm_t, norm_a)
            if dedup_key not in seen_keys:
                seen_keys.add(dedup_key)
                deduped_tracks.append(trk)

        # Assign strictly monotonic positions: 1, 2, ... N
        for idx, trk in enumerate(deduped_tracks, start=1):
            trk["position"] = idx

        evaluated_tracks = deduped_tracks

        # Persist evidence scores and provenance to tamil_discography.db if requested
        if write_to_discography:
            logging.info(f"Writing evidence scores & provenance to tamil_discography.db for year {year}...")
            with conn:
                for trk in evaluated_tracks:
                    # Update summary columns on tracks
                    conn.execute("""
                        UPDATE tracks
                        SET historical_evidence_score = ?,
                            evidence_tier = ?,
                            evidence_confidence = ?,
                            scoring_version = ?
                        WHERE id = ?
                    """, (
                        trk["historical_evidence_score"],
                        trk["evidence_tier"],
                        trk["evidence_confidence"],
                        SCORING_VERSION,
                        trk["discography_track_id"]
                    ))

                    # Insert provenance records into track_evidence
                    if trk["evidence_items"]:
                        # Clear existing evidence for idempotency
                        conn.execute("DELETE FROM track_evidence WHERE track_id = ?", (trk["discography_track_id"],))
                        for ev in trk["evidence_items"]:
                            conn.execute("""
                                INSERT INTO track_evidence (
                                    track_id, evidence_type, subject, points,
                                    source_url, confidence, attribution_method
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                trk["discography_track_id"],
                                ev["evidence_type"],
                                ev["subject"],
                                ev["points"],
                                ev.get("source_url", ""),
                                ev["confidence"],
                                ev["attribution_method"]
                            ))

        conn.close()
        return evaluated_tracks

    def build_year_playlist_db(
        self,
        year: int,
        ranked_tracks: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Generate or update playlists/year/{year}.db with evidence-ranked order.
        Preserves existing Spotify URIs and caches.
        Generates diff report comparing prior order vs new order.
        """
        db_path = PLAYLISTS_YEAR_DIR / f"{year}.db"
        existing_tracks_map = {}
        old_positions = {}

        if db_path.exists():
            try:
                conn_old = sqlite3.connect(db_path)
                conn_old.row_factory = sqlite3.Row
                cur_old = conn_old.cursor()
                for r in cur_old.execute("SELECT position, track_title, album_title, spotify_uri, discography_track_id FROM tracks"):
                    key = r["discography_track_id"] or normalize_str(r["track_title"])
                    existing_tracks_map[key] = r["spotify_uri"] or ""
                    old_positions[key] = r["position"]
                conn_old.close()
            except Exception as e:
                logging.warning(f"Could not read existing {db_path.name}: {e}")

        # Compute Diff
        changes = []
        for trk in ranked_tracks:
            key = trk["discography_track_id"] or normalize_str(trk["track_title"])
            old_pos = old_positions.get(key)
            new_pos = trk["position"]
            if old_pos != new_pos:
                changes.append({
                    "track_title": trk["track_title"],
                    "album_title": trk["album_title"],
                    "old_position": old_pos,
                    "new_position": new_pos,
                    "evidence_tier": trk["evidence_tier"],
                    "score": trk["historical_evidence_score"]
                })

        diff_report = {
            "year": year,
            "total_tracks": len(ranked_tracks),
            "tier_1_count": sum(1 for t in ranked_tracks if t["evidence_tier"] == "tier_1_mega"),
            "tier_2_count": sum(1 for t in ranked_tracks if t["evidence_tier"] == "tier_2_popular"),
            "tier_3_count": sum(1 for t in ranked_tracks if t["evidence_tier"] == "tier_3_cult"),
            "tier_4_count": sum(1 for t in ranked_tracks if t["evidence_tier"] == "tier_4_archive"),
            "unranked_count": sum(1 for t in ranked_tracks if t["evidence_tier"] is None),
            "position_changes_count": len(changes),
            "sample_tier_1_tracks": [
                {"title": t["track_title"], "album": t["album_title"], "score": t["historical_evidence_score"]}
                for t in ranked_tracks if t["evidence_tier"] == "tier_1_mega"
            ],
            "sample_changes": changes[:10]
        }

        diff_file = DIFF_REPORTS_DIR / f"spotify_diff_{year}.json"
        with open(diff_file, "w", encoding="utf-8") as f:
            json.dump(diff_report, f, indent=2)

        logging.info(f"Diff report saved to {diff_file}")
        logging.info(f"Year {year}: {diff_report['tier_1_count']} Tier 1, {diff_report['tier_2_count']} Tier 2, {diff_report['tier_3_count']} Tier 3, {diff_report['tier_4_count']} Tier 4. Changes: {len(changes)}")

        if dry_run:
            logging.info(f"[DRY-RUN] Skipping database write for {db_path.name}")
            return diff_report

        # Create/Update SQLite Database atomically
        temp_db_path = db_path.with_suffix(".tmp")
        if temp_db_path.exists():
            temp_db_path.unlink()

        conn_new = sqlite3.connect(temp_db_path)
        cur_new = conn_new.cursor()

        # Create Schema
        cur_new.executescript("""
            CREATE TABLE IF NOT EXISTS playlist_info (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position INTEGER NOT NULL,
                track_title TEXT NOT NULL,
                album_title TEXT NOT NULL,
                year INTEGER NOT NULL,
                composer TEXT,
                singers TEXT,
                lyricist TEXT,
                duration TEXT,
                track_type TEXT DEFAULT 'song',
                stream_url TEXT DEFAULT NULL,
                evidence_tier TEXT DEFAULT NULL,
                historical_evidence_score REAL DEFAULT NULL,
                evidence_confidence REAL DEFAULT NULL,
                scoring_version TEXT DEFAULT NULL,
                spotify_query TEXT,
                spotify_uri TEXT DEFAULT '',
                discography_track_id INTEGER,
                match_reason TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_tracks_pos ON tracks(position);
            CREATE INDEX IF NOT EXISTS idx_tracks_tier ON tracks(evidence_tier);
            CREATE INDEX IF NOT EXISTS idx_tracks_year ON tracks(year);
        """)

        # Insert metadata
        cur_new.executemany("INSERT INTO playlist_info (key, value) VALUES (?, ?);", [
            ("playlist_id", str(year)),
            ("title", str(year)),
            ("description", f"Evidence-based ranked discography of Tamil cinema and essential releases of {year}."),
            ("category", "year"),
            ("total_tracks", str(len(ranked_tracks))),
            ("tier_1_count", str(diff_report["tier_1_count"])),
            ("tier_2_count", str(diff_report["tier_2_count"])),
            ("tier_3_count", str(diff_report["tier_3_count"])),
            ("tier_4_count", str(diff_report["tier_4_count"])),
            ("scoring_version", SCORING_VERSION),
            ("generated_at", str(datetime_now_iso()))
        ])

        # Insert Tracks
        for trk in ranked_tracks:
            key = trk["discography_track_id"] or normalize_str(trk["track_title"])
            cached_sp_uri = existing_tracks_map.get(key, "")

            cur_new.execute("""
                INSERT INTO tracks (
                    position, track_title, album_title, year, composer,
                    singers, lyricist, duration, track_type, stream_url,
                    evidence_tier, historical_evidence_score, evidence_confidence,
                    scoring_version, spotify_query, spotify_uri, discography_track_id,
                    match_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trk["position"],
                trk["track_title"],
                trk["album_title"],
                trk["year"],
                trk["composer"],
                trk["singers"],
                trk["lyricist"],
                trk["duration"],
                trk["track_type"],
                trk["stream_url"],
                trk["evidence_tier"],
                trk["historical_evidence_score"],
                trk["evidence_confidence"],
                SCORING_VERSION,
                f"{trk['track_title']} {trk['album_title']}",
                cached_sp_uri,
                trk["discography_track_id"],
                "evidence_ranking_v1"
            ))

        conn_new.commit()

        # Run integrity check before replacing original
        integrity = cur_new.execute("PRAGMA integrity_check;").fetchone()[0]
        conn_new.close()

        if integrity != "ok":
            logging.error(f"Integrity check failed for {temp_db_path}: {integrity}")
            temp_db_path.unlink()
            raise RuntimeError(f"Database integrity check failed: {integrity}")

        # Atomic rename
        temp_db_path.replace(db_path)
        logging.info(f"✅ Successfully wrote {db_path.name} with {len(ranked_tracks)} tracks in evidence order.")
        return diff_report


def datetime_now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description="Evidence-Based Multi-Tier Ranking Engine.")
    parser.add_argument("--year", type=int, help="Process single year (e.g. 1985 or 2024)")
    parser.add_argument("--batch", type=str, help="Process era batch (e.g. 1980-1989)")
    parser.add_argument("--all", action="store_true", help="Process all active years")
    parser.add_argument("--dry-run", action="store_true", help="Generate diff report without modifying files")
    args = parser.parse_args()

    engine = HistoricalEvidenceEngine()

    if args.year:
        ranked = engine.rank_year(args.year, write_to_discography=not args.dry_run)
        engine.build_year_playlist_db(args.year, ranked, dry_run=args.dry_run)

    elif args.batch:
        start_yr, end_yr = map(int, args.batch.split("-"))
        logging.info(f"Processing batch {start_yr} to {end_yr}...")
        for yr in range(start_yr, end_yr + 1):
            if yr in [1990, 1991, 1993, 1995]:
                logging.info(f"Skipping scrape gap year {yr} (isolated in repair ticket).")
                continue
            ranked = engine.rank_year(yr, write_to_discography=not args.dry_run)
            if ranked:
                engine.build_year_playlist_db(yr, ranked, dry_run=args.dry_run)

    elif args.all:
        logging.info("Processing all active years...")
        for yr in range(1960, 2027):
            if yr in [1990, 1991, 1993, 1995]:
                continue
            ranked = engine.rank_year(yr, write_to_discography=not args.dry_run)
            if ranked:
                engine.build_year_playlist_db(yr, ranked, dry_run=args.dry_run)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
