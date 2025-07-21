import subprocess
import os
import platform

IS_WINDOWS = platform.system() == "Windows"

# 紀錄正在執行的伺服器程序
server_processes = {}

def start_server(server_name, script_path):
    if server_name in server_processes:
        return False, f"{server_name} 已在運行中"
    if not os.path.exists(script_path):
        return False, f"啟動腳本不存在：{script_path}"
    try:
        script_dir = os.path.dirname(os.path.abspath(script_path))
        if IS_WINDOWS and script_path.endswith('.bat'):
            proc = subprocess.Popen(
                ['cmd.exe', '/c', script_path],
                cwd=script_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            proc = subprocess.Popen(script_path, shell=True, cwd=script_dir)
        server_processes[server_name] = proc
        return True, f"已啟動伺服器：{server_name}"
    except Exception as e:
        return False, f"啟動錯誤：{e}"

def stop_server(server_name):
    proc = server_processes.get(server_name)
    if not proc:
        return False, f"{server_name} 未啟動"
    try:
        proc.terminate()
        proc.wait(timeout=5)
        del server_processes[server_name]
        return True, f"已停止伺服器：{server_name}"
    except Exception as e:
        return False, f"停止錯誤：{e}"

def is_server_running(server_name):
    proc = server_processes.get(server_name)
    return proc is not None and proc.poll() is None
