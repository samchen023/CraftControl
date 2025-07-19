import tkinter as tk
from tkinter import messagebox
import os
import requests
import webbrowser
from tkinter import ttk
import threading
from controller import start_server, stop_server, is_server_running  

APP_VERSION = "v1.0"

IS_WINDOWS = os.name == "nt"

SERVER_PATHS = {
    "BungeeCord": "servers/bungee/start.bat" if IS_WINDOWS else "servers/bungee/start.sh",
    "Paper 1": "servers/paper1/start.bat" if IS_WINDOWS else "servers/paper1/start.sh",
    "Paper 2": "servers/paper2/start.bat" if IS_WINDOWS else "servers/paper2/start.sh",
}

# === log & 狀態列更新 ===
def log(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)

# === 伺服器控制 ===
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
        lbl = status_labels[name]
        if running:
            lbl.config(text="🟢 運行中", fg="green")
        else:
            lbl.config(text="🔴 未啟動", fg="red")
    root.after(3000, update_server_statuses)

# === 下載功能 ===
def load_paper_versions():
    try:
        log("正在載入 Paper 版本清單...")
        r = requests.get("https://api.papermc.io/v2/projects/paper", timeout=10)
        r.raise_for_status()
        data = r.json()
        versions = data.get("versions", [])
        if versions:
            versions.reverse()  # 最新版本排最上面
            paper_version_combo['values'] = versions
            paper_version_combo.set(versions[0])
            log("Paper 版本載入完成")
        else:
            paper_version_combo['values'] = ["無法載入"]
            paper_version_combo.set("無法載入")
            log("找不到版本資料")
    except Exception as e:
        paper_version_combo['values'] = ["錯誤"]
        paper_version_combo.set("錯誤")
        log(f"載入版本失敗：{e}")

def download_latest_paper():
    version = paper_version_var.get().strip()
    if not version:
        messagebox.showerror("錯誤", "請輸入 Paper 版本號")
        return
    dest_folder = "servers/paper1"
    os.makedirs(dest_folder, exist_ok=True)
    try:
        api = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
        builds = requests.get(api).json()["builds"]
        latest = builds[-1]
        jar_path = os.path.join(dest_folder, "paper.jar")

        if os.path.exists(jar_path):
            log(f"Paper {version} Build {latest} 已存在，跳過下載")
            return

        jar_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest}/downloads/paper-{version}-{latest}.jar"
        r = requests.get(jar_url)
        r.raise_for_status()
        with open(jar_path, "wb") as f:
            f.write(r.content)
        log(f"下載完成 Paper {version} Build {latest}")
    except Exception as e:
        messagebox.showerror("下載失敗", str(e))
        log(f"下載失敗：{e}")

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
        messagebox.showerror("下載失敗", str(e))
        log(f"BungeeCord 下載失敗：{e}")

def show_about():
    messagebox.showinfo("關於 CraftControl", f"CraftControl {APP_VERSION}\nMinecraft Server 控制面板\nBy 你自己！")

# === GUI 開始 ===

root = tk.Tk()
root.title(f"CraftControl {APP_VERSION} - Minecraft Server 控制器")

# === 功能選單 ===
menubar = tk.Menu(root)

server_menu = tk.Menu(menubar, tearoff=0)
server_menu.add_command(label="啟動所有伺服器", command=start_all)
server_menu.add_command(label="停止所有伺服器", command=stop_all)
menubar.add_cascade(label="伺服器", menu=server_menu)

download_menu = tk.Menu(menubar, tearoff=0)
download_menu.add_command(label="重新載入版本", command=load_paper_versions)
download_menu.add_command(label="前往 Paper 官網", command=lambda:webbrowser.open_new("https://papermc.io"))
download_menu.add_command(label="前往 BungeeCord 官網", command=lambda:webbrowser.open_new("https://www.spigotmc.org/threads/1-8-1-15-bungeecord.392/"))
menubar.add_cascade(label="連結", menu=download_menu)

help_menu = tk.Menu(menubar, tearoff=0)
help_menu.add_command(label="關於", command=show_about)
menubar.add_cascade(label="說明", menu=help_menu)

root.config(menu=menubar)

# === GUI 主體 ===
tk.Label(root, text="伺服器控制", font=("Arial", 14, "bold")).pack(pady=10)
for name in SERVER_PATHS:
    frame = tk.Frame(root)
    frame.pack(pady=2)
    tk.Label(frame, text=name, width=15).pack(side=tk.LEFT)
    tk.Button(frame, text="啟動", command=lambda n=name: on_start(n)).pack(side=tk.LEFT, padx=5)
    tk.Button(frame, text="停止", command=lambda n=name: on_stop(n)).pack(side=tk.LEFT)

status_frame = tk.Frame(root)
status_frame.pack(pady=10)

status_labels = {}

tk.Label(status_frame, text="伺服器狀態", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 5))

for i, name in enumerate(SERVER_PATHS):
    tk.Label(status_frame, text=name + "：").grid(row=i+1, column=0, sticky="e", padx=5)
    lbl = tk.Label(status_frame, text="未知", fg="gray")
    lbl.grid(row=i+1, column=1, sticky="w", padx=5)
    status_labels[name] = lbl

tk.Label(root, text="\n伺服器下載", font=("Arial", 14, "bold")).pack(pady=10)
frame_dl = tk.Frame(root)
frame_dl.pack()

tk.Label(frame_dl, text="Paper 版本：").pack(side=tk.LEFT)
paper_version_var = tk.StringVar()
paper_version_combo = ttk.Combobox(frame_dl, textvariable=paper_version_var, state="readonly")
paper_version_combo.pack(side=tk.LEFT)
paper_version_combo['values'] = ["載入中..."]
paper_version_combo.set("載入中...")

tk.Button(root, text="下載最新 Paper", command=download_latest_paper).pack(pady=3)
tk.Button(root, text="下載最新 BungeeCord", command=download_latest_bungee).pack(pady=3)

tk.Label(root, text="\n日誌", font=("Arial", 14, "bold")).pack()
log_box = tk.Text(root, height=12, width=60)
log_box.pack(pady=5)

threading.Thread(target=load_paper_versions, daemon=True).start()
update_server_statuses()
root.mainloop()
