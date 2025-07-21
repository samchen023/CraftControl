import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import os
import requests
import threading
import webbrowser
from controller import start_server, stop_server, is_server_running
from config_manager import get_paper_count, set_paper_count

APP_VERSION = "v1.0"
IS_WINDOWS = os.name == "nt"

# === GUI 變數先宣告 ===
status_var = None
log_box = None
status_labels = {}
paper_version_var = None
paper_version_combo = None
SERVER_PATHS = {}

# === log 函式 - 請放前面，供其他函式調用 ===
def log(msg):
    if log_box:
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)
    if status_var:
        status_var.set(msg)

# === 讀取 Paper Server 數量，若無設定跳出視窗詢問 ===
def ask_paper_count():
    count = get_paper_count()
    if count is None:
        count = simpledialog.askinteger("設定 Paper 數量", "請輸入要啟用幾個 Paper Server：", minvalue=1, maxvalue=100)
        if count is None:
            messagebox.showerror("錯誤", "未設定 Paper 數量，程式即將關閉。")
            exit()
        set_paper_count(count)
    return count

# === 根據 paper count 建立 SERVER_PATHS 字典 ===
def build_server_paths(paper_count):
    paths = {
        "BungeeCord": "servers/bungee/start.bat" if IS_WINDOWS else "servers/bungee/start.sh"
    }
    for i in range(1, paper_count + 1):
        name = f"Paper {i}"
        path = f"servers/paper{i}/start.bat" if IS_WINDOWS else f"servers/paper{i}/start.sh"
        paths[name] = path
    return paths

# === 自動建立資料夾與啟動腳本 ===
def ensure_server_dirs():
    for name, script_path in SERVER_PATHS.items():
        folder = os.path.dirname(script_path)
        os.makedirs(folder, exist_ok=True)
        # 啟動腳本會在自動修復時補，這裡先不寫入

# === 檢查缺失，日誌顯示 ===
def check_server_files():
    log("開始檢查伺服器資料夾檔案...")
    for name, script_path in SERVER_PATHS.items():
        folder = os.path.dirname(script_path)
        jar_path = os.path.join(folder, "paper.jar")
        script_exists = os.path.exists(script_path)
        jar_exists = os.path.exists(jar_path) if "paper" in name.lower() else True

        if not jar_exists:
            log(f"⚠️ {name} 缺少 paper.jar")
        if not script_exists:
            log(f"⚠️ {name} 缺少啟動腳本 ({script_path})")

# === 自動修復缺失項目(帶 Loading 視窗，非阻塞) ===
def auto_repair_missing():
    loading_win = tk.Toplevel(root)
    loading_win.title("請稍候")
    loading_win.geometry("300x100")
    loading_win.resizable(False, False)
    tk.Label(loading_win, text="正在自動修復缺失項目，請稍候...").pack(expand=True, padx=20, pady=20)
    loading_win.transient(root)
    loading_win.grab_set()

    def repair_task():
        try:
            version = paper_version_var.get().strip()
            if not version:
                log("無法修復：尚未選擇 Paper 版本")
                return

            api = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
            builds = requests.get(api).json()["builds"]
            latest = builds[-1]

            for name, script_path in SERVER_PATHS.items():
                folder = os.path.dirname(script_path)
                os.makedirs(folder, exist_ok=True)

                # 補啟動腳本
                if not os.path.exists(script_path):
                    if IS_WINDOWS:
                        with open(script_path, "w", encoding="utf-8") as f:
                            f.write(f"""@echo off
java -Xmx2G -jar paper.jar nogui
pause
""")
                    else:
                        with open(script_path, "w", encoding="utf-8") as f:
                            f.write(f"""#!/bin/bash
java -Xmx2G -jar paper.jar nogui
read -p "Press Enter to exit..."
""")
                        os.chmod(script_path, 0o755)
                    log(f"✅ 已補上啟動腳本：{name}")

                # 補 paper.jar
                if "paper" in name.lower():
                    jar_path = os.path.join(folder, "paper.jar")
                    if not os.path.exists(jar_path):
                        jar_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest}/downloads/paper-{version}-{latest}.jar"
                        r = requests.get(jar_url)
                        r.raise_for_status()
                        with open(jar_path, "wb") as f:
                            f.write(r.content)
                        log(f"✅ 已補上 paper.jar：{name}")

            log("✅ 所有伺服器資料夾修復完成")
        except Exception as e:
            log(f"❌ 自動修復失敗：{e}")
        finally:
            root.after(0, loading_win.destroy)

    threading.Thread(target=repair_task, daemon=True).start()

