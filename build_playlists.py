#!/usr/bin/env python3
"""
build_playlists.py - Standalone SQLite Playlist Database Generator.
Generates an individual, dedicated .db file for EACH specific slug/playlist across
all taxonomy categories: Artist (Hits/Underrated per artist), Mood (each emotion),
Genre, Activity, Relationship, Era, and Tamil categories.
"""

import os
import re
import sqlite3
import datetime
import shutil
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DISCO_DB = BASE_DIR / "tamil_discography.db"
PLAYLISTS_DIR = BASE_DIR / "playlists"

# Top artists definition with tailored hit/underrated keywords
TOP_ARTISTS = [
    {
        "name": "A. R. Rahman",
        "slug_base": "ar_rahman",
        "role": "composer",
        "emoji": "🎹",
        "filter": r"\b(a\.?\s*r\.?\s*rahman|a\.?\s*r\.?\s*raghuman)\b",
        "exclude_filter": r"\b(abdul\s*rahman|mujeep\s*rahman)\b",
        "hit_keywords": r"roja|bombay|gentleman|mudhalvan|jeans|kadhalan|alaipayuthey|kandukondain|sivaji|enthiran|vinnaithaandi|vinnathaandi|ayutha ezhuthu|boys|new york|urusvasi|mustafa|chinnanchiru|munbe",
        "underrated_keywords": r"taj mahal|sangamam|tenali|parthale|may madham|kizhakku cheemayile|karuthamma|anthimanthaarai|connections|couples|maryan|raavanan|kaaviyathalaivan|achcham yenbadhu|chekka chivantha|vendhu thanindhathu|iravin nizhal"
    },
    {
        "name": "Ilaiyaraaja",
        "slug_base": "ilaiyaraaja",
        "role": "composer",
        "emoji": "👑",
        "filter": r"\b(ilaiyaraaja|ilayaraja|ilayaraaja)\b",
        "exclude_filter": r"meenakshi\s*ilayaraja",
        "hit_keywords": r"karakattakaran|nayakan|thalapathi|mouna ragam|sindhu bhairavi|anand|thevar magan|michael madana|payanangal|chinna thambi|ejamaan|avatharam|hey ram|virumaandi|pitamagan|kadhalukku mariyadhai",
        "underrated_keywords": r"en bommukutty|poonthotta|idhu oru|chembaruthi|marupadiyum|mogrini|pazhassi|dhaam dhoom|megha|ulavuthurai|onayum|thara thappattai|viduthalai|climax"
    },
    {
        "name": "Harris Jayaraj",
        "slug_base": "harris_jayaraj",
        "role": "composer",
        "emoji": "🎸",
        "filter": r"\b(harris\s*jayaraj|harris)\b",
        "exclude_filter": None,
        "hit_keywords": r"minnale|kaakha kaakha|ghajini|anniyan|vettaiyaadu|vaaranam aayiram|ayan|aadhavan|engeyum kadhal|nanban|thuppakki|yennai arindhaal|irumugan",
        "underrated_keywords": r"samurai|lesa lesa|kovil|arputha|ullam ketkume|chellamae|majunu|dhaam dhoom|orange|oru kal oru kannadi|dev|kaappaan|legend"
    },
    {
        "name": "Yuvan Shankar Raja",
        "slug_base": "yuvan_shankar_raja",
        "role": "composer",
        "emoji": "🔥",
        "filter": r"\b(yuvan\s*shankar\s*raja|yuvan)\b",
        "exclude_filter": None,
        "hit_keywords": r"7g rainbow|kadhal kondein|pudhupettai|raam|paruthiveeran|billa|mankatha|paiyaa|naan mahaan alla|aaranya kaandam|biriyani|dharani|neethaane en vasantham|anjaan|maanaadu|goat",
        "underrated_keywords": r"poovellam kettuppar|thulluvadho ilamai|mounam pesiyadhe|kurumbu|pudhiya geethai|kanda naal mudhal|kalvanin kadhali|saroja|vaamanan|theeradha vilaiyattu|kazhugu|aadhi bhagavan|ngk|valimai"
    },
    {
        "name": "Anirudh Ravichander",
        "slug_base": "anirudh",
        "role": "composer",
        "emoji": "⚡",
        "filter": r"\b(anirudh\s*ravichander|anirudh)\b",
        "exclude_filter": None,
        "hit_keywords": r"3|ethir neechal|vanakkam chennai|vip|velaiilla|kaththi|maari|naanum rowdy dhaan|vedalam|remmo|petta|master|doctor|don|vikram|beast|thiruchitrambalam|jailer|leo|devara|vettaiyan",
        "underrated_keywords": r"david|aakko|kaaki sattai|rum|vivegam|kolamaavu kokila|jersey|gang leader|darbar|pavakkadhaigal"
    },
    {
        "name": "Vidyasagar",
        "slug_base": "vidyasagar",
        "role": "composer",
        "emoji": "🎼",
        "filter": r"\bvidyasagar\b",
        "exclude_filter": None,
        "hit_keywords": r"ghilli|dhool|dhill|run|chandramukhi|mozhi|kuruvi|anbe sivam|thirumalai|poovellam un vaasam|parthiban kanavu|giri|villu",
        "underrated_keywords": r"karnaa|aahaa|ujala|nilave mugam kaattu|alavandhan|thithikudhe|otran|madhurey|kannaadi pookal|majaa|thambi|sivappathigaram|kaavalan"
    },
    {
        "name": "Deva",
        "slug_base": "deva",
        "role": "composer",
        "emoji": "🪘",
        "filter": r"\bdeva\b",
        "exclude_filter": r"\b(mahadevan|vasudevan|prabhu\s*deva|gurudeva|jaideva|devadas)\b",
        "hit_keywords": r"baasha|annamalai|suriyan|basha|kadhal kottai|kushi|vaali|avvai shanmugi|arunachalam|natpukkaga|red|citizen|mugavaree|chocolate",
        "underrated_keywords": r"vaigasi poranthachu|kizhakku vaasal|marumalarchi|unnidathil ennai|ninaithen vandhai|priyamudan|nenjinile|kannaal pesavaa|appu"
    },
    {
        "name": "Santhosh Narayanan",
        "slug_base": "santhosh_narayanan",
        "role": "composer",
        "emoji": "🎷",
        "filter": r"\b(santhosh\s*narayanan|sa\.?\s*na)\b",
        "exclude_filter": r"\b(dhayanidhi|venki|studios)\b",
        "hit_keywords": r"attakathi|pizza|soodhu kavvum|jigarthanda|madras|kabali|kaala|vada chennai|pariyerum perumal|karnan|sarpatta|mahaan|chithha|kalki",
        "underrated_keywords": r"cuckoo|enakku vaaltha|irudhi suttru|manithan|kashmora|server sundaram|gypsy|jagame thandhiram|dasara"
    },
    {
        "name": "D. Imman",
        "slug_base": "d_imman",
        "role": "composer",
        "emoji": "🌾",
        "filter": r"\b(d\.?\s*imman|imman)\b",
        "exclude_filter": None,
        "hit_keywords": r"kumki|kayal|varuthapadatha valibar|rajini murugan|viswasam|annaatthe|miruthan|bogan|kadaikutty singam|seema raja",
        "underrated_keywords": r"tamizhan|girivalam|marudhamalai|myna|manampole|sigaram thodu|vetrivel|panjumittai|podhuvaga emmanasu"
    },
    {
        "name": "G. V. Prakash Kumar",
        "slug_base": "gv_prakash",
        "role": "composer",
        "emoji": "🎻",
        "filter": r"\b(g\.?\s*v\.?\s*prakash(\s*kumar)?|gv\s*prakash)\b",
        "exclude_filter": None,
        "hit_keywords": r"veyil|kireedam|angadi theru|aayirathil oruvan|madrasapattinam|aadukalam|mayakkam enna|thalaivaa|raja rani|theri|soorarai pottru|captain miller|amarasaran",
        "underrated_keywords": r"polladhavan|kuselan|ananda thandavam|irandam ulagam|deiva thirumagal|saguni|paradesi|marudhu|kaashmora|sarvam thaala mayam"
    },
    {
        "name": "M. S. Viswanathan",
        "slug_base": "ms_viswanathan",
        "role": "composer",
        "emoji": "✨",
        "filter": r"\b(m\.?\s*s\.?\s*viswanathan|m\.?\s*s\.?\s*v|viswanathan)\b",
        "exclude_filter": r"\b(poornam\s*viswanathan|d\.?\s*k\.?\s*viswanathan)\b",
        "hit_keywords": r"karnan|ayirathil oruvan|padagotti|server sundaram|bama vijayam|adhey kangal|kavalkaran|galatta kalyanam|rickshawkaran|ulagam sutrum valiban|nenjirukkum varai|aval oru thodarkadhai",
        "underrated_keywords": r"pazhani|anbu karangal|selvam|sorgam|gnana oli|bharatha vilas|sivagamiyin sabatham|avargal|varumayin niram sivappu|thillu mullu"
    },
    {
        "name": "K. V. Mahadevan",
        "slug_base": "kv_mahadevan",
        "role": "composer",
        "emoji": "🪕",
        "filter": r"\b(k\.?\s*v\.?\s*mahadevan|kvm)\b",
        "exclude_filter": r"\b(shankar\s*mahadevan|shivam\s*mahadevan)\b",
        "hit_keywords": r"thiruvilaiyadal|saraswathi sabatham|kandhan karunai|thillana mohanambal|kadavul amaitha medai|vasanthamaligai|sankarabharanam",
        "underrated_keywords": r"sampoorna ramayanam|thirumanam|pudhiya pathai|adimai penn|velli vizha|swati mutyam|sruthilayalu"
    },
    {
        "name": "S. P. Balasubrahmanyam",
        "slug_base": "spb",
        "role": "singer",
        "emoji": "🎙️",
        "filter": r"\b(balasubrahmanyam|s\.?\s*p\.?\s*b)\b",
        "exclude_filter": None,
        "hit_keywords": r"kadhal|mannan|baasha|muthu|padayappa|keladi kanmani|thalapathi|sindhu bhairavi|guna|payanangal|gentleman|ejamaan",
        "underrated_keywords": r"sigaram|duet|anand|mounam|gopura vasalile|idhu namma aalu|enakkul oruvan|avatharam"
    },
    {
        "name": "K. J. Yesudas",
        "slug_base": "kj_yesudas",
        "role": "singer",
        "emoji": "🌟",
        "filter": r"\b(yesudas|k\.?\s*j\.?\s*yesudas)\b",
        "exclude_filter": None,
        "hit_keywords": r"thenpandi|kannaana|amman|kanmani|sangeetha|deivam|aararo|vellai|thalattu|oru koodai|aboorva|dalapathi",
        "underrated_keywords": r"azhagan|poongatru|mannil|ulagam|kanavugal|sree ragam|nadham"
    },
    {
        "name": "K. S. Chithra",
        "slug_base": "ks_chithra",
        "role": "singer",
        "emoji": "🕊️",
        "filter": r"\b(chithra|k\.?\s*s\.?\s*chithra)\b",
        "exclude_filter": None,
        "hit_keywords": r"chinna chinna|kannalane|malargale|kannodu|anbendra|roja|porkkalam|kannukulle|vaseegara|munbe",
        "underrated_keywords": r"oru naal|poongatru|sendhoora|azhagi|manasellam|kanave|thalattu"
    },
    {
        "name": "S. Janaki",
        "slug_base": "s_janaki",
        "role": "singer",
        "emoji": "🎶",
        "filter": r"\b(janaki|s\.?\s*janaki)\b",
        "exclude_filter": None,
        "hit_keywords": r"thanga manasukkaran|mahaprabhu|vanaja girija|vaikarai|idimuzhakkam|singam|karakattakaran|sindhu bhairavi|mouna ragam|nayakan|thevar magan|thalapathi|16 vayathinile|sankarabharanam",
        "underrated_keywords": r"thean|sinthidum|teenz|poovarasam|idhu oru|chembaruthi|marupadiyum|poonthotta|en bommukutty"
    },
    {
        "name": "Hariharan",
        "slug_base": "hariharan",
        "role": "singer",
        "emoji": "🌹",
        "filter": r"\bhariharan\b",
        "exclude_filter": None,
        "hit_keywords": r"uyire|kurukku|telepathy|thirakkatha|venmathi|en navil|unale|nenjukkul|malargale|anbe anbe",
        "underrated_keywords": r"kavithai|chanda|suttum|kannodu|pazhaya|kannadi|thendral"
    },
    {
        "name": "Shankar Mahadevan",
        "slug_base": "shankar_mahadevan",
        "role": "singer",
        "emoji": "⚡",
        "filter": r"\bshankar\s*mahadevan\b",
        "exclude_filter": None,
        "hit_keywords": r"thaniye|manmadha|theradi|kalloori|uppu karuvadu|varaha|sandakozhi|pattukottai|vetri",
        "underrated_keywords": r"poove|kanavugal|nenjil|anbil|gopura|uyarndhu"
    },
    {
        "name": "Sid Sriram",
        "slug_base": "sid_sriram",
        "role": "singer",
        "emoji": "🎤",
        "filter": r"\bsid\s*sriram\b",
        "exclude_filter": None,
        "hit_keywords": r"unkoodave|anbe peranbe|kadhaippoma|kaadhal theevey|adiye|ennodu|thalli pogathey|maruvaarthai|kannaana|innum|mudhal|paravai|unale|bae|kaadhal",
        "underrated_keywords": r"kannu thangom|easy come|poova thalaiyaa|en uyir|thinam thinam|michael|pooppom|yaen|kannukulle|adada|oru naalil|katchi sera"
    },
    {
        "name": "Shreya Ghoshal",
        "slug_base": "shreya_ghoshal",
        "role": "singer",
        "emoji": "🌸",
        "filter": r"\bshreya\s*ghosh?al\b",
        "exclude_filter": None,
        "hit_keywords": r"ninaithu ninaithu|mailaanji|anbe peranbe|ival dhaana|munbe vaa|mannipaaya|aila aila|un mela|adada|oru naalil|kannaana|innum|thuli|partha",
        "underrated_keywords": r"paartha nyabagam|kolai|vaa tharagaye|teenz|paramporul|nenjil|siragugal|vinnathaandi|thalli|anbil|malargal"
    }
]

