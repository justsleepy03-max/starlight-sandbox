import json
import os

DATA_DIR = "/app/data"
DATA_FILE = os.path.join(DATA_DIR, "rpg_data.json")

DEFAULT_EQUIPMENT = {
    "sword": None,
    "armor": None,
    "horse": None,
    "pet": None,
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def ensure_player_defaults(player):
    if not isinstance(player, dict):
        player = {}

    player.setdefault("wallet", 100)
    player.setdefault("bank", 0)
    player.setdefault("hp", 100)
    player.setdefault("max_hp", 100)
    player.setdefault("level", 1)
    player.setdefault("xp", 0)
    player.setdefault("area", 1)
    player.setdefault("inventory", {})
    player.setdefault("cooldowns", {})

    if not isinstance(player.get("equipment"), dict):
        player["equipment"] = dict(DEFAULT_EQUIPMENT)
    else:
        for slot, default_val in DEFAULT_EQUIPMENT.items():
            player["equipment"].setdefault(slot, default_val)

    return player


def get_player(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data or not isinstance(data[uid], dict):
        data[uid] = ensure_player_defaults({
            "wallet": 100,
            "bank": 0,
            "hp": 100,
            "max_hp": 100,
            "level": 1,
            "xp": 0,
            "area": 1,
            "inventory": {},
            "equipment": dict(DEFAULT_EQUIPMENT),
            "cooldowns": {},
        })
        save_data(data)
    else:
        before = json.dumps(data[uid], sort_keys=True)
        ensure_player_defaults(data[uid])
        if json.dumps(data[uid], sort_keys=True) != before:
            save_data(data)
    return data[uid]


def update_player(user_id, player_data):
    data = load_data()
    data[str(user_id)] = ensure_player_defaults(player_data)
    save_data(data)


def get_all_players():
    data = load_data()
    all_players = {}
    for uid, player in data.items():
        if isinstance(player, dict):
            all_players[str(uid)] = ensure_player_defaults(dict(player))
    return all_players
