import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import os
import requests
import threading
import webbrowser
import subprocess
from gui import controller, config_manager
from controller import start_server, stop_server, is_server_running
from config_manager import get_paper_count, set_paper_count

APP_VERSION = "v1.0"
IS_WINDOWS = os.name == "nt"

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

# 將當前工作目錄切換到 CraftControl 根目錄
os.chdir(base_dir)

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
    base_dir = os.path.dirname(sys.executable)
    paths = {
        "BungeeCord": os.path.join(base_dir, "servers", "bungee", "start.bat") if IS_WINDOWS else os.path.join(base_dir, "servers", "bungee", "start.sh")
    }
    for i in range(1, paper_count + 1):
        name = f"Paper {i}"
        path = os.path.join(base_dir, "servers", f"paper{i}", "start.bat") if IS_WINDOWS else os.path.join(base_dir, "servers", f"paper{i}", "start.sh")
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
        # 判斷是 Paper 或 Bungee
        if "paper" in name.lower():
            jar_path = os.path.join(folder, "paper.jar")
            jar_exists = os.path.exists(jar_path)
            script_exists = os.path.exists(script_path)
            if not jar_exists:
                log(f"⚠️ {name} 缺少 paper.jar")
            if not script_exists:
                log(f"⚠️ {name} 缺少啟動腳本 ({script_path})")
        elif "bungee" in name.lower():
            jar_path = os.path.join(folder, "BungeeCord.jar")
            jar_exists = os.path.exists(jar_path)
            script_exists = os.path.exists(script_path)
            if not jar_exists:
                log(f"⚠️ {name} 缺少 BungeeCord.jar")
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

            # Paper API
            paper_api = f"https://api.papermc.io/v2/projects/paper/versions/{version}"
            builds = requests.get(paper_api).json()["builds"]
            latest = builds[-1]

            for name, script_path in SERVER_PATHS.items():
                folder = os.path.dirname(script_path)
                os.makedirs(folder, exist_ok=True)

                # 補啟動腳本
                if not os.path.exists(script_path):
                    if IS_WINDOWS:
                        with open(script_path, "w", encoding="utf-8") as f:
                            folder_abs = os.path.abspath(os.path.dirname(script_path))
                            if "paper" in name.lower():
                                f.write(f"""@echo off
cd /d "{folder_abs}"
java -Xmx2G -jar paper.jar nogui
pause
""")
                            else:  # Bungee
                                f.write(f"""@echo off
cd /d "{folder_abs}"
java -Xmx512M -jar BungeeCord.jar
pause
""")
                    else:
                        with open(script_path, "w", encoding="utf-8") as f:
                            if "paper" in name.lower():
                                f.write(f"""#!/bin/bash
java -Xmx2G -jar paper.jar nogui
read -p "Press Enter to exit..."
""")
                            else:
                                f.write(f"""#!/bin/bash
java -Xmx512M -jar BungeeCord.jar
read -p "Press Enter to exit..."
""")
                        os.chmod(script_path, 0o755)
                    log(f"✅ 已補上啟動腳本：{name}")

                # 補 jar 檔
                if "paper" in name.lower():
                    jar_path = os.path.join(folder, "paper.jar")
                    if not os.path.exists(jar_path):
                        jar_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest}/downloads/paper-{version}-{latest}.jar"
                        r = requests.get(jar_url)
                        r.raise_for_status()
                        with open(jar_path, "wb") as f:
                            f.write(r.content)
                        log(f"✅ 已補上 paper.jar：{name}")
                elif "bungee" in name.lower():
                    jar_path = os.path.join(folder, "BungeeCord.jar")
                    if not os.path.exists(jar_path):
                        url = "https://ci.md-5.net/job/BungeeCord/lastSuccessfulBuild/artifact/bootstrap/target/BungeeCord.jar"
                        r = requests.get(url)
                        r.raise_for_status()
                        with open(jar_path, "wb") as f:
                            f.write(r.content)
                        log(f"✅ 已補上 BungeeCord.jar：{name}")

            log("✅ 所有伺服器資料夾修復完成")
        except Exception as e:
            log(f"❌ 自動修復失敗：{e}")
        finally:
            root.after(0, loading_win.destroy)

    threading.Thread(target=repair_task, daemon=True).start()