# Complete taxonomy mapping
TAXONOMY = {
    # -------------------------------------------------------------
    # Category 1: By Artist (Each artist gets separate hits & underrated slugs)
    # -------------------------------------------------------------
    "artist": [],  # dynamically populated from TOP_ARTISTS below

    # -------------------------------------------------------------
    # Category 2: By Mood (Every single mood is its own slug)
    # -------------------------------------------------------------
    "mood": [
        {"slug": "happy", "name": "😊 Happy", "category": "By Mood", "emoji": "😊", "desc": "Joyful, sunny, and upbeat Tamil melodies.", "rules": [{"type": "keyword", "pattern": r"\b(happy|kushi|siriki|anbendra|enjoy|jolly|kondattam|aarambam|pookal|sundari|chinna chinna|malargal)\b"}]},
        {"slug": "feel_good", "name": "Feel-Good", "category": "By Mood", "emoji": "✨", "desc": "Warm, uplifting feel-good tracks that lighten your spirit.", "rules": [{"type": "keyword", "pattern": r"\b(chillax|aathangara|vaadi|kanmoodi|pattukottai|chella|podu|velli|thamizh|penn|kannadi|anbil)\b"}]},
        {"slug": "sad", "name": "😢 Sad", "category": "By Mood", "emoji": "😢", "desc": "Soul-stirring, sorrowful songs and melancholic masterworks.", "rules": [{"type": "keyword", "pattern": r"\b(sogam|kannir|kanner|pirivu|valikudhu|thani|vali|valigal|maranam|vidai|azhuvadhu|azhudha|ninaithu|thooram)\b"}]},
        {"slug": "heartbreak", "name": "Heartbreak", "category": "By Mood", "emoji": "💔", "desc": "Aching cries of lost love, broken vows, and shattered dreams.", "rules": [{"type": "keyword", "pattern": r"\b(vilagi|kanave|kanavu|maranthu|theeyil|kadhal valikudhu|poongatru|kannukulle|engae|enna solla|ammadi)\b"}]},
        {"slug": "love", "name": "❤️ Love", "category": "By Mood", "emoji": "❤️", "desc": "Timeless romantic anthems celebrating the depth of love.", "rules": [{"type": "keyword", "pattern": r"\b(kadhal|kaadhal|anbe|uyire|priya|idhayame|penne|azhagi|manasellam|unakkul|unnai|kannazhaga)\b"}]},
        {"slug": "romance", "name": "Romance", "category": "By Mood", "emoji": "🌹", "desc": "Passionate, tender, and sensual romantic melodies.", "rules": [{"type": "keyword", "pattern": r"\b(vizhiyil|malare|kannodu|vaseegara|enrenrum|ennodu|unale|nenjukkul|paarthu|kannum|paravai)\b"}]},
        {"slug": "chill", "name": "😎 Chill", "category": "By Mood", "emoji": "😎", "desc": "Laid-back, acoustic and easy-listening vibes to unwind.", "rules": [{"type": "keyword", "pattern": r"\b(chill|thendral|breeze|kaatru|nila|nilavu|poongatru|illamai|katre)\b"}]},
        {"slug": "relax", "name": "Relax", "category": "By Mood", "emoji": "🛋️", "desc": "Soothing, gentle compositions to relieve stress and ease the mind.", "rules": [{"type": "keyword", "pattern": r"\b(alai|venmathi|munbe|new york|oorvasi|oru devathai|pesugiren|kangal|malargale|anbil)\b"}]},
        {"slug": "hype", "name": "🔥 Hype", "category": "By Mood", "emoji": "🔥", "desc": "Electric, stadium-sized bangers and heroic anthem drops.", "rules": [{"type": "keyword", "pattern": r"\b(hype|mass|verithanam|aaluma|neruppu|thee|adra|kuthu|thala|thalapathy|vathi|dheera)\b"}]},
        {"slug": "energetic", "name": "Energetic", "category": "By Mood", "emoji": "⚡", "desc": "Fast-tempo, rhythmic beats packed with adrenaline.", "rules": [{"type": "keyword", "pattern": r"\b(singam|thupakki|kabali|vikram|leo|jailer|master|billa|mankatha|petta|valimai|verithanam|aaluma|neruppu|thee|adra|kuthu|dheera|surviva|badass|hukum|hunterr)\b"}]},
        {"slug": "angry", "name": "😡 Angry", "category": "By Mood", "emoji": "😡", "desc": "Raw aggression, roaring vocals, and furious storm tracks.", "rules": [{"type": "keyword", "pattern": r"\b(paga|pagai|erimalai|azhivu|vettai|kolai|sathiyam|porattam|por|singa|rudhran|asuran)\b"}]},
        {"slug": "revenge", "name": "Revenge", "category": "By Mood", "emoji": "⚔️", "desc": "Dark retaliation anthems, payback scores, and retribution themes.", "rules": [{"type": "keyword", "pattern": r"\b(polladhavan|karnan|vada chennai|thuppakki|thimiru|soorarai|raavanan|ayirathil|aravindhan)\b"}]},
        {"slug": "peaceful", "name": "🌙 Peaceful", "category": "By Mood", "emoji": "🌙", "desc": "Tranquil stillness, midnight breezes, and quiet serenity.", "rules": [{"type": "keyword", "pattern": r"\b(peace|amaithi|thalattu|thaalattu|aararo|kanne|urangu|poovarasam|kanave)\b"}]},
        {"slug": "calm", "name": "Calm", "category": "By Mood", "emoji": "🕊️", "desc": "Gentle, non-intrusive melodies to soothe nerves and restore balance.", "rules": [{"type": "keyword", "pattern": r"\b(chinna chinna|vellai|vidukathaiya|thenral|thendral|sendhoora|malargale|kannodu|anbendra|amaithi|shanti|poovarasam)\b"}]},
        {"slug": "emotional", "name": "💭 Emotional", "category": "By Mood", "emoji": "💭", "desc": "Heart-tugging ballads touching the deepest human chords.", "rules": [{"type": "keyword", "pattern": r"\b(ninaivu|ninaivugal|pasam|kannadi|kaalam|ilamai|pazhaya|natpu|thozha)\b"}]},
        {"slug": "nostalgic", "name": "Nostalgic", "category": "By Mood", "emoji": "🕰️", "desc": "Golden flashbacks, fond memories of youth, and days gone by.", "rules": [{"type": "keyword", "pattern": r"\b(kanave|uyir|appavin|amma|thai|thaai|poothendral|thenpandi|marakkuma|raasave)\b"}]},
        {"slug": "feel_good_romance", "name": "🥰 Feel-Good Romance", "category": "By Mood", "emoji": "🥰", "desc": "Sweet, bubbly, butterflies-in-the-stomach romantic duets.", "rules": [{"type": "keyword", "pattern": r"\b(chellam|azhage|kalyana vaibhogame|kannukulle|adada|anbe peranbe|bae|thuli thuli|kurumugil|innum konjam)\b"}]},
        {"slug": "motivation", "name": "💪 Motivation", "category": "By Mood", "emoji": "💪", "desc": "Triumphant battle cries and perseverance anthems to conquer mountains.", "rules": [{"type": "keyword", "pattern": r"\b(vetri|nambikkai|vettri|ezhu|uyarndhu|kanavugal|dheera|singam|oorvasi|oruvan|sakthi|veeram)\b"}]},
        {"slug": "inspiration", "name": "Inspiration", "category": "By Mood", "emoji": "🌟", "desc": "Life-affirming, philosophical poetry and inspiring musical swells.", "rules": [{"type": "keyword", "pattern": r"\b(ezhu ezhu|nambikkai|vidukathaiya|vetri nichayam|kanavugal|chariot|unnal mudiyum|anbe sivam)\b"}]}
    ],

    # -------------------------------------------------------------
    # Category 3: By Music Genre
    # -------------------------------------------------------------
    "genre": [
        {"slug": "pop", "name": "Pop", "category": "By Music Genre", "emoji": "🎤", "desc": "Catchy hooks and vibrant Tamil pop bangers.", "rules": [{"type": "keyword", "pattern": r"\b(pop|disco|party|dance|urvasi|chiku|mambo|mustafa|chikku|jolly|rowdy|arabic|chellamma)\b"}]},
        {"slug": "rock", "name": "Rock", "category": "By Music Genre", "emoji": "🎸", "desc": "Electric guitars, heavy drums, and Tamil rock riffs.", "rules": [{"type": "keyword", "pattern": r"\b(rock|guitar|heavy|asuran|kabali|vikram|leo|master|anirudh|badass|neruppu|lokiverse)\b"}]},
        {"slug": "hip_hop_rap", "name": "Hip-Hop & Rap", "category": "By Music Genre", "emoji": "🎧", "desc": "Street hip-hop flow and conscious Tamil rap bars.", "rules": [{"type": "keyword", "pattern": r"\b(rap|hip hop|hiphop|tamizha|therukural|arivu|blaaze|yogi b|mc sai|ady|dheena|marana)\b"}]},
        {"slug": "rnb_soul", "name": "R&B / Soul", "category": "By Music Genre", "emoji": "🎷", "desc": "Velvety vocal runs and contemporary soul grooves.", "rules": [{"type": "keyword", "pattern": r"\b(soul|r&b|vaseegara|en navil|unakkul|nenjukkul|kannum|hosanna|partha|sid sriram|pradeep kumar)\b"}]},
        {"slug": "electronic_edm", "name": "Electronic / EDM", "category": "By Music Genre", "emoji": "🎛️", "desc": "Synth drops, EDM festival anthems, and dancefloor power.", "rules": [{"type": "keyword", "pattern": r"\b(electronic|edm|techno|trance|electro|remix|dj|aluma|verithanam|vaathi|donu|sodakku|tasakku)\b"}]},
        {"slug": "classical", "name": "Classical / Carnatic", "category": "By Music Genre", "emoji": "🪕", "desc": "Traditional Carnatic ragas and classical orchestration.", "rules": [{"type": "raga_or_keyword", "pattern": r"\b(raga|ragam|carnatic|sindhu\s*bhairavi|kalyani|thodi|charukesi|hamsadhwani|shankarabharanam|sankarabharanam|mohanam|swaram|keeravani)\b"}]},
        {"slug": "jazz_blues", "name": "Jazz & Blues", "category": "By Music Genre", "emoji": "🎺", "desc": "Swinging horn sections, walking bass, and bluesy melancholy.", "rules": [{"type": "keyword", "pattern": r"\b(jazz|blues|sax|trumpet|piano|megam|irumbile|oru naal|andhadhi|jillendru)\b"}]},
        {"slug": "folk", "name": "Folk", "category": "By Music Genre", "emoji": "🥁", "desc": "Rooted percussion, rural soul, and village festivities.", "rules": [{"type": "keyword", "pattern": r"\b(folk|naatupura|oru koodai|karakattakaran|paruthi|komban|chinna machan|appatha|gramathu|thavil|oorum)\b"}]},
        {"slug": "acoustic", "name": "Acoustic", "category": "By Music Genre", "emoji": "🪗", "desc": "Intimate guitar fingerpicking and unplugged vocals.", "rules": [{"type": "keyword", "pattern": r"\b(acoustic|unplugged|fingerpicking|acoustic guitar|spanish guitar|solo violin|grand piano)\b"}]},
        {"slug": "indie", "name": "Indie", "category": "By Music Genre", "emoji": "🌿", "desc": "Independent, alternative sounds and fresh non-film artistry.", "rules": [{"type": "keyword", "pattern": r"\b(indie|pradeep|sean roldan|dhee|enjoy enjaami|katchi sera|asai|bodhai|kannamma|orasaadha)\b"}]},
        {"slug": "devotional", "name": "Devotional", "category": "By Music Genre", "emoji": "🪔", "desc": "Spiritual hymns and sacred devotional chants.", "rules": [{"type": "keyword", "pattern": r"\b(murugan|shiva|krishna|vinayagar|amman|ayyappa|venkateswara|bakthi|sami|kovil|arunachala)\b"}]},
        {"slug": "instrumental", "name": "Instrumental", "category": "By Music Genre", "emoji": "🎻", "desc": "Pure instrumental themes, flute, veena, and violin solos.", "rules": [{"type": "keyword", "pattern": r"\b(instrumental|theme|flute|veena|violin|mandolin|piano|melody|symphony|bgm|score)\b"}]},
        {"slug": "lofi", "name": "Lo-fi", "category": "By Music Genre", "emoji": "📼", "desc": "Warm tape crackle, slow-reverb chords, and rainy night vibes.", "rules": [{"type": "keyword", "pattern": r"\b(lofi|lo-fi|slowed\s*and\s*reverb|slowed|reverb mix|bedroom pop|tape crackle)\b"}]},
        {"slug": "phonk", "name": "Phonk", "category": "By Music Genre", "emoji": "🏎️", "desc": "Dark 808 bass slides, drift cowbells, and menacing swagger.", "rules": [{"type": "keyword", "pattern": r"\b(drift phonk|phonk|brazilian phonk|drift bass|cowbell)\b"}]},
        {"slug": "jazz_fusion", "name": "Jazz Fusion", "category": "By Music Genre", "emoji": "🎷", "desc": "Intricate fusion of Indian classical ragas with world jazz.", "rules": [{"type": "keyword", "pattern": r"\b(fusion|jazz fusion|shakti|guitar prasanna|mandolin u|prasanna guitar)\b"}]}
    ],

    # -------------------------------------------------------------
    # Category 4: By Activity
    # -------------------------------------------------------------
    "activity": [
        {"slug": "workout_gym", "name": "Workout & Gym", "category": "By Activity", "emoji": "🏋️", "desc": "High-octane fuel for cardio, heavy lifting, and workouts.", "rules": [{"type": "keyword", "pattern": r"\b(workout|gym|running|verithanam|badass|hukum|aaluma|neruppu|surviva|adra|dheera|singam)\b"}]},
        {"slug": "driving_road_trip", "name": "Driving / Road Trip", "category": "By Activity", "emoji": "🚗", "desc": "Windows-down cruising melodies for endless highway miles.", "rules": [{"type": "keyword", "pattern": r"\b(road|drive|trip|oorvasi|mustafa|new york|chal chalo|ennamo|jolly)\b"}]},
        {"slug": "studying_focus", "name": "Studying & Focus", "category": "By Activity", "emoji": "📚", "desc": "Non-intrusive calm background melodies for deep concentration.", "rules": [{"type": "keyword", "pattern": r"\b(focus|study|instrumental|flute|piano|theme|bgm|thendral|amaithi|malargale|kannodu)\b"}]},
        {"slug": "sleeping", "name": "Sleeping", "category": "By Activity", "emoji": "💤", "desc": "Soft, whispery lullabies to gently drift into dreamland.", "rules": [{"type": "keyword", "pattern": r"\b(sleep|thalattu|aararo|urangu|kanmaniye|poovarasam)\b"}]},
        {"slug": "working", "name": "Working", "category": "By Activity", "emoji": "💻", "desc": "Steady, rhythmic and mellow tracks to power through the workday.", "rules": [{"type": "keyword", "pattern": r"\b(work|flow|melody|peace|chill|anbil|unakkul|en navil|pesugiren)\b"}]},
        {"slug": "morning_motivation", "name": "Morning Motivation", "category": "By Activity", "emoji": "🌅", "desc": "Fresh dawn breezes, positive energy, and inspiring beginnings.", "rules": [{"type": "keyword", "pattern": r"\b(morning|sunrise|kaalai|vidiyum|ezhu|nambikkai|vellai|kanavugal|dheera|chinna chinna|vetri)\b"}]},
        {"slug": "party_dance", "name": "Party & Dance", "category": "By Activity", "emoji": "🎉", "desc": "Club-filling dance anthems, kuthu beats, and festive celebrations.", "rules": [{"type": "keyword", "pattern": r"\b(party|dance|kuthu|danga|podu|jolly|rowdy|arabic|chellamma|two two|kurchi|kaavaalaa)\b"}]},
        {"slug": "travel", "name": "Travel", "category": "By Activity", "emoji": "✈️", "desc": "Scenic wanderlust soundtracks for flights, trains, and trails.", "rules": [{"type": "keyword", "pattern": r"\b(travel|journey|payanam|kaatru|thendral|malaigal|oorum|paravai|marakkuma|vinnathaandi)\b"}]},
        {"slug": "meditation", "name": "Meditation", "category": "By Activity", "emoji": "🧘", "desc": "Tranquil stillness, OM vibrations, and peaceful reflection.", "rules": [{"type": "keyword", "pattern": r"\b(meditation|peace|om|shanti|zen|amaithi|nadham|flute|devotional|kovil|arunachala)\b"}]},
        {"slug": "background_music", "name": "Background Music", "category": "By Activity", "emoji": "☕", "desc": "Pleasant ambient café instrumental tones that never overwhelm.", "rules": [{"type": "keyword", "pattern": r"\b(background|theme|bgm|instrumental|piano|guitar|violin|melody|orchestra|soft)\b"}]}
    ],

    # -------------------------------------------------------------
    # Category 5: By Relationship & Emotion
    # -------------------------------------------------------------
    "relationship": [
        {"slug": "first_love", "name": "First Love", "category": "By Relationship & Emotion", "emoji": "💘", "desc": "The innocent, unforgettable fluttering of falling in love.", "rules": [{"type": "keyword", "pattern": r"\b(first love|muthal kadhal|mudhal kadhal|muthal murai|mudhal murai|kannazhaga|vaseegara|ennavale|kannukulle)\b"}]},
        {"slug": "one_sided_love", "name": "One-Sided Love", "category": "By Relationship & Emotion", "emoji": "💔", "desc": "The bitter-sweet ache of loving silently from a distance.", "rules": [{"type": "keyword", "pattern": r"\b(one side|unrequited|solla mudiyatha|pesaadhe|maranthu|vilagi)\b"}]},
        {"slug": "breakup", "name": "Breakup", "category": "By Relationship & Emotion", "emoji": "🥀", "desc": "Tear-stained goodbyes and the pain of parting ways.", "rules": [{"type": "keyword", "pattern": r"\b(breakup|pirivu|valikudhu|thani|vali|maranthu|ennodu|pogathe|kannir|kanner|sogam)\b"}]},
        {"slug": "missing_someone", "name": "Missing Someone", "category": "By Relationship & Emotion", "emoji": "🫂", "desc": "Haunting memories and the deep longing to hold them again.", "rules": [{"type": "keyword", "pattern": r"\b(missing|ninaivu|ninaivugal|engae|enna solla|unakkul|vilagi|thooram)\b"}]},
        {"slug": "long_distance_love", "name": "Long-Distance Love", "category": "By Relationship & Emotion", "emoji": "✈️", "desc": "Love that defies borders, time-zones, and physical miles.", "rules": [{"type": "keyword", "pattern": r"\b(distance|thooram|kadal|kaatru|thendral|new york|alaye|vidai|pesugiren|paravai)\b"}]},
        {"slug": "wedding_songs", "name": "Wedding Songs", "category": "By Relationship & Emotion", "emoji": "💍", "desc": "Kalyanam cheers, sacred mangalyam rituals, and wedding joy.", "rules": [{"type": "keyword", "pattern": r"\b(kalyanam|thali|mangalyam|kattikitta|wedding|kalyana|muhurtham|kettimelam|nadaswaram|sammandhi|manappen|manamagan)\b"}]},
        {"slug": "friendship", "name": "Friendship", "category": "By Relationship & Emotion", "emoji": "🤝", "desc": "Natpu anthems: unbreakable bonds, laughter, and brotherhood.", "rules": [{"type": "keyword", "pattern": r"\b(natpu|thozha|friend|nanba|machan|mustafa|orasaadha|thalapathi|kattukuyilu)\b"}]},
        {"slug": "family", "name": "Family", "category": "By Relationship & Emotion", "emoji": "👨‍👩‍👧‍👦", "desc": "Tender odes to parents, siblings, and unconditional family love.", "rules": [{"type": "keyword", "pattern": r"\b(amma|thai|thaai|appa|thangachi|annai|thambi|kudumbam|pasam|kanne|aararo)\b"}]},
        {"slug": "memories", "name": "Memories", "category": "By Relationship & Emotion", "emoji": "📸", "desc": "Nostalgic snapshots of childhood, school days, and yesterday.", "rules": [{"type": "keyword", "pattern": r"\b(ninaivu|ninaivugal|ilamai kaalam|pazhaya ninaivugal|marakkuma|nyabagam|flashback)\b"}]},
        {"slug": "moving_on", "name": "Moving On", "category": "By Relationship & Emotion", "emoji": "🌱", "desc": "Picking up the pieces, finding peace, and starting a new chapter.", "rules": [{"type": "keyword", "pattern": r"\b(moving on|ezhu|vidu|vidai|maranthu|puthiya|nambikkai|vettri|aarambam|soorarai)\b"}]}
    ],

    # -------------------------------------------------------------
    # Category 6: By Era & Collection
    # -------------------------------------------------------------
    "era": [
        {"slug": "latest_releases", "name": "Latest Releases", "category": "By Era & Collection", "emoji": "🆕", "desc": "Fresh chartbusters from 2024 to 2026.", "rules": [{"type": "year_range", "start": 2024, "end": 2026}]},
        {"slug": "trended_trending", "name": "Trended & Trending Songs", "category": "By Era & Collection", "emoji": "📈", "desc": "Reels hits and viral streaming phenomena (2021-2026).", "rules": [{"type": "year_range", "start": 2021, "end": 2026}]},
        {"slug": "all_time_hits", "name": "All-Time Hits", "category": "By Era & Collection", "emoji": "🏆", "desc": "Immortal Tamil blockbuster anthems across all decades.", "rules": [{"type": "all_time_hits"}]},
        {"slug": "90s_classics", "name": "90s Classics", "category": "By Era & Collection", "emoji": "📻", "desc": "The revolutionary golden 1990s decade (1990-1999).", "rules": [{"type": "year_range", "start": 1990, "end": 1999}]},
        {"slug": "2000s_hits", "name": "2000s Hits", "category": "By Era & Collection", "emoji": "💿", "desc": "The dynamic 2000s era (2000-2009).", "rules": [{"type": "year_range", "start": 2000, "end": 2009}]},
        {"slug": "golden_era", "name": "Golden Era", "category": "By Era & Collection", "emoji": "👑", "desc": "Timeless vintage treasures (1960-1979).", "rules": [{"type": "year_range", "start": 1960, "end": 1979}]},
        {"slug": "old_is_gold", "name": "Old Is Gold", "category": "By Era & Collection", "emoji": "✨", "desc": "Evergreen golden classics (1960-1989).", "rules": [{"type": "year_range", "start": 1960, "end": 1989}]},
        {"slug": "hidden_gems", "name": "Hidden Gems", "category": "By Era & Collection", "emoji": "🔮", "desc": "Underrated compositions waiting to be rediscovered.", "rules": [{"type": "keyword", "pattern": r"\b(vidyasagar|dharan|ramesh|govind vasantha|sean roldan|pradeep kumar|sam cs)\b"}]},
        {"slug": "underrated_songs", "name": "Underrated Songs", "category": "By Era & Collection", "emoji": "🎯", "desc": "Stunning compositions that deserved far more fame.", "rules": [{"type": "keyword", "pattern": r"\b(taj noor|justin prabhakaran|nivas k prasanna|leon james|ghibran|ramesh vinayakam)\b"}]},
        {"slug": "personal_favorites", "name": "Personal Favorites", "category": "By Era & Collection", "emoji": "⭐", "desc": "Hand-picked signature Tamil masterpieces.", "rules": [{"type": "keyword", "pattern": r"\b(rahman|ilaiyaraaja|harris|yuvan|anirudh|spb|yesudas|chithra|janaki)\b"}]}
    ],

    # -------------------------------------------------------------
    # Category 7: Tamil Music Categories
    # -------------------------------------------------------------
    "tamil": [
        {"slug": "tamil_melody", "name": "Tamil Melody", "category": "Tamil Music Categories", "emoji": "🎼", "desc": "Classic Tamil melody at its finest.", "rules": [{"type": "keyword", "pattern": r"\b(melody|thenpandi|poongatru|kannodu|malargale|vaseegara|en navil|unakkul)\b"}]},
        {"slug": "love_duets", "name": "Love Duets", "category": "Tamil Music Categories", "emoji": "👩‍❤️‍👨", "desc": "Iconic male-female romantic duets.", "rules": [{"type": "love_duet"}]},
        {"slug": "sad_melody", "name": "Sad Melody", "category": "Tamil Music Categories", "emoji": "🎻", "desc": "Poignant, tearful violin-laden melodies.", "rules": [{"type": "keyword", "pattern": r"\b(sogam|kannir|pirivu|valikudhu|thani|vali|maranam|theeyil|poongatru)\b"}]},
        {"slug": "gaana", "name": "Gaana", "category": "Tamil Music Categories", "emoji": "🪘", "desc": "Authentic Chennai street gaana beats.", "rules": [{"type": "gaana_special"}]},
        {"slug": "kuthu_dance", "name": "Kuthu / Dance", "category": "Tamil Music Categories", "emoji": "💃", "desc": "High-octane folk kuthu percussion and whistle beats.", "rules": [{"type": "keyword", "pattern": r"\b(kuthu|dapankuthu|verithanam|aaluma|neruppu|adra|vaathi|rowdy|arabic)\b"}]},
        {"slug": "folk_village", "name": "Folk & Village Songs", "category": "Tamil Music Categories", "emoji": "🌾", "desc": "Rural instruments, harvest songs, and village soil.", "rules": [{"type": "keyword", "pattern": r"\b(folk|naatupura|oru koodai|karakattakaran|paruthi|komban|chinna machan|appatha)\b"}]},
        {"slug": "tamil_rap", "name": "Tamil Rap", "category": "Tamil Music Categories", "emoji": "🎤", "desc": "Fast flows, rhymes, and Tamil street hip-hop.", "rules": [{"type": "keyword", "pattern": r"\b(rap|hiphop|tamizha|therukural|arivu|blaaze|yogi b|mc sai|ady)\b"}]},
        {"slug": "mass_hero_bgm", "name": "Mass Hero BGM", "category": "Tamil Music Categories", "emoji": "💥", "desc": "Mass entry themes and theatre-rattling scores.", "rules": [{"type": "keyword", "pattern": r"\b(theme|bgm|badass|hukum|vikram|leo|jailer|master|kabali|billa|mankatha|teaser|entry|mass|score)\b"}]},
        {"slug": "romantic_duets", "name": "Romantic Duets", "category": "Tamil Music Categories", "emoji": "🌹", "desc": "Tender romantic melodies sung in duet harmony.", "rules": [{"type": "romantic_duet"}]},
        {"slug": "ilaiyaraaja_classics", "name": "Ilaiyaraaja Classics", "category": "Tamil Music Categories", "emoji": "👑", "desc": "The Maestro's symphonic and folk immortality.", "rules": [{"type": "composer", "pattern": r"ilaiyaraaja|ilayaraja"}]},
        {"slug": "ar_rahman_hits", "name": "A. R. Rahman Hits", "category": "Tamil Music Categories", "emoji": "🎹", "desc": "The Mozart of Madras's global masterpieces.", "rules": [{"type": "composer", "pattern": r"a\.?\s*r\.?\s*rahman|a\.?\s*r\.?\s*raghuman", "exclude_pat": r"abdul\s*rahman|mujeep\s*rahman"}]},
        {"slug": "harris_jayaraj_hits", "name": "Harris Jayaraj Hits", "category": "Tamil Music Categories", "emoji": "🎸", "desc": "Acoustic chords, whistling intros, and 2000s anthems.", "rules": [{"type": "composer", "pattern": r"harris jayaraj|harris"}]},
        {"slug": "yuvan_shankar_raja_hits", "name": "Yuvan Shankar Raja Hits", "category": "Tamil Music Categories", "emoji": "🔥", "desc": "Youth icon's addictive melancholy and raw beats.", "rules": [{"type": "composer", "pattern": r"yuvan shankar raja|yuvan"}]},
        {"slug": "anirudh_hits", "name": "Anirudh Hits", "category": "Tamil Music Categories", "emoji": "⚡", "desc": "Rockstar viral drops, viral hooks, and mass basslines.", "rules": [{"type": "composer", "pattern": r"anirudh ravichander|anirudh"}]},
        {"slug": "tamil_instrumental_bgm", "name": "Tamil Instrumental & BGM", "category": "Tamil Music Categories", "emoji": "🎻", "desc": "Best film OST scores, instrumental renditions, and overtures.", "rules": [{"type": "keyword", "pattern": r"\b(instrumental|theme|bgm|flute|score|orchestra|overture|symphony)\b"}]}
    ],

    # -------------------------------------------------------------
    # Category 8: By Year (Standalone playlist for each release year)
    # -------------------------------------------------------------
    "year": [],

    # -------------------------------------------------------------
    # Category 9: By Indie & YouTube Album Songs (11 Standalone Playlists)
    # -------------------------------------------------------------
    "indie": [
        {"slug": "indie_master", "name": "Tamil Indie Master", "category": "By Indie", "emoji": "🌿", "desc": "The complete definitive collection of Tamil independent, YouTube, and non-film music.", "rules": [{"type": "indie_all"}]},
        {"slug": "indie_blockbusters", "name": "Indie Blockbusters (50M+ & 10M+)", "category": "By Indie", "emoji": "🔥", "desc": "Mega viral hits and chartbusters with 10M to 100M+ views.", "rules": [{"type": "indie_views", "tiers": ["tier_1_mega", "tier_2_popular"]}]},
        {"slug": "hidden_indie_gems", "name": "Hidden Indie Gems", "category": "By Indie", "emoji": "💎", "desc": "Underground indie wonders, acoustic singles, and cult discoveries (<10M views).", "rules": [{"type": "indie_views", "tiers": ["tier_3_emerging", "tier_4_underground"]}]},
        {"slug": "indie_rap", "name": "Tamil Indie Rap & Hip-Hop", "category": "By Indie", "emoji": "🎤", "desc": "Street anthems, conscious hip-hop, and fast Tamil bars.", "rules": [{"type": "indie_regex", "pattern": r"arivu|paal dabba|asal kolaar|hiphop tamizha|yogi b|adk|sri rascol|mc sai|shabir|rap|hip hop|therukural|casteless collective|tenma"}]},
        {"slug": "romantic_indie", "name": "Romantic Indie", "category": "By Indie", "emoji": "🌹", "desc": "Soulful indie love melodies, acoustic ballads, and romantic duets.", "rules": [{"type": "indie_regex", "pattern": r"stephen zechariah|sai abhyankkar|sai smriti|leon james|jonita|vivek.*mervin|pradeep kumar|kadhale|orasaadha|aasa kooda|katchi sera|adi penne|usuraiya|saaral|vilagathe|bodhai kodhai|ulaviravu|kannamma"}]},
        {"slug": "folk_gaana_album", "name": "Folk & Gaana Album Songs", "category": "By Indie", "emoji": "🪘", "desc": "Raw rural soul, street percussion, and folk indie albums.", "rules": [{"type": "indie_regex", "pattern": r"anthony daasan|casteless collective|tenma|gana bala|asal kolaar|vaisagh|ramji|vaadi en machinichi|rathina katti|gaana|folk|kuthu"}]},
        {"slug": "stephen_zechariah", "name": "Stephen Zechariah Indie Hits", "category": "By Indie", "emoji": "✨", "desc": "Complete independent catalog of Singapore-Tamil sensation Stephen Zechariah.", "rules": [{"type": "indie_regex", "pattern": r"stephen zechariah"}]},
        {"slug": "kaber_vasuki", "name": "Kaber Vasuki & Kurangan", "category": "By Indie", "emoji": "🎸", "desc": "Lyrical genius, raw acoustic songwriting, and indie cult classics by Kaber Vasuki.", "rules": [{"type": "indie_regex", "pattern": r"kaber vasuki|kurangan"}]},
        {"slug": "arivu_paal_dabba", "name": "Arivu & Paal Dabba", "category": "By Indie", "emoji": "⚡", "desc": "High-octane conscious rap and infectious Chennai street flows.", "rules": [{"type": "indie_regex", "pattern": r"arivu|paal dabba|therukural"}]},
        {"slug": "vaisagh", "name": "Vaisagh Indie Collection", "category": "By Indie", "emoji": "🎧", "desc": "Catchy melodies, relatable lyrics, and viral indie bangers by Vaisagh.", "rules": [{"type": "indie_regex", "pattern": r"vaisagh"}]},
        {"slug": "sean_roldan_pradeep_indie", "name": "Sean Roldan & Pradeep Kumar Indie", "category": "By Indie", "emoji": "🎼", "desc": "Unplugged acoustic soul, live sessions, and indie compositions by Sean Roldan & Pradeep Kumar.", "rules": [{"type": "indie_regex", "pattern": r"sean roldan|pradeep kumar"}]}
    ]
}

