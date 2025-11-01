# UIstarter.py
import tkinter as tk
import sys
import os
import subprocess
import threading
import time

def input(title=None):
    """自定义输入函数"""
    stau = [0]
    result = [""]
    
    def get_input():
        win = tk.Tk(className=f'{title}')
        win.attributes('-topmost', 1)
        w = int(win.winfo_screenwidth() / 2 - 180)
        h = int(win.winfo_screenheight() / 2 - 120)
        win.geometry(f'360x240+{w}+{h}')
        
        s = tk.Entry(win, font=('Terminal', 15), width=24)
        s.pack(padx=2, pady=20)
        s.focus_set()  # 自动聚焦到输入框
        
        def on_confirm():
            result[0] = s.get()
            stau[0] = 1
            win.destroy()
        
        tk.Button(win, text='确定', relief='solid', command=on_confirm,
                  font=('等线', 15)).pack()
        
        # 绑定回车键
        win.bind('<Return>', lambda e: on_confirm())
        
        while not stau[0]:
            try:
                win.update()
                time.sleep(0.01)
            except:
                break
    
    # 在子线程中运行GUI，避免阻塞
    if threading.current_thread() is threading.main_thread():
        get_input()
    else:
        # 如果在子线程中，需要在主线程运行GUI
        import queue
        q = queue.Queue()
        
        def run_in_main():
            get_input()
            q.put(result[0])
        
        win.after(0, run_in_main)
        result[0] = q.get()
    
    return result[0]

def run_python_file(file_path):
    """使用子进程运行Python文件"""
    try:
        # 设置当前工作目录到文件所在目录
        file_dir = os.path.dirname(os.path.abspath(file_path))
        os.chdir(file_dir)
        
        # 使用子进程运行，这样可以处理所有复杂情况
        process = subprocess.Popen(
            [sys.executable, file_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 处理输入输出
        def handle_io():
            while True:
                # 读取输出
                output = process.stdout.readline()
                if output:
                    print(output, end='')
                
                # 读取错误
                error = process.stderr.readline()
                if error:
                    print(error, end='', file=sys.stderr)
                
                # 检查进程是否结束
                if process.poll() is not None:
                    # 读取剩余输出
                    remaining_output, remaining_error = process.communicate()
                    if remaining_output:
                        print(remaining_output, end='')
                    if remaining_error:
                        print(remaining_error, end='', file=sys.stderr)
                    break
        
        # 在子线程中处理IO
        io_thread = threading.Thread(target=handle_io, daemon=True)
        io_thread.start()
        
        # 等待进程结束
        process.wait()
        
    except Exception as e:
        print(f"运行错误: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_to_run = sys.argv[-1]
        
        if os.path.exists(file_to_run):
            print(f"正在运行: {file_to_run}")
            print("-" * 50)
            
            # 使用子进程运行文件
            run_python_file(file_to_run)
            
            print("-" * 50)
            print("程序运行结束......")
        else:
            print(f"文件不存在: {file_to_run}")