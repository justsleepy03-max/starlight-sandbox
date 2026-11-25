# Master item catalog for Starlight RPG (EPIC RPG 1:1 Replica + Starlight Custom)

SWORDS = {
    1: {"name": "rusty iron shortsword", "price": 100, "at": 1},
    2: {"name": "briarwood hunter bow", "price": 350, "at": 2},
    3: {"name": "moss-veined staff", "price": 800, "at": 3},
    4: {"name": "damp dagger of the depths", "price": 1500, "at": 4},
    5: {"name": "granite crag hammer", "price": 3000, "at": 5},
    6: {"name": "glacial frost spear", "price": 5500, "at": 6},
    7: {"name": "magma core greatsword", "price": 10000, "at": 7},
    8: {"name": "dune-scourge scimitar", "price": 18000, "at": 8},
    9: {"name": "knight's oath broadsword", "price": 30000, "at": 9},
    10: {"name": "abyssal tide trident", "price": 50000, "at": 10},
    11: {"name": "void edge", "price": 75000, "at": 11},
    12: {"name": "sunburst seraph blade", "price": 120000, "at": 12},
    13: {"name": "temporal crossbow", "price": 200000, "at": 13},
    14: {"name": "event horizon scythe", "price": 325000, "at": 14},
    15: {"name": "starlight greatsword", "price": 500000, "at": 15},
}

ARMORS = {
    1: {"name": "worn leather tunic", "price": 150, "def": 2},
    2: {"name": "forest scout guard", "price": 450, "def": 4},
    3: {"name": "rune-woven robes", "price": 1000, "def": 7},
    4: {"name": "dampscale mail", "price": 2000, "def": 11},
    5: {"name": "iron-riveted leather", "price": 3800, "def": 16},
    6: {"name": "frost-guard fur parka", "price": 6800, "def": 22},
    7: {"name": "magma plate armor", "price": 12000, "def": 30},
    8: {"name": "dune-strider carapace", "price": 21000, "def": 40},
    9: {"name": "veteran knight's cuirass", "price": 35000, "def": 52},
    10: {"name": "abyssal pressure suit", "price": 60000, "def": 66},
    11: {"name": "void-tethered shroud", "price": 90000, "def": 82},
    12: {"name": "celestial aegis", "price": 120000, "def": 100},
    13: {"name": "chrono-shift ward", "price": 220000, "def": 125},
    14: {"name": "event horizon vestments", "price": 350000, "def": 155},
    15: {"name": "singularity carapace", "price": 450000, "def": 200},
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
    "celestial egg": {"price": 75000, "desc": "Hatches into a legendary cosmic entity!"},
    "void egg": {"price": 150000, "desc": "Hatches rare abyssal companions with unique buffs."},
    "transcendent egg": {"price": 1000000, "desc": "The ultimate egg containing a divine Starlight Prime Avatar!"}
}

MISC_ITEMS = {
    "minor hp bottle": {"price": 100, "desc": "Restores +35 HP with /heal (quick top-up)."},
    "greater hp bottle": {"price": 1250, "desc": "Restores +120 HP with /heal (solid recovery)."},
    "starlight elixir": {"price": 12000, "desc": "Restores +250 HP and grants +25 Max HP via /heal."},
    "celestial vitality draught": {"price": 150000, "desc": "Restores +500 HP and grants +75 Max HP via /heal."},
    "transcendent life flask": {"price": 750000, "desc": "Restores +1,000 HP and grants +150 Max HP via /heal."},
    "dungeon key": {"price": 5000, "desc": "Required to enter the /dungeon"},
    "lottery ticket": {"price": 50, "desc": "To join the /lottery"},
    "seed": {"price": 4000, "desc": "Used to /farm"},
    "portable workbench": {"price": 10000, "desc": "Allows you to craft on the go anywhere in the field."},
    "common lootbox": {"price": 800, "desc": "Contains a few items, open with /open"},
    "uncommon lootbox": {"price": 6000, "desc": "Contains some items, open with /open"},
    "rare lootbox": {"price": 40000, "desc": "Contains many items, open with /open"},
    "epic lootbox": {"price": 150000, "desc": "Contains a lot of items, open with /open"},
    "edgy lootbox": {"price": 420666, "desc": "Contains A LOT of items, open with /open"},
    "mystery artifact crate": {"price": 20000, "desc": "Drops rare crafting materials from random biomes."}
}

BUNDLES = {
    "gatherer's pack": {"price": 400, "contents": {"starblossom": 10, "starlight_bulb": 5}},
    "miner's crate": {"price": 600, "contents": {"iron_ore": 10, "celestial_ore": 3}},
    "hunter's cache": {"price": 750, "contents": {"goblin_fang": 5, "slime_jelly": 5, "shadow_pelt": 2}},
    "cosmic catalyst bundle": {"price": 1500, "contents": {"dragon_scale": 1, "serpentarius": 1, "stardust": 250}}
}

RESOURCES = {
    "wood": {"price": 15, "desc": "Sturdy timber for basic crafting."},
    "fish": {"price": 20, "desc": "Freshly caught from local waters."},
    "iron ore": {"price": 60, "desc": "Unrefined metal for mid-tier forging."},
    "soft bark": {"price": 30, "desc": "Whispering Woods material."},
    "ancient stone": {"price": 50, "desc": "Crumbling Ruins relic fragment."},
    "river pearl": {"price": 85, "desc": "Sunken Riverbank gem."},
    "crystal shard": {"price": 150, "desc": "Glimmering cavern crystal."},
    "magma core": {"price": 400, "desc": "Volcanic Caldera heat source."},
    "dragon scale": {"price": 1200, "desc": "Heat-forged scale from Dragon's Spire."},
    "starlight essence": {"price": 2500, "desc": "Celestial Sanctuary energy."},
    "void matter": {"price": 5000, "desc": "Unstable abyssal crafting material."},
    "singularity core": {"price": 15000, "desc": "Endgame cosmic catalyst."}
}

PLUSHIES = {
    "slime plushie": {"price": 2500, "desc": "Squishy, slightly damp, and very huggable."},
    "goblin plushie": {"price": 5000, "desc": "Looks like it might steal your spare change."},
    "alpha wolf plushie": {"price": 12000, "desc": "Fluffy miniature of the Whispering Woods boss."},
    "starlight spirit plushie": {"price": 25000, "desc": "Glows softly in the dark. A fan favorite!"},
    "shadow mouse plushie": {"price": 50000, "desc": "Sneaky collectible plush for true hoarders."},
    "crystal golem plushie": {"price": 100000, "desc": "Surprisingly soft despite looking like solid rock."},
    "ancient dragon plushie": {"price": 250000, "desc": "Stuffed with real fire-resistant fluff."},
    "golden starlight plushie": {"price": 1000000, "desc": "Pure flexing rights. Limited sandbox edition."}
}


def get_sword_info(tier_or_name) -> tuple[int, dict] | None:
    if isinstance(tier_or_name, int):
        return (tier_or_name, SWORDS[tier_or_name]) if tier_or_name in SWORDS else None
    cleaned = str(tier_or_name).strip().lower()
    if cleaned.isdigit():
        tier = int(cleaned)
        return (tier, SWORDS[tier]) if tier in SWORDS else None
    for tier, data in SWORDS.items():
        if data["name"].lower() == cleaned:
            return tier, data
    return None


def get_armor_info(tier_or_name) -> tuple[int, dict] | None:
    if isinstance(tier_or_name, int):
        return (tier_or_name, ARMORS[tier_or_name]) if tier_or_name in ARMORS else None
    cleaned = str(tier_or_name).strip().lower()
    if cleaned.isdigit():
        tier = int(cleaned)
        return (tier, ARMORS[tier]) if tier in ARMORS else None
    for tier, data in ARMORS.items():
        if data["name"].lower() == cleaned:
            return tier, data
    return None