# Populate Category 1: By Artist (Each artist gets separate All Songs, Hits, and Underrated slugs)
for a in TOP_ARTISTS:
    # 1. Complete Artist Collection slug (By Artist)
    TAXONOMY["artist"].append({
        "slug": f"{a['slug_base']}",
        "name": f"{a['name']}",
        "category": "By Artist",
        "emoji": a["emoji"],
        "desc": f"The complete discography & essential catalog of {a['name']}.",
        "rules": [
            {"type": "artist_all", "artist_pat": a["filter"], "role": a.get("role", "composer"), "exclude_pat": a.get("exclude_filter")}
        ]
    })
    # 2. Artist Hits slug
    TAXONOMY["artist"].append({
        "slug": f"{a['slug_base']}_hits",
        "name": f"{a['name']} Hits",
        "category": "By Artist",
        "emoji": a["emoji"],
        "desc": f"Blockbusters, chartbusters & signature hits by {a['name']}.",
        "rules": [
            {"type": "artist_hits", "artist_pat": a["filter"], "hit_pat": a["hit_keywords"], "role": a.get("role", "composer"), "exclude_pat": a.get("exclude_filter")}
        ]
    })
    # 3. Artist Underrated slug
    TAXONOMY["artist"].append({
        "slug": f"{a['slug_base']}_underrated",
        "name": f"{a['name']} Underrated",
        "category": "By Artist",
        "emoji": "💎",
        "desc": f"Hidden gems, deep cuts & lesser-known masterpieces by {a['name']}.",
        "rules": [
            {"type": "artist_underrated", "artist_pat": a["filter"], "underrated_pat": a["underrated_keywords"], "role": a.get("role", "composer"), "exclude_pat": a.get("exclude_filter")}
        ]
    })

