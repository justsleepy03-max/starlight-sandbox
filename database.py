import json
import os

DATA_DIR = "/app/data"
DATA_FILE = os.path.join(DATA_DIR, "rpg_data.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_data(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_player(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "wallet": 100,
            "bank": 0,
            "hp": 100,
            "max_hp": 100,
            "level": 1,
            "xp": 0,
            "area": 1,
            "inventory": {},
            "equipment": {"sword": None, "armor": None, "horse": None},
            "cooldowns": {}
        }
        save_data(data)
    return data[uid]

def update_player(user_id, player_data):
    data = load_data()
    data[str(user_id)] = player_data
    save_data(data)
