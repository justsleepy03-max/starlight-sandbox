from datetime import datetime, timezone
import json
import os
import shutil

DATA_DIR = "/app/data"
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
DATA_FILE = os.path.join(DATA_DIR, "rpg_data.json")
TEMP_FILE = os.path.join(DATA_DIR, "rpg_data.json.tmp")

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
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.replace(TEMP_FILE, DATA_FILE)


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

    # Spire & NG+ progression fields
    player.setdefault("spire_floor", 1)
    player.setdefault("spire_ng_unlocked", 0)
    player.setdefault("spire_ng_current", 0)

    if not isinstance(player.get("inventory"), dict):
        player["inventory"] = {}
    if not isinstance(player.get("cooldowns"), dict):
        player["cooldowns"] = {}

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
            "spire_floor": 1,
            "spire_ng_unlocked": 0,
            "spire_ng_current": 0,
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


def backup_data():
    """Creates a timestamped backup of rpg_data.json before destructive actions."""
    if not os.path.exists(DATA_FILE):
        return None
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"rpg_data_backup_{timestamp}.json")
    shutil.copy2(DATA_FILE, backup_path)
    return backup_path


def wipe_all_players():
    """Backs up current data, resets all player profiles to fresh starter defaults, and returns (wiped_count, backup_path)."""
    backup_path = backup_data()
    data = load_data()

    wiped_count = 0
    new_data = {}
    for uid, profile in data.items():
        if isinstance(profile, dict):
            new_data[str(uid)] = ensure_player_defaults({})
            wiped_count += 1
        else:
            # Preserve any non-player metadata keys if they exist
            new_data[str(uid)] = profile

    save_data(new_data)
    return wiped_count, backup_path