# Populate Category 8: By Year (63 active years in discography, 1960 to 2026)
MISSING_SCRAPE_YEARS = {1990, 1991, 1993, 1995}
for yr in range(1960, 2027):
    if yr in MISSING_SCRAPE_YEARS:
        continue
    TAXONOMY["year"].append({
        "slug": str(yr),
        "name": str(yr),
        "category": "By Year",
        "emoji": "📅",
        "desc": f"Complete Tamil cinema soundtrack discography & essential releases of {yr}.",
        "rules": [
            {"type": "exact_year", "year": yr}
        ]
    })


def init_playlist_db(db_path: Path, pl_meta: dict):
    """Initialize a dedicated playlist SQLite database file."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS playlist_info (
            key TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position INTEGER NOT NULL,
            track_title TEXT NOT NULL,
            album_title TEXT NOT NULL,
            year INTEGER,
            composer TEXT,
            singers TEXT,
            lyricist TEXT,
            duration TEXT,
            track_type TEXT DEFAULT 'song',
            stream_url TEXT DEFAULT '',
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
        CREATE INDEX IF NOT EXISTS idx_tracks_title ON tracks(track_title);
        CREATE INDEX IF NOT EXISTS idx_tracks_tier ON tracks(evidence_tier);
        CREATE INDEX IF NOT EXISTS idx_tracks_year ON tracks(year);
        """)

        # Insert metadata
        info_items = [
            ("slug", pl_meta["slug"]),
            ("name", pl_meta["name"]),
            ("category", pl_meta["category"]),
            ("emoji", pl_meta["emoji"]),
            ("description", pl_meta["desc"]),
            ("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            ("total_tracks", "0")
        ]
        conn.executemany("INSERT INTO playlist_info (key, value) VALUES (?, ?);", info_items)

    return conn


def clean_meta_text(s):
    if not s:
        return ""
    s = re.sub(r'style="[^"]*"', '', s, flags=re.I)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('|', ' ').replace('}', ' ').replace('{', ' ')
    return " ".join(s.split()).strip()


def load_all_discography_tracks():
    """Load all tracks from tamil_discography.db."""
    if not DISCO_DB.exists():
        raise FileNotFoundError(f"Database {DISCO_DB} not found!")

    conn = sqlite3.connect(DISCO_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    sql = """
        SELECT 
            t.id AS track_id,
            t.title AS track_title,
            t.singers,
            t.lyricist,
            t.raga,
            t.duration,
            COALESCE(t.track_type, 'song') AS track_type,
            COALESCE(t.views_tier, '') AS views_tier,
            COALESCE(t.views_count, 0) AS views_count,
            COALESCE(t.stream_url, '') AS stream_url,
            t.evidence_tier,
            t.historical_evidence_score,
            t.evidence_confidence,
            t.scoring_version,
            a.id AS album_id,
            a.title AS album_title,
            a.year,
            a.composer,
            a.director,
            a.cast,
            COALESCE(a.album_type, 'film') AS album_type,
            COALESCE(a.label, '') AS label
        FROM tracks t
        JOIN albums a ON t.album_id = a.id
        WHERE t.title IS NOT NULL AND t.title != ''
        ORDER BY a.year DESC, a.title ASC, t.id ASC;
    """
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Playlists that exclusively host instrumental/music pieces
INSTRUMENTAL_ONLY_SLUGS = {"instrumental", "tamil_instrumental_bgm", "mass_hero_bgm"}
# Playlists that can accept both calm vocal songs and ambient music
INSTRUMENTAL_ALLOWED_SLUGS = {"studying_focus", "background_music", "meditation"}


def check_artist_match(composer, singers, artist_pat, role="composer", exclude_pat=None):
    """
    Strict role-scoped artist classification preventing cross-role / substring collisions.
    - If role == 'composer': checks 'composer' column. Can check 'singers' only if the composer
      personally sang the track, and does NOT match exclude_pat. NEVER checks cast/director/album.
    - If role == 'singer': strictly checks 'singers' column (and composer if singer also composed).
    """
    comp = clean_meta_text(composer)
    sing = clean_meta_text(singers)

    if role == "composer":
        # Check composer field first
        if comp and re.search(artist_pat, comp, re.I):
            if not (exclude_pat and re.search(exclude_pat, comp, re.I)):
                return True
        # Check singers field (for self-sung tracks, e.g. Deva gaana or Rahman vocals)
        if sing and re.search(artist_pat, sing, re.I):
            if not (exclude_pat and re.search(exclude_pat, sing, re.I)):
                return True
        return False

    elif role == "singer":
        if sing and re.search(artist_pat, sing, re.I):
            if not (exclude_pat and re.search(exclude_pat, sing, re.I)):
                return True
        # Edge case: some singers also compose
        if comp and re.search(artist_pat, comp, re.I):
            if not (exclude_pat and re.search(exclude_pat, comp, re.I)):
                return True
        return False

    return False


def matches_rules(track, rules, playlist_slug=None, playlist_category=None):
    """Determine if a track matches the playlist rules."""
    track_type = track.get("track_type", "song")
    album_type = track.get("album_type", "film")

    # Zero Collision Invariant: Strict segregation between cinema catalog and independent releases
    if playlist_category == "By Indie":
        if album_type != "indie_single":
            return False, None
    else:
        # Standard cinema playlists must never be polluted by independent YouTube singles
        if playlist_slug != "indie" and album_type == "indie_single":
            return False, None

    # If it is an instrumental-only playlist, strictly require non-song music/instrumental
    if playlist_slug in INSTRUMENTAL_ONLY_SLUGS:
        if track_type != "instrumental":
            return False, None
    # For standard song playlists, strictly exclude non-song music/instrumental
    elif playlist_slug not in INSTRUMENTAL_ALLOWED_SLUGS:
        if track_type == "instrumental":
            return False, None

    t_title = clean_meta_text(track.get("track_title", ""))
    a_title = clean_meta_text(track.get("album_title", ""))
    composer = clean_meta_text(track.get("composer", ""))
    singers = clean_meta_text(track.get("singers", ""))
    raga = clean_meta_text(track.get("raga", ""))
    year = track.get("year") or 0
    views_tier = track.get("views_tier", "")
    views_count = track.get("views_count") or 0
    evidence_tier = track.get("evidence_tier") or ""
    historical_evidence_score = track.get("historical_evidence_score") or 0

    # Scope 1: Strictly song title (ZERO cast/director/label/notes pollution)
    song_scope = t_title.lower()

    # Scope 2: Film context (song title, album title)
    film_scope = f"{t_title} {a_title}".lower()

    # Scope 3: Music scope (track title, album title, composer, singers)
    # Cast, director, and label are permanently excluded
    music_scope = f"{t_title} {a_title} {composer} {singers}".lower()

    for r in rules:
        rtype = r["type"]

        if rtype == "indie_all":
            if album_type == "indie_single":
                return True, "Indie All match"

        elif rtype == "indie_views":
            tiers = r.get("tiers", [])
            if views_tier in tiers:
                return True, f"Indie Views Tier match: {views_tier}"
            if "tier_1_mega" in tiers and views_count >= 50000000:
                return True, f"Indie Views Count match: {views_count}"
            if "tier_2_popular" in tiers and 10000000 <= views_count < 50000000:
                return True, f"Indie Views Count match: {views_count}"
            if "tier_3_emerging" in tiers and 1000000 <= views_count < 10000000:
                return True, f"Indie Views Count match: {views_count}"
            if "tier_4_underground" in tiers and views_count < 1000000:
                return True, f"Indie Views Count match: {views_count}"

        elif rtype == "indie_regex":
            pat = r["pattern"]
            if re.search(pat, music_scope, re.I):
                return True, f"Indie Regex match: {pat[:25]}"

        elif rtype == "artist_all":
            artist_pat = r["artist_pat"]
            role = r.get("role", "composer")
            exclude_pat = r.get("exclude_pat")
            if check_artist_match(composer, singers, artist_pat, role, exclude_pat):
                return True, f"Artist All match: {artist_pat[:15]}"

        elif rtype == "artist_hits":
            artist_pat = r["artist_pat"]
            hit_pat = r["hit_pat"]
            role = r.get("role", "composer")
            exclude_pat = r.get("exclude_pat")
            if check_artist_match(composer, singers, artist_pat, role, exclude_pat):
                if not hit_pat or re.search(hit_pat, film_scope, re.I):
                    return True, f"Artist Hit match: {artist_pat[:15]}"

        elif rtype == "artist_underrated":
            artist_pat = r["artist_pat"]
            underrated_pat = r["underrated_pat"]
            role = r.get("role", "composer")
            exclude_pat = r.get("exclude_pat")
            if check_artist_match(composer, singers, artist_pat, role, exclude_pat):
                if re.search(underrated_pat, film_scope, re.I):
                    return True, f"Artist Underrated match: {artist_pat[:15]}"

        elif rtype == "year_range":
            if r["start"] <= year <= r["end"]:
                return True, f"Year match: {year} in [{r['start']}-{r['end']}]"

        elif rtype == "exact_year":
            if year == r["year"]:
                return True, f"Exact year match: {year}"

        elif rtype == "keyword":
            pat = r["pattern"]
            exclude_pat = r.get("exclude_pattern")

            # Determine appropriate search target based on playlist category
            if playlist_category in ("By Mood", "By Activity", "By Relationship & Emotion"):
                search_target = song_scope
            elif playlist_slug in ("devotional", "pop", "rock", "lofi", "phonk", "sad_melody", "kuthu_dance", "folk_village"):
                search_target = song_scope
            elif playlist_slug in ("mass_hero_bgm", "tamil_melody", "tamil_instrumental_bgm"):
                search_target = film_scope
            else:
                search_target = music_scope

            # Specific negative filters for sensitive emotional playlists
            if playlist_slug in ("sad", "heartbreak", "breakup", "sad_melody"):
                if re.search(r"\b(party|dance|kuthu|kondattam|celebration|jolly|rowdy)\b", song_scope, re.I):
                    continue

            if playlist_slug in ("peaceful", "calm", "sleeping", "meditation"):
                if re.search(r"\b(kuthu|danga|verithanam|badass|fight|action|rowdy|item|sarakku|neruppu|thee|adra)\b", song_scope, re.I):
                    continue

            if playlist_slug in ("studying_focus", "background_music"):
                if re.search(r"\b(badass|verithanam|fight|action|kuthu|mass|teaser|hukum)\b", song_scope, re.I):
                    continue

            if re.search(pat, search_target, re.I):
                if not (exclude_pat and re.search(exclude_pat, search_target, re.I)):
                    return True, f"Keyword match: {pat[:20]}"

        elif rtype == "composer":
            pat = r["pattern"]
            exclude_pat = r.get("exclude_pat")
            if re.search(pat, composer, re.I):
                if not (exclude_pat and re.search(exclude_pat, composer, re.I)):
                    return True, f"Composer match: {pat}"

        elif rtype == "gaana_special":
            if re.search(r"\bjana\s*gana\b", t_title, re.I):
                continue
            if re.search(r"\b(gaana|gana|marana\s*gaana|danga|tasakku|sodakku|aluma|aaluma|dapankuthu|local\s*gaana|chennai\s*gaana|kuthu\s*pattu)\b", t_title, re.I):
                return True, "Gaana keyword match in title"
            is_deva_singer = bool(re.search(r"\bdeva\b", singers, re.I) and not re.search(r"\b(mahadevan|vasudevan|prabhu\s*deva)\b", singers, re.I))
            is_deva_composer = bool(re.search(r"\bdeva\b", composer, re.I) and not re.search(r"\b(mahadevan|vasudevan|prabhu\s*deva)\b", composer, re.I))
            if is_deva_singer:
                return True, "Deva vocal gaana"
            if is_deva_composer and re.search(r"\b(gana|kuthu|local|chennai|auto|pattas|podu|thirunelveli|madurai|briyani|sarakku|meen|vethala|ayya|salem|dappakuthu)\b", t_title, re.I):
                return True, "Deva composed street gaana"

        elif rtype in ("love_duet", "romantic_duet"):
            has_multiple_singers = bool(singers and ("," in singers or "&" in singers or " and " in singers.lower() or "with" in singers.lower()))
            if not has_multiple_singers:
                continue
            if re.search(r"\b(theme|bgm|score|instrumental|sogam|maranam|theeyil|saavu|oppari|funeral|fight|action|gaana|gana|kuthu|danga|tasakku|sodakku|aluma|aaluma|verithanam|dappakuthu)\b", song_scope, re.I):
                continue
            if re.search(r"\b(kadhal|kaadhal|anbe|anbu|uyire|priya|idhayame|penne|azhagi|azhage|manasellam|kannodu|malare|malargale|vaseegara|enrenrum|ennodu|unale|nenjukkul|kannum|partha|roja|kannukulle|adada|munbe|kanmani|chellam|kalyana|valai|thandhai|thenpandi|vaadi|poongatru)\b", song_scope, re.I):
                return True, "Romantic duet match"
            if evidence_tier in ("tier_1_mega", "tier_2_popular") and not re.search(r"\b(kuthu|danga|tasakku|sodakku|aluma|verithanam)\b", song_scope, re.I):
                return True, "Popular duet match"

        elif rtype == "all_time_hits":
            if evidence_tier in ("tier_1_mega", "tier_2_popular") or views_count >= 10000000 or historical_evidence_score >= 65:
                return True, "Evidence-based all time hit"
            is_maestro = bool(re.search(r"\b(a\.?\s*r\.?\s*rahman|ilaiyaraaja|ilayaraja|harris\s*jayaraj|yuvan\s*shankar\s*raja|anirudh|vidyasagar|m\.?\s*s\.?\s*viswanathan)\b|\bdeva\b", composer, re.I) and not re.search(r"\b(mahadevan|vasudevan|prabhu\s*deva)\b", composer, re.I))
            if is_maestro:
                blockbuster_films = r"\b(baasha|padayappa|muthu|roja|bombay|gentleman|annamalai|thalapathi|mouna ragam|nayakan|16 vayathinile|sankarabharanam|vasantha maligai|minnale|kaakha kaakha|ghilli|sivaji|enthiran|aaytha ezhuthu|alaipayuthey|pudhupettai|paiyaa|master|leo|vikram|jailer|chandramukhi|indian|mudhalvan|kadhalan|jeans|kushi|pithamagan|sethu|anniyan|vettaiyaadu|vaaranam aayiram|vinnaithaandi|mankatha|petta|thuppakki|mersal|bigil|theri|kathi|viswasam)\b"
                if re.search(blockbuster_films, a_title, re.I):
                    return True, "Blockbuster film maestro hit"

        elif rtype == "duet":
            if singers and ("," in singers or "&" in singers or "and" in singers.lower()):
                return True, "Duet vocal combination"
            if re.search(r["pattern"], music_scope, re.I):
                return True, "Duet pattern matched"

        elif rtype == "raga_or_keyword":
            carnatic_whitelist = r"\b(raga|ragam|carnatic|sindhu\s*bhairavi|charukesi|hamsadhwani|shankarabharanam|sankarabharanam|keeravani|mayamalavagowla|abheri|sivaranjani|hindolam|bilahari|kambhoji|natabhairavi|darbari\s*kanada|ananda\s*bhairavi)\b"
            if raga and re.search(carnatic_whitelist, raga, re.I):
                return True, f"Carnatic raga: {raga}"
            carnatic_film_or_terms = r"\b(sindhu\s*bhairavi|sankarabharanam|shankarabharanam|thillana\s*mohanambal|salangai\s*oli|mahaganapathim|mari\s*mari\s*ninne|varnam|keerthanam|kriti|thillana|swaram|ragam\s*thanam\s*pallavi)\b"
            if re.search(carnatic_film_or_terms, film_scope, re.I):
                if not re.search(r"\b(theme|bgm|score|remix|rap|fight|action|badass|verithanam|kuthu|danga)\b", song_scope, re.I):
                    return True, "Carnatic classical match"

    return False, None


def generate_all_playlists(target_section=None):
    """Build individual SQLite playlist databases."""
    # Pre-harvest all existing cached Spotify URIs across local databases to preserve match state
    cached_spotify_uris = {}
    if PLAYLISTS_DIR.exists():
        for existing_db in PLAYLISTS_DIR.glob("**/*.db"):
            try:
                c = sqlite3.connect(existing_db)
                for row in c.execute("SELECT discography_track_id, track_title, album_title, spotify_uri FROM tracks WHERE spotify_uri IS NOT NULL AND spotify_uri != '';"):
                    dt_id, tt, at, uri = row[0], row[1], row[2], row[3]
                    if dt_id:
                        cached_spotify_uris[("id", dt_id)] = uri
                    if tt and at:
                        cached_spotify_uris[("title_album", tt.lower().strip(), at.lower().strip())] = uri
                c.close()
            except Exception:
                pass

    if target_section:
        if target_section not in TAXONOMY:
            print(f"Error: Unknown section '{target_section}'. Valid sections: {list(TAXONOMY.keys())}")
            return
        sec_dir = PLAYLISTS_DIR / target_section
        if sec_dir.exists():
            for f in sec_dir.glob("*.db"):
                if f.name != "all_independent_songs.db":
                    f.unlink()
        sec_dir.mkdir(parents=True, exist_ok=True)
    else:
        if PLAYLISTS_DIR.exists():
            for f in PLAYLISTS_DIR.glob("**/*.db"):
                if f.name != "all_independent_songs.db":
                    f.unlink()
        PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)

    print("="*75)
    print(" 🚀 GENERATING STANDALONE PLAYLIST DATABASE FOR EACH SLUG")
    print("="*75)
    
    print("\n[1/3] Loading tracks from tamil_discography.db...")
    all_tracks = load_all_discography_tracks()
    print(f"      Loaded {len(all_tracks)} indexed tracks across 1960–2026.")

    sections_to_run = {target_section: TAXONOMY[target_section]} if target_section else TAXONOMY
    total_playlists = sum(len(items) for items in sections_to_run.values())
    print(f"\n[2/3] Generating {total_playlists} distinct database files under {PLAYLISTS_DIR}...")

    current_idx = 1
    for section_folder, playlist_list in sections_to_run.items():
        folder_path = PLAYLISTS_DIR / section_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        
        print(f"\n  📁 Section: [{section_folder.upper()}] ({len(playlist_list)} Individual Playlists)")
        
        for pl_meta in playlist_list:
            slug = pl_meta["slug"]
            db_file = folder_path / f"{slug}.db"
            conn = init_playlist_db(db_file, pl_meta)
            
            matched_records = []
            seen_keys = set()
            pos = 1
            # For indie section, sort deterministically by evidence tier, score, views, and year
            if section_folder == "indie":
                tier_order = {"tier_1_mega": 1, "tier_2_popular": 2, "tier_3_emerging": 3, "tier_4_underground": 4}
                track_source = sorted(
                    all_tracks,
                    key=lambda x: (
                        tier_order.get(x.get("evidence_tier"), 99),
                        -(x.get("historical_evidence_score") or 0.0),
                        -(x.get("views_count") or 0),
                        -(x.get("year") or 0),
                        x["track_id"]
                    )
                )
            # For active current year (2026), process newest tracks first (descending track_id)
            elif slug == "2026":
                track_source = sorted(all_tracks, key=lambda x: x["track_id"], reverse=True)
            else:
                track_source = all_tracks

            for t in track_source:
                is_match, reason = matches_rules(t, pl_meta["rules"], playlist_slug=slug, playlist_category=pl_meta.get("category"))
                if is_match:
                    t_clean = clean_meta_text(t["track_title"])
                    a_clean = clean_meta_text(t["album_title"])
                    if not t_clean:
                        continue
                    key = (t_clean.lower(), a_clean.lower())
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    c_clean = clean_meta_text(t["composer"])
                    s_clean = clean_meta_text(t["singers"])
                    yr = t["year"] or 0
                    ttype = t.get("track_type", "song")
                    surl = t.get("stream_url", "") or ""
                    
                    if t.get("album_type") == "indie_single":
                        sp_query = f"track:\"{t_clean}\" artist:\"{c_clean or s_clean}\""
                    else:
                        sp_query = f"track:\"{t_clean}\" album:\"{a_clean}\""
                        if c_clean and len(c_clean) < 30:
                            sp_query += f" artist:\"{c_clean}\""

                    # Restore cached Spotify URI if available
                    sp_uri = cached_spotify_uris.get(("id", t["track_id"])) or cached_spotify_uris.get(("title_album", t_clean.lower(), a_clean.lower())) or ""

                    matched_records.append((
                        pos,
                        t_clean,
                        a_clean,
                        yr,
                        c_clean,
                        s_clean,
                        clean_meta_text(t.get("lyricist", "")),
                        t.get("duration", "") or "",
                        ttype,
                        surl,
                        t.get("evidence_tier"),
                        t.get("historical_evidence_score"),
                        t.get("evidence_confidence"),
                        t.get("scoring_version"),
                        sp_query,
                        sp_uri,
                        t["track_id"],
                        reason
                    ))
                    pos += 1

            # Insert all matched tracks
            with conn:
                conn.executemany("""
                    INSERT INTO tracks (
                        position, track_title, album_title, year,
                        composer, singers, lyricist, duration, track_type,
                        stream_url, evidence_tier, historical_evidence_score,
                        evidence_confidence, scoring_version,
                        spotify_query, spotify_uri, discography_track_id, match_reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, matched_records)

                conn.execute("UPDATE playlist_info SET value = ? WHERE key = 'total_tracks';", (str(len(matched_records)),))

            conn.close()
            print(f"     [{current_idx:03d}/{total_playlists}] {pl_meta['emoji']} {pl_meta['name']:<35} -> {len(matched_records):>4} songs ({db_file.name})")
            current_idx += 1

    print("\n" + "="*75)
    print(" ✅ ALL REQUESTED PLAYLIST DATABASES GENERATED!")
    print("="*75)
    print(f"Total Standalone Databases : {total_playlists}")
    print(f"Directory                  : {PLAYLISTS_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate standalone playlist databases.")
    parser.add_argument("--section", "--category", type=str, default=None, help="Generate only a specific section (e.g. artist, mood, genre)")
    args = parser.parse_args()
    generate_all_playlists(target_section=args.section)

