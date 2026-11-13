# Master item catalog for Starlight RPG (EPIC RPG 1:1 Replica + Starlight Custom)

SWORDS = {
    1: {"name": "basic sword", "price": 150, "at": 1},
    2: {"name": "epic sword", "price": 1000, "at": 3},
    3: {"name": "hyper sword", "price": 5000, "at": 8},
    4: {"name": "ultimate sword", "price": 25000, "at": 20},
}

ARMORS = {
    1: {"name": "basic armor", "price": 200, "def": 2},
    2: {"name": "epic armor", "price": 1200, "def": 6},
    3: {"name": "hyper armor", "price": 6000, "def": 15},
    4: {"name": "ultimate armor", "price": 30000, "def": 40},
}

HORSES = {
    1: {"name": "basic horse", "price": 500, "tier": 1},
    2: {"name": "good horse", "price": 2500, "tier": 2},
    3: {"name": "great horse", "price": 10000, "tier": 3},
    4: {"name": "super horse", "price": 50000, "tier": 4},
}

PET_EGGS = {
    "common egg": {"price": 1000, "desc": "Hatches into a common companion!"},
    "golden egg": {"price": 15000, "desc": "Hatches into a rare Starlight pet!"},
    "celestial egg": {"price": 75000, "desc": "Hatches into a legendary cosmic entity!"}
}

MISC_ITEMS = {
    "life potion": {"price": 25, "desc": "Restore your life with /heal"},
    "dungeon key": {"price": 5000, "desc": "Required to enter the /dungeon"},
    "lottery ticket": {"price": 50, "desc": "To join the /lottery"},
    "seed": {"price": 4000, "desc": "Used to /farm"},
    "common lootbox": {"price": 800, "desc": "Contains a few items, open with /open"},
    "uncommon lootbox": {"price": 6000, "desc": "Contains some items, open with /open"},
    "rare lootbox": {"price": 40000, "desc": "Contains many items, open with /open"},
    "epic lootbox": {"price": 150000, "desc": "Contains a lot of items, open with /open"},
    "edgy lootbox": {"price": 420666, "desc": "Contains A LOT of items, open with /open"},
    "life boost a": {"price": 10000, "desc": "Provides +10 LIFE (temporary)"},
    "life boost b": {"price": 100000, "desc": "Provides +25 LIFE (temporary)"},
    "life boost c": {"price": 1000000, "desc": "Provides +50 LIFE (temporary)"}
}

BUNDLES = {
    "gatherer's pack": {"price": 400, "contents": {"starblossom": 10, "starlight_bulb": 5}},
    "miner's crate": {"price": 600, "contents": {"iron_ore": 10, "celestial_ore": 3}},
    "hunter's cache": {"price": 750, "contents": {"goblin_fang": 5, "slime_jelly": 5, "shadow_pelt": 2}},
    "cosmic catalyst bundle": {"price": 1500, "contents": {"dragon_scale": 1, "serpentarius": 1, "stardust": 250}}
}