# === 控制伺服器 ===
def on_start(server_name):
    success, msg = start_server(server_name, SERVER_PATHS[server_name])
    log(msg)
    if not success:
        messagebox.showerror("錯誤", msg)

def on_stop(server_name):
    success, msg = stop_server(server_name)
    log(msg)
    if not success:
        messagebox.showerror("錯誤", msg)

def start_all():
    for name in SERVER_PATHS:
        on_start(name)

def stop_all():
    for name in SERVER_PATHS:
        on_stop(name)

def update_server_statuses():
    for name in SERVER_PATHS:
        running = is_server_running(name)
        lbl = status_labels.get(name)
        if lbl:
            lbl.config(text="🟢 運行中" if running else "🔴 未啟動", fg="green" if running else "red")
    root.after(3000, update_server_statuses)

# === 下載函式 ===
def download_latest_paper():
    version = paper_version_var.get().strip()
    if not version:
        messagebox.showerror("錯誤", "請選擇版本")
        return

    try:
        api = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
        builds = requests.get(api).json()["builds"]
        latest = builds[-1]
        log(f"開始下載 Paper {version} Build {latest} 到所有資料夾...")

        for name, script_path in SERVER_PATHS.items():
            if "paper" not in name.lower():
                continue

            folder = os.path.dirname(script_path)
            os.makedirs(folder, exist_ok=True)
            jar_path = os.path.join(folder, "paper.jar")

            if os.path.exists(jar_path):
                log(f"{name} 已存在 paper.jar，跳過")
                continue

            jar_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest}/downloads/paper-{version}-{latest}.jar"
            r = requests.get(jar_url)
            r.raise_for_status()
            with open(jar_path, "wb") as f:
                f.write(r.content)
            log(f"{name} 下載完成 paper.jar")
    except Exception as e:
        log(f"下載失敗：{e}")
        messagebox.showerror("下載失敗", str(e))

def download_latest_bungee():
    dest_folder = "servers/bungee"
    os.makedirs(dest_folder, exist_ok=True)
    jar_path = os.path.join(dest_folder, "BungeeCord.jar")

    if os.path.exists(jar_path):
        log("BungeeCord 已存在，跳過下載")
        return

    url = "https://ci.md-5.net/job/BungeeCord/lastSuccessfulBuild/artifact/bootstrap/target/BungeeCord.jar"
    try:
        r = requests.get(url)
        r.raise_for_status()
        with open(jar_path, "wb") as f:
            f.write(r.content)
        log("下載完成 BungeeCord")
    except Exception as e:
        log(f"BungeeCord 下載失敗：{e}")
        messagebox.showerror("下載失敗", str(e))

# === 載入 Paper 版本清單 ===
def load_paper_versions():
    try:
        log("正在載入 Paper 版本清單...")
        r = requests.get("https://api.papermc.io/v2/projects/paper")
        r.raise_for_status()
        data = r.json()
        versions = data.get("versions", [])
        if versions:
            versions.reverse()
            paper_version_combo['values'] = versions
            paper_version_combo.set(versions[0])
            log("版本載入完成")
            # 載入完版本才做自動修復
            auto_repair_missing()
        else:
            paper_version_combo['values'] = ["無法載入"]
            paper_version_combo.set("無法載入")
            log("找不到版本資料")
    except Exception as e:
        paper_version_combo['values'] = ["錯誤"]
        paper_version_combo.set("錯誤")
        log(f"版本載入失敗：{e}")

# === 修改 Paper Server 數量 ===
def change_paper_count():
    new_count = simpledialog.askinteger("修改 Paper 數量", "請輸入新的 Paper Server 數量：", minvalue=1, maxvalue=100)
    if new_count is not None:
        set_paper_count(new_count)
        messagebox.showinfo("請重新啟動", "已儲存設定，請重新啟動應用程式以套用")
        root.destroy()

