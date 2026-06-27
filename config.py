# ── Rarity ──────────────────────────────────────────────────────────
RARITY_EMOJI = {
    "L": "🟡",   # Legendary
    "E": "🟣",   # Epic
    "R": "🔵",   # Rare
    "C": "⚪",   # Common
    "U": "🟢",   # Uncommon (future use)
}

RARITY_LABEL = {
    "L": "Legendary",
    "E": "Epic",
    "R": "Rare",
    "C": "Common",
    "U": "Uncommon",
}

RARITY_COLOR = {
    "L": 0xFFD700,   # Gold
    "E": 0x9B59B6,   # Purple
    "R": 0x3498DB,   # Blue
    "C": 0x95A5A6,   # Grey
    "U": 0x2ECC71,   # Green
}

# ── Elements ─────────────────────────────────────────────────────────
ELEMENT_EMOJI = {
    "Fire":  "🔥",
    "Water": "💧",
    "Wind":  "🌪️",
    "Earth": "🌿",
    "Light": "✨",
    "Dark":  "🌑",
}

# ── Summon rates ─────────────────────────────────────────────────────
SUMMON_RATES = {
    "L": 0.03,   # 3%
    "E": 0.12,   # 12%
    "R": 0.30,   # 30%
    "C": 0.55,   # 55%
}

# ── Economy ──────────────────────────────────────────────────────────
SUMMON_COST_HON    = 300    # Cost per single summon
MULTI_SUMMON_COUNT = 10     # !multi pulls
MULTI_SUMMON_COST  = 2700   # 10% discount
DAILY_HON_REWARD   = 500
HOURLY_HON_REWARD  = 100

# ── Pagination ───────────────────────────────────────────────────────
CHARS_PER_PAGE = 15
GALLERY_PER_PAGE = 9

# ── Banners ──────────────────────────────────────────────────────────
BANNERS = {
    "1": {
        "name": "Swarajya Banner",
        "description": "Standard banner — summon Maratha warriors!",
        "pool": ["C", "R", "E"],
        "cost": SUMMON_COST_HON,
    },
    "2": {
        "name": "Hindavi Swarajya Banner",
        "description": "⚡ Limited banner — chance for Legendary warriors!",
        "pool": ["R", "E", "L"],
        "cost": SUMMON_COST_HON + 100,
    },
}

# ── Colors ───────────────────────────────────────────────────────────
COLOR_MAIN    = 0xFF6600   # Maratha saffron
COLOR_SUCCESS = 0x2ECC71
COLOR_ERROR   = 0xE74C3C
COLOR_INFO    = 0x3498DB
COLOR_GOLD    = 0xFFD700