# === 控制伺服器 ===
def on_start(server_name):
    success, msg = start_server(server_name, SERVER_PATHS[server_name])
    print(SERVER_PATHS[server_name])
    # log(msg)  # 移除這行，不輸出到 log_box
    # 新增自動開啟 eula.txt 檔案
    folder = os.path.dirname(SERVER_PATHS[server_name])
    eula_path = os.path.join(folder, "eula.txt")
    need_open_eula = False
    if os.path.exists(eula_path):
        try:
            with open(eula_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # 只檢查 eula= 這一行
            eula_value = None
            for line in lines:
                if line.strip().lower().startswith("eula="):
                    eula_value = line.strip().lower()
                    break
            need_open_eula = (eula_value != "eula=true")
        except Exception as e:
            log(f"讀取 eula.txt 失敗：{e}")
            need_open_eula = True
    else:
        need_open_eula = False

    if need_open_eula:
        try:
            if IS_WINDOWS:
                os.startfile(eula_path)
            else:
                subprocess.Popen(["xdg-open", eula_path])
            log(f"已自動開啟 {server_name} 的 eula.txt，請同意後再啟動。")
        except Exception as e:
            log(f"開啟 eula.txt 失敗：{e}")
            messagebox.showerror("錯誤", f"開啟 eula.txt 失敗：{e}")
    if not success:
        messagebox.showerror("錯誤", msg)

def on_stop(server_name):
    # 根據伺服器類型決定關閉指令
    if "paper" in server_name.lower():
        stop_cmd = "stop"
    elif "bungee" in server_name.lower():
        stop_cmd = "end"
    else:
        stop_cmd = "stop"  # 預設

    success, msg = stop_server(server_name, stop_cmd)
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
        running = is_server_running(name,port=25565)
        lbl = status_labels.get(name)
        if lbl:
            lbl.config(text="🟢 運行中" if running else "🔴 未啟動", foreground="green" if running else "red")
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
    messagebox.showinfo("關於 CraftControl", f"CraftControl {APP_VERSION}\nMade By Samchen023\nMinecraft Server 控制面板")

def write_start_script(path, max_ram_gb=2):
    max_ram = f"-Xmx{max_ram_gb}G"
    IS_WINDOWS = os.name == "nt"
    if IS_WINDOWS:
        content = f"""@echo off
java {max_ram} -jar paper.jar nogui
pause
"""
    else:
        content = f"""#!/bin/bash
java {max_ram} -jar paper.jar nogui
read -p "Press Enter to exit..."
"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    if not IS_WINDOWS:
        os.chmod(path, 0o755)

def set_server_ram(server_name):
    script_path = SERVER_PATHS[server_name]
    win = tk.Toplevel(root)
    win.title(f"{server_name} 記憶體設定")
    win.geometry("300x120")
    tk.Label(win, text="請輸入最大記憶體 (GB)：").pack(pady=5)
    ram_entry = tk.Entry(win)
    ram_entry.pack(pady=5)
    ram_entry.insert(0, "2")
    def on_apply():
        ram_str = ram_entry.get()
        try:
            ram_gb = int(ram_str)
            if ram_gb < 1 or ram_gb > 64:
                raise ValueError
        except ValueError:
            messagebox.showerror("錯誤", "請輸入 1~64 之間的整數")
            return
        write_start_script(script_path, ram_gb)
        messagebox.showinfo("成功", f"已設定最大記憶體為 {ram_gb} GB，並更新啟動腳本")
        win.destroy()
    tk.Button(win, text="套用", command=on_apply).pack(pady=10)

def open_server_folder(server_name):
    folder = os.path.dirname(SERVER_PATHS[server_name])
    abs_folder = os.path.abspath(folder)  # 取得絕對路徑
    try:
        os.makedirs(abs_folder, exist_ok=True)  # 確保資料夾存在
        if IS_WINDOWS:
            os.startfile(abs_folder)
        else:
            subprocess.Popen(["xdg-open", abs_folder])
        log(f"已開啟 {server_name} 資料夾")
    except Exception as e:
        log(f"開啟資料夾失敗：{e}")
        messagebox.showerror("錯誤", f"開啟資料夾失敗：{e}")

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

# 新增「開啟伺服器資料夾」子選單
open_folder_menu = tk.Menu(server_menu, tearoff=0)
for name in SERVER_PATHS:
    open_folder_menu.add_command(label=name, command=lambda n=name: open_server_folder(n))
server_menu.add_cascade(label="開啟伺服器資料夾", menu=open_folder_menu)

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
help_menu.add_command(label="官網", command=lambda: webbrowser.open_new("https://github.com/samchen023/CraftControl"))
help_menu.add_command(label="關於", command=show_about)
menubar.add_cascade(label="說明", menu=help_menu)

root.config(menu=menubar)

# === 主界面元件 ===
ttk.Label(root, text="伺服器控制", font=("Arial", 14, "bold")).pack(pady=10)
for name in SERVER_PATHS:
    frame = ttk.Frame(root)
    frame.pack(pady=2)
    ttk.Label(frame, text=name, width=15).pack(side=tk.LEFT)
    ttk.Button(frame, text="啟動", command=lambda n=name: on_start(n)).pack(side=tk.LEFT, padx=5)
    ttk.Button(frame, text="停止", command=lambda n=name: on_stop(n)).pack(side=tk.LEFT)
    # 新增記憶體設定按鈕（僅 Paper 伺服器）
    if "paper" in name.lower():
        ttk.Button(frame, text="記憶體設定", command=lambda n=name: set_server_ram(n)).pack(side=tk.LEFT, padx=5)

status_frame = ttk.Frame(root)
status_frame.pack(pady=10)
ttk.Label(status_frame, text="伺服器狀態", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 5))
for i, name in enumerate(SERVER_PATHS):
    ttk.Label(status_frame, text=name + "：").grid(row=i + 1, column=0, sticky="e")
    lbl = ttk.Label(status_frame, text="未知", foreground="gray")
    lbl.grid(row=i + 1, column=1, sticky="w")
    status_labels[name] = lbl

ttk.Label(root, text="\n伺服器下載", font=("Arial", 14, "bold")).pack(pady=10)
frame_dl = ttk.Frame(root)
frame_dl.pack()
ttk.Label(frame_dl, text="Paper 版本：").pack(side=tk.LEFT)
paper_version_combo = ttk.Combobox(frame_dl, textvariable=paper_version_var, state="readonly")
paper_version_combo.pack(side=tk.LEFT)
paper_version_combo['values'] = ["載入中..."]
paper_version_combo.set("載入中...")

ttk.Button(root, text="下載最新 Paper", command=download_latest_paper).pack(pady=3)
ttk.Button(root, text="下載最新 BungeeCord", command=download_latest_bungee).pack(pady=3)

ttk.Label(root, text="\n日誌", font=("Arial", 14, "bold")).pack()
log_box = tk.Text(root, height=12, width=60)
log_box.pack(pady=5)

status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor="w")
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

ensure_server_dirs()
check_server_files()

threading.Thread(target=load_paper_versions, daemon=True).start()
update_server_statuses()

root.mainloop()
