import json
import os
import sys

# 取得打包後的執行檔或原始 script 所在目錄
if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(base_dir, "config.json")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("[錯誤] config.json 格式錯誤，將重新建立。")
        return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except PermissionError:
        print(f"[錯誤] 無法寫入設定檔：{CONFIG_PATH}")
        print("請勿將執行檔放在 /usr/bin/，請移到 ~/mcmanager/ 等可寫入資料夾。")
        sys.exit(1)

def get_paper_count():
    config = load_config()
    return config.get("paper_count", None)

def set_paper_count(n):
    config = load_config()
    config["paper_count"] = n
    save_config(config)