# === 關於視窗 ===
def show_about():
    messagebox.showinfo("關於 CraftControl", f"CraftControl {APP_VERSION}\nMinecraft Server 控制面板")

# === 主程式開始 ===
paper_count = ask_paper_count()
SERVER_PATHS = build_server_paths(paper_count)

root = tk.Tk()
root.title(f"CraftControl {APP_VERSION} - Minecraft Server 控制器")

status_var = tk.StringVar()
status_var.set(f"CraftControl {APP_VERSION} 準備就緒")

log_box = None
status_labels = {}
paper_version_var = tk.StringVar()
paper_version_combo = None

# === 建立菜單 ===
menubar = tk.Menu(root)

server_menu = tk.Menu(menubar, tearoff=0)
server_menu.add_command(label="啟動所有伺服器", command=start_all)
server_menu.add_command(label="停止所有伺服器", command=stop_all)
menubar.add_cascade(label="伺服器", menu=server_menu)

download_menu = tk.Menu(menubar, tearoff=0)
download_menu.add_command(label="下載最新 Paper", command=download_latest_paper)
download_menu.add_command(label="下載最新 BungeeCord", command=download_latest_bungee)
download_menu.add_separator()
download_menu.add_command(label="前往 Paper 官網", command=lambda: webbrowser.open_new("https://papermc.io"))
download_menu.add_command(label="前往 BungeeCord 官網", command=lambda: webbrowser.open_new("https://www.spigotmc.org/threads/1-8-1-15-bungeecord.392/"))
menubar.add_cascade(label="下載", menu=download_menu)

config_menu = tk.Menu(menubar, tearoff=0)
config_menu.add_command(label="修改 Paper 數量", command=change_paper_count)
config_menu.add_command(label="一鍵修復缺失項目", command=auto_repair_missing)
menubar.add_cascade(label="設定", menu=config_menu)

help_menu = tk.Menu(menubar, tearoff=0)
help_menu.add_command(label="關於", command=show_about)
menubar.add_cascade(label="說明", menu=help_menu)

root.config(menu=menubar)

# === 主界面元件 ===
tk.Label(root, text="伺服器控制", font=("Arial", 14, "bold")).pack(pady=10)
for name in SERVER_PATHS:
    frame = tk.Frame(root)
    frame.pack(pady=2)
    tk.Label(frame, text=name, width=15).pack(side=tk.LEFT)
    tk.Button(frame, text="啟動", command=lambda n=name: on_start(n)).pack(side=tk.LEFT, padx=5)
    tk.Button(frame, text="停止", command=lambda n=name: on_stop(n)).pack(side=tk.LEFT)

status_frame = tk.Frame(root)
status_frame.pack(pady=10)
tk.Label(status_frame, text="伺服器狀態", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 5))
for i, name in enumerate(SERVER_PATHS):
    tk.Label(status_frame, text=name + "：").grid(row=i + 1, column=0, sticky="e")
    lbl = tk.Label(status_frame, text="未知", fg="gray")
    lbl.grid(row=i + 1, column=1, sticky="w")
    status_labels[name] = lbl

tk.Label(root, text="\n伺服器下載", font=("Arial", 14, "bold")).pack(pady=10)
frame_dl = tk.Frame(root)
frame_dl.pack()
tk.Label(frame_dl, text="Paper 版本：").pack(side=tk.LEFT)
paper_version_combo = ttk.Combobox(frame_dl, textvariable=paper_version_var, state="readonly")
paper_version_combo.pack(side=tk.LEFT)
paper_version_combo['values'] = ["載入中..."]
paper_version_combo.set("載入中...")

tk.Button(root, text="下載最新 Paper", command=download_latest_paper).pack(pady=3)
tk.Button(root, text="下載最新 BungeeCord", command=download_latest_bungee).pack(pady=3)

tk.Label(root, text="\n日誌", font=("Arial", 14, "bold")).pack()
log_box = tk.Text(root, height=12, width=60)
log_box.pack(pady=5)

status_bar = tk.Label(root, textvariable=status_var, bd=1, relief=tk.SUNKEN, anchor="w")
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

ensure_server_dirs()
check_server_files()

threading.Thread(target=load_paper_versions, daemon=True).start()
update_server_statuses()

root.mainloop()
