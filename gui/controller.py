import subprocess
import os
import platform
import socket

IS_WINDOWS = platform.system() == "Windows"

# 紀錄正在執行的伺服器程序
server_processes = {}

def start_server(server_name, script_path):
    try:
        proc = subprocess.Popen(
            script_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True,
            cwd=os.path.dirname(script_path),
            encoding="utf-8"
        )
        output, _ = proc.communicate(timeout=10)
        # output 會包含所有 console log
        if "Failed to load eula.txt" in output:
            return False, output
        return True, output
    except Exception as e:
        return False, str(e)

def stop_server(server_name, stop_cmd="stop"):
    proc = server_processes.get(server_name)
    if not proc:
        return False, f"{server_name} 未啟動"
    try:
        # 傳送指令到伺服器標準輸入
        if proc.poll() is None and proc.stdin:
            try:
                proc.stdin.write((stop_cmd + "\n").encode())
                proc.stdin.flush()
                # 多送幾次 Enter，確保 pause 被觸發
                for _ in range(3):
                    proc.stdin.write(b"\n")
                    proc.stdin.flush()
            except Exception as e:
                proc.terminate()
        else:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=5)
        del server_processes[server_name]
        return True, f"已停止伺服器：{server_name}"
    except Exception as e:
        return False, f"停止錯誤：{e}"

def is_port_open(port):
    """檢查指定 port 是否有程式在監聽"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        return result == 0

def is_server_running(server_name, port=None):
    proc = server_processes.get(server_name)
    running = proc is not None and proc.poll() is None
    if port is not None:
        # 若指定 port，則以 port 狀態為主
        return running and is_port_open(port)
    return running
