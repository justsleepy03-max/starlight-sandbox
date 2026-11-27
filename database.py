def wipe_single_player(user_id):
    """Backs up current data, resets a single player's profile to starter defaults, and returns (found, backup_path)."""
    backup_path = backup_data()
    data = load_data()
    uid = str(user_id)

    if uid not in data or not isinstance(data[uid], dict):
        return False, backup_path

    data[uid] = ensure_player_defaults({})
    save_data(data)
    return True, backup_path
