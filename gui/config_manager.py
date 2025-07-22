import json
import os
import sys

# 建議儲存在使用者主目錄下的 .config 目錄
def get_config_path():
    if getattr(sys, 'frozen', False):
        base_dir = os.path.expanduser("~/.config/mcmanager")
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "config.json")

CONFIG_PATH = get_config_path()

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def get_paper_count():
    config = load_config()
    return config.get("paper_count", None)

def set_paper_count(n):
    config = load_config()
    config["paper_count"] = n
    save_config(config)
