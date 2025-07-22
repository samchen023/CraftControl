import json
import os
import sys

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(base_dir, "config.json")

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
