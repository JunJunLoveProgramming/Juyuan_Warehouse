try:
    from fix_encoding import fix_all_encoding
    fix_all_encoding()
except ImportError:
    # 如果fix_encoding.py不存在，使用内置修复
    pass

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import os
import subprocess
import sys
import threading
import queue
from PIL import Image, ImageTk
import time
import ctypes
import pyperclip

# === 单实例检查开始 ===
import socket
try:
    # 尝试绑定一个端口，如果端口已被占用，说明程序已在运行
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lock_socket.bind(('localhost', 47291))  # 使用一个特定端口
    print("程序启动成功 - 单实例")
except socket.error:
    print("程序已在运行中，即将退出")
    sys.exit(1)
# === 单实例检查结束 ===

if sys.platform == 'win32':
    ctypes.windll.shcore.SetProcessDpiAwareness(1)

def feedback(rt):
    s = tk.Toplevel(rt)
    s.geometry('400x400')
    s.transient(rt)
    tk.Label(s, text='将反馈发送至邮箱:\njunjunaibiancheng@qq.com',
             font=('等线', 20)).pack()
    tk.Button(s, text='复制邮件', command=lambda: pyperclip.copy('junjunaibiancheng@qq.com')).pack(pady=2)

class CodeEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("聚源仓-Version1.0.1")
        self.root.geometry("1440x900")
        if os.path.exists("./Resources/app.ico"):
            self.root.iconbitmap("./Resources/app.ico")
        
        # 比例系数，用于等比例缩放
        self.scale_ratio = 1.0
        
        self.toolbar_items = [
            ("新建", './Resources/new.png', self.new_file),
            ("打开", './Resources/open.png', self.open_file),
            ("保存", './Resources/save.png', self.save_file),
            ("运行", './Resources/run.png', self.run_code),
            ("停止", './Resources/stop.png', self.stop_code), 
            ("AI分析", './Resources/ai.png', self.analyze_syntax),
            ("解释代码", './Resources/ai.png', self.explain_code),
            ("优化代码", './Resources/ai.png', self.optimize_code),
            ("打开系统终端", './Resources/run.png', self.open_system_terminal),  # 新增
            ("关于", './Resources/info.png', self.show_about),
        ]
        
        # 当前打开的文件路径
        self.current_file = None
        self.console_process = None
        self.console_queue = queue.Queue(65535)
        self.error_queue = queue.Queue()
        self.console_input = ""
        self.running = [False]
        
        # 终端相关属性
        self.terminal_process = None
        self.terminal_queue = queue.Queue()
        self.terminal_error_queue = queue.Queue()
        self.terminal_running = False
        self.terminal_mode = False  # 标记是否在终端模式
        
        self.setup_ui()
        self.setup_console()
        
        self.root.bind("<Configure>", self.on_resize)
        
        # 设置控制台文本标签样式
        styles = [
            ['Error', {'foreground': 'red', 'background': 'white'}],
            ['Dark', {'foreground': 'yellow', 'background': 'black'}],
            ['Input', {'foreground': 'green', 'background': 'white'}],
            ['Terminal', {'foreground': 'cyan', 'background': 'black'}]
        ]
        for k, w in styles:
            self.console_text.tag_configure(k, **w)
        
        # 启动终端模式
        self.start_terminal_mode()
        
        # 使用after方法定期处理控制台输出，避免阻塞主线程
        self.root.after(100, self.process_console_io)

    def setup_ui(self):
        # 顶部工具栏
        self.toolbar = ttk.Frame(self.root)
        self.toolbar.pack(fill=tk.X, side=tk.TOP)
        
        # 批量注册工具栏项目
        self.image = []

        if os.path.exists('./Resources/app.jpg'):
            self.image.append(ImageTk.PhotoImage(Image.open('./Resources/app.jpg').resize((80, 80))))
            tk.Label(self.toolbar, image=self.image[0]).pack(side='left')
            
        for name, icon, command in self.toolbar_items:
            if icon is not None and os.path.exists(icon):
                ico = Image.open(icon).resize((40, 40))
                self.image.append(ImageTk.PhotoImage(ico))
                tk.Button(self.toolbar, text=name, command=command, font=('等线', 12, 'bold'),
                          relief='flat', image=self.image[-1], compound='top').pack(side=tk.LEFT, padx=2, pady=2)
            else:
                tk.Button(self.toolbar, text=name, command=command, font=('等线', 12, 'bold'),
                          relief='flat').pack(side=tk.LEFT, padx=2, pady=2)
            
        # 主容器（包含左侧树和右侧编辑区域）
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # 左侧文件树
        self.ast_frame = ttk.Frame(self.main_container, width=250)
        self.ast_frame.pack(fill=tk.Y, side=tk.LEFT)
        
        ttk.Label(self.ast_frame, text="文件目录树").pack(fill=tk.X, padx=5, pady=5)
        
        # 添加刷新按钮
        toolbar_frame = ttk.Frame(self.ast_frame)
        toolbar_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(toolbar_frame, text="刷新", command=self.refresh_tree).pack(side=tk.LEFT)
        ttk.Button(toolbar_frame, text="打开文件夹", command=self.open_folder).pack(side=tk.LEFT)
        
        self.tree = ttk.Treeview(self.ast_frame)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree.heading("#0", text="项目文件", anchor=tk.W)
        
        # 绑定双击事件
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        # 初始时扫描当前目录
        self.project_root = os.getcwd()
        self.populate_tree(self.project_root)
        
        # 右侧代码编辑区域
        self.edit_frame = ttk.Frame(self.main_container)
        self.edit_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        self.code_text = scrolledtext.ScrolledText(self.edit_frame, wrap=tk.WORD, font=("Consolas", 12))
        self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 底部控制台
        self.console_frame = ttk.Frame(self.root, height=200)
        self.console_frame.pack(fill=tk.BOTH, side=tk.BOTTOM)
        
        console_header = ttk.Frame(self.console_frame)
        console_header.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(console_header, text="Python终端", font=('Consolas', 13)).pack(side=tk.LEFT)
        
        # 添加终端控制按钮
        terminal_buttons = ttk.Frame(console_header)
        terminal_buttons.pack(side=tk.RIGHT)
        ttk.Button(terminal_buttons, text='清空终端', command=self.clear_terminal).pack(side=tk.LEFT, padx=2)
        ttk.Button(terminal_buttons, text='重启终端', command=self.restart_terminal).pack(side=tk.LEFT, padx=2)
        ttk.Button(terminal_buttons, text='切换模式', command=self.toggle_mode).pack(side=tk.LEFT, padx=2)
        
        self.console_text = scrolledtext.ScrolledText(self.console_frame, wrap=tk.WORD, font=("Consolas", 12))
        self.console_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 绑定键盘事件
        self.console_text.bind("<KeyPress>", self.on_console_key_press)
        self.console_text.bind("<Return>", self.on_console_return)
        self.console_text.bind("<BackSpace>", self.on_console_backspace)
        
        # 添加控制台输入提示
        self.console_text.insert(tk.END, "Python 3 Terminal >>> ", 'Terminal')
        self.console_text.mark_set("input_start", "end-1c")
        self.console_text.mark_gravity("input_start", "left")
        self.console_text.see(tk.END)

    def setup_console(self):
        """初始化控制台设置"""
        pass

    def start_terminal_mode(self):
        """启动Python终端模式 - 简化版本"""
        try:
            # 停止之前的终端进程
            if self.terminal_process and self.terminal_process.poll() is None:
                self.terminal_process.terminate()
            
            # 设置启动参数
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # 启动Python交互式终端 - 使用文本模式
            self.terminal_process = subprocess.Popen(
                [sys.executable, "-i", "-u"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # 使用文本模式
                bufsize=1,  # 行缓冲
                encoding='utf-8',  # 明确指定编码
                errors='replace',  # 替换无法解码的字符
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            
            self.terminal_running = True
            self.terminal_mode = True
            
            # 启动线程读取终端输出
            threading.Thread(target=self.read_terminal_output_simple, daemon=True).start()
            
            # 在控制台显示提示
            self.console_text.insert(tk.END, "\nPython交互式终端已启动\n", 'Terminal')
            self.console_text.see(tk.END)
            
        except Exception as e:
            self.console_text.insert(tk.END, f"\n启动终端失败: {str(e)}\n", 'Error')
            self.console_text.see(tk.END)

    def read_terminal_output_simple(self):
        """读取终端输出 - 简单可靠的方法"""
        while self.terminal_running:
            try:
                # 检查进程是否结束
                if self.terminal_process.poll() is not None:
                    self.terminal_running = False
                    break
                
                # 读取标准输出 - 使用文本模式
                output = self.terminal_process.stdout.readline()
                if output:
                    self.terminal_queue.put(output)
                
                # 读取错误输出
                error = self.terminal_process.stderr.readline()
                if error:
                    self.terminal_error_queue.put(error)
                        
            except Exception as e:
                # 忽略常见的IO错误，这些通常发生在进程结束时
                if "I/O operation on closed file" not in str(e):
                    print(f"读取终端输出错误: {e}")
                break

    def on_console_key_press(self, event):
        """处理控制台键盘输入"""
        # 如果光标在输入区域之前，移动到输入区域
        if self.console_text.compare(tk.INSERT, "<", "input_start"):
            self.console_text.mark_set(tk.INSERT, "end-1c")
            return "break"
        
        # 允许正常输入
        return None

    def on_console_backspace(self, event):
        """处理控制台退格键"""
        # 如果光标在输入区域开始位置，阻止退格
        if self.console_text.compare(tk.INSERT, "==", "input_start"):
            return "break"
        return None

    def on_console_return(self, event):
        """处理控制台回车键 - 简化版本"""
        # 获取输入内容
        input_line = self.console_text.get("input_start", "end-1c")
        
        # 如果是空行，只添加新提示符
        if not input_line.strip():
            prompt = ">>> " if self.terminal_mode else ">>> "
            self.console_text.insert(tk.END, f"\n{prompt}", 'Terminal' if self.terminal_mode else 'Dark')
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            return "break"
        
        # 确保以换行符结束
        if not input_line.endswith('\n'):
            input_line += '\n'
        
        # 根据当前模式处理输入
        if self.terminal_mode and self.terminal_running:
            # 终端模式：发送到Python交互式终端
            try:
                self.terminal_process.stdin.write(input_line)
                self.terminal_process.stdin.flush()
                
                # 添加新行和提示符
                prompt = "... " if input_line.rstrip().endswith(":") else ">>> "
                self.console_text.insert(tk.END, f"\n{prompt}", 'Terminal')
                self.console_text.mark_set("input_start", "end-1c")
                self.console_text.mark_gravity("input_start", "left")
                self.console_text.see(tk.END)
                
            except Exception as e:
                self.console_text.insert(tk.END, f"\n终端输入错误: {str(e)}\n>>> ", 'Error')
                self.console_text.mark_set("input_start", "end-1c")
                self.console_text.mark_gravity("input_start", "left")
                self.console_text.see(tk.END)
                
        elif self.console_process and self.console_process.poll() is None:
            # 运行模式：发送到正在运行的程序
            try:
                self.console_process.stdin.write(input_line)
                self.console_process.stdin.flush()
                
                # 添加新行和提示符
                self.console_text.insert(tk.END, "\n>>> ")
                self.console_text.mark_set("input_start", "end-1c")
                self.console_text.mark_gravity("input_start", "left")
                self.console_text.see(tk.END)
                
            except Exception as e:
                self.console_text.insert(tk.END, f"\n输入错误: {str(e)}\n>>> ", 'Error')
                self.console_text.mark_set("input_start", "end-1c")
                self.console_text.mark_gravity("input_start", "left")
                self.console_text.see(tk.END)
        else:
            # 无模式：直接在控制台中执行Python代码
            try:
                # 尝试执行单行代码
                result = eval(input_line)
                self.console_text.insert(tk.END, f"\n{result}\n>>> ")
            except:
                try:
                    # 尝试执行多行代码
                    exec(input_line)
                    self.console_text.insert(tk.END, "\n>>> ")
                except Exception as e:
                    self.console_text.insert(tk.END, f"\n错误: {str(e)}\n>>> ", 'Error')
            
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
        
        return "break"
        
    def process_console_io(self):
        """处理控制台输入输出的定期检查"""
        try:
            # 处理终端输出
            while True:
                try:
                    output = self.terminal_queue.get_nowait()
                    # 在输出前确保光标位置正确
                    self.console_text.insert(tk.END, output, 'Terminal')
                    
                    # 更新输入起始位置
                    self.console_text.mark_set("input_start", "end-1c")
                    self.console_text.mark_gravity("input_start", "left")
                    
                    self.console_text.see(tk.END)
                except queue.Empty:
                    break
            
            # 处理终端错误输出
            while True:
                try:
                    error = self.terminal_error_queue.get_nowait()
                    self.console_text.insert(tk.END, error, 'Error')
                    
                    # 更新输入起始位置
                    self.console_text.mark_set("input_start", "end-1c")
                    self.console_text.mark_gravity("input_start", "left")
                    
                    self.console_text.see(tk.END)
                except queue.Empty:
                    break
            
            # 处理程序输出
            while True:
                try:
                    output = self.console_queue.get_nowait()
                    self.console_text.insert(tk.END, output, 'Dark')
                    
                    # 更新输入起始位置
                    self.console_text.mark_set("input_start", "end-1c")
                    self.console_text.mark_gravity("input_start", "left")
                    
                    self.console_text.see(tk.END)
                except queue.Empty:
                    break
            
            # 处理程序错误输出
            while True:
                try:
                    error = self.error_queue.get_nowait()
                    self.console_text.insert(tk.END, error, 'Error')
                    
                    # 更新输入起始位置
                    self.console_text.mark_set("input_start", "end-1c")
                    self.console_text.mark_gravity("input_start", "left")
                    
                    self.console_text.see(tk.END)
                except queue.Empty:
                    break
                    
        except Exception as e:
            print(f"处理控制台IO错误: {e}")
        
        # 继续定期检查
        self.root.after(50, self.process_console_io)

    def clear_terminal(self):
        """清空终端"""
        self.console_text.delete(1.0, tk.END)
        if self.terminal_mode:
            self.console_text.insert(tk.END, "Python 3 Terminal >>> ", 'Terminal')
        else:
            self.console_text.insert(tk.END, ">>> ")
        self.console_text.mark_set("input_start", "end-1c")
        self.console_text.mark_gravity("input_start", "left")
        self.console_text.see(tk.END)

    def restart_terminal(self):
        """重启终端"""
        self.console_text.insert(tk.END, "\n重启Python终端...\n", 'Terminal')
        self.console_text.see(tk.END)
        self.start_terminal_mode()

    def toggle_mode(self):
        """切换终端/运行模式"""
        if self.terminal_mode:
            # 切换到运行模式
            self.terminal_mode = False
            self.console_text.insert(tk.END, "\n切换到运行模式\n>>> ")
            self.console_text.see(tk.END)
        else:
            # 切换到终端模式
            self.terminal_mode = True
            self.console_text.insert(tk.END, "\n切换到Python终端模式\n>>> ", 'Terminal')
            self.console_text.see(tk.END)
        
        self.console_text.mark_set("input_start", "end-1c")
        self.console_text.mark_gravity("input_start", "left")

    def populate_tree(self, path, parent="", deepth=0, max_depth=3):
        """填充文件树，支持多级目录"""
        try:
            # 如果超过最大深度，停止递归
            if deepth >= max_depth:
                return
                
            items = os.listdir(path)
            
            # 先添加文件夹，再添加文件
            folders = []
            files = []
            
            for item in items:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                else:
                    files.append(item)
            
            # 按字母顺序排序
            folders.sort()
            files.sort()
            
            # 添加文件夹
            for folder in folders:
                if folder.startswith('.'):  # 跳过隐藏文件夹
                    continue
                    
                folder_path = os.path.join(path, folder)
                node = self.tree.insert(parent, tk.END, text=folder, values=[folder_path, 'folder'])
                self.tree.insert(node, tk.END, text="加载中...")  # 占位符
                
            # 添加文件
            for file in files:
                if file.endswith('.py') or file.endswith('.txt') or file.endswith('.md'):
                    file_path = os.path.join(path, file)
                    self.tree.insert(parent, tk.END, text=file, values=[file_path, 'file'])
                    
        except PermissionError:
            # 跳过没有权限的文件夹
            pass
        except Exception as e:
            print(f"加载目录错误: {e}")

    def on_tree_double_click(self, event):
        """处理树节点的双击事件"""
        item = self.tree.selection()[0]
        item_values = self.tree.item(item, 'values')
        
        if item_values:
            item_path = item_values[0]
            item_type = item_values[1] if len(item_values) > 1 else 'file'
            
            if item_type == 'folder':
                # 如果是文件夹，展开或折叠
                if self.tree.get_children(item):
                    # 如果已经有子节点，切换展开状态
                    if self.tree.item(item, 'open'):
                        self.tree.item(item, open=False)
                    else:
                        self.tree.item(item, open=True)
                else:
                    # 加载子目录
                    self.load_subdirectory(item, item_path)
            elif item_type == 'file':
                # 如果是文件，打开它
                self.open_file_from_tree(item_path)

    def load_subdirectory(self, parent_node, path):
        """加载子目录"""
        # 删除"加载中..."占位符
        children = self.tree.get_children(parent_node)
        for child in children:
            self.tree.delete(child)
        
        # 加载实际内容
        self.populate_tree(path, parent_node, deepth=1)

    def open_file_from_tree(self, file_path):
        """从文件树打开文件"""
        try:
            if file_path.endswith('.py'):
                self.current_file = file_path
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.code_text.delete(1.0, tk.END)
                self.code_text.insert(1.0, content)
                
                # 在控制台显示提示
                self.console_text.insert(tk.END, f"\n已打开文件: {file_path}\n>>> ")
                self.console_text.mark_set("input_start", "end-1c")
                self.console_text.mark_gravity("input_start", "left")
                self.console_text.see(tk.END)
            else:
                # 对于非Python文件，尝试用系统默认程序打开
                import subprocess
                if os.name == 'nt':  # Windows
                    os.startfile(file_path)
                elif os.name == 'posix':  # Linux/Mac
                    subprocess.call(('open' if sys.platform == 'darwin' else 'xdg-open', file_path))
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def refresh_tree(self):
        """刷新文件树"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.populate_tree(self.project_root)

    def open_folder(self):
        """打开文件夹"""
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.project_root = folder_path
            self.refresh_tree()

    def read_console_output_simple(self):
        """读取控制台输出 - 简单可靠的方法"""
        print('SubThread is opening (simple mode)')
        
        while self.running[0]:
            try:
                # 检查进程是否结束
                if self.console_process.poll() is not None:
                    self.running[0] = False
                    break
                
                # 读取标准输出 - 使用文本模式
                output = self.console_process.stdout.readline()
                if output:
                    self.console_queue.put(output)
                
                # 读取错误输出
                error = self.console_process.stderr.readline()
                if error:
                    self.error_queue.put(error)
                        
            except Exception as e:
                # 忽略常见的IO错误，这些通常发生在进程结束时
                if "I/O operation on closed file" not in str(e):
                    print(f"读取输出错误: {e}")
                break
        
        print('SubThread exit (simple mode)')

    def update_layout(self):
        # 根据比例系数调整各部分大小
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 左侧树宽度占总宽度的20%
        tree_width = int(window_width * 0.2)
        self.ast_frame.config(width=tree_width)
        
        # 控制台高度占总高度的20%
        console_height = int(window_height * 0.35)
        self.console_frame.config(height=console_height)

    def on_resize(self, event):
        # 计算新的比例系数
        base_width = 1200
        base_height = 800
        new_width = event.width
        new_height = event.height
        
        # 使用最小的比例来保持等比例
        self.scale_ratio = min(new_width / base_width, new_height / base_height)
        self.update_layout()

    # 工具栏函数
    def new_file(self):
        self.current_file = None
        self.code_text.delete(1.0, tk.END)

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if file_path:
            self.current_file = file_path
            with open(file_path, "r", encoding="utf-8") as f:
                self.code_text.delete(1.0, tk.END)
                self.code_text.insert(1.0, f.read())

    def save_file(self):
        if self.current_file:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.code_text.get(1.0, tk.END))
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if file_path:
            self.current_file = file_path
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.code_text.get(1.0, tk.END))

    def run_code(self):
        if self.current_file:
            self.save_file()
            self.console_text.delete(1.0, tk.END)  # 清空控制台
            self.console_text.insert(tk.END, f'正在运行: {self.current_file}\n>>> ')
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            
            self.running[0] = True
            
            # 停止之前的进程
            if self.console_process is not None:
                if self.console_process.poll() is None:
                    self.console_process.kill()
            
            # 设置启动参数
            startupinfo = None
            creationflags = 0
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE
                creationflags = subprocess.CREATE_NO_WINDOW
            
            # 使用系统的python命令
            python_executable = "python"
            
            try:
                # 使用文本模式，简化编码设置
                self.console_process = subprocess.Popen(
                    [python_executable, "-u", self.current_file],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,  # 使用文本模式
                    bufsize=1,  # 行缓冲
                    encoding='utf-8',  # 明确指定编码
                    errors='replace',  # 替换无法解码的字符
                    startupinfo=startupinfo,
                    creationflags=creationflags
                )
                
                # 启动线程读取输出
                threading.Thread(target=self.read_console_output_simple, daemon=True).start()
                
                # 启动后重新设置控制台焦点
                self.console_text.focus_set()
                
            except FileNotFoundError:
                messagebox.showerror("错误", "未找到Python解释器。请确保已安装Python并添加到系统PATH环境变量中。")
                self.running[0] = False
            except Exception as e:
                messagebox.showerror("错误", f"运行失败: {str(e)}")
                self.running[0] = False
            
        else:
            messagebox.showwarning("警告", "请先保存文件")

    def analyze_syntax(self):
        """AI分析代码"""
        # 获取当前编辑的代码
        code = self.code_text.get(1.0, tk.END)
        
        if not code.strip():
            messagebox.showwarning("警告", "请先输入代码")
            return
        
        # 检查是否设置了API密钥
        try:
            import ai_compiler
            # 设置API密钥（你需要在某个地方设置这个）
            ai_compiler.set_api_key("sk-da4d67f10f7d407599e333ad99994758")
            
            # 显示等待提示
            self.console_text.insert(tk.END, "\n🤖 AI正在分析代码...\n>>> ")
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            
            # 调用AI分析
            result = ai_compiler.analyze(code)
            
            # 显示结果
            self.console_text.insert(tk.END, f"\n📊 分析结果：\n{result}\n>>> ")
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            
        except ImportError:
            messagebox.showerror("错误", "找不到AI编译器模块")
        except Exception as e:
            messagebox.showerror("错误", f"分析失败：{str(e)}")

    # 你还可以添加更多AI功能：
    def explain_code(self):
        """解释代码"""
        code = self.code_text.get(1.0, tk.END)
        if code.strip():
            try:
                import ai_compiler
                result = ai_compiler.explain(code)
                self.show_ai_result("代码解释", result)
            except Exception as e:
                messagebox.showerror("错误", f"解释失败：{str(e)}")

    def optimize_code(self):
        """优化代码"""
        code = self.code_text.get(1.0, tk.END)
        if code.strip():
            try:
                import ai_compiler
                result = ai_compiler.optimize(code)
                self.show_ai_result("代码优化", result)
            except Exception as e:
                messagebox.showerror("错误", f"优化失败：{str(e)}")

    def show_ai_result(self, title, content):
        """显示AI分析结果"""
        result_window = tk.Toplevel(self.root)
        result_window.title(title)
        result_window.geometry("800x600")
        
        text_area = scrolledtext.ScrolledText(result_window, wrap=tk.WORD, font=("Consolas", 11))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_area.insert(tk.END, content)
        text_area.config(state=tk.DISABLED)
        
        # 添加关闭按钮
        tk.Button(result_window, text="关闭", command=result_window.destroy).pack(pady=10)

    def show_about(self):
        messagebox.showinfo("关于", "Python聚源仓项目，是一款AI智能编译器，目前只支持Python，制作团队基本都是学生，具有AI分析代码，AI优化代码，AI上下文理解等功能，完全免费，完全免费开源")

    def on_close(self):
        # 关闭控制台进程
        if self.console_process:
            self.console_process.stdin.close()
            self.console_process.terminate()
            self.console_process.wait()
        # 关闭终端进程
        if self.terminal_process:
            self.terminal_process.stdin.close()
            self.terminal_process.terminate()
            self.terminal_process.wait()
        self.root.destroy()

    def stop_code(self):
        """停止正在运行的Python程序（增强版）"""
        if not self.console_process:
            self.console_text.insert(tk.END, "\n⚠️ 没有正在运行的程序\n>>> ")
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            return
        
        try:
            # 检查进程状态
            if self.console_process.poll() is None:
                self.console_text.insert(tk.END, "\n🛑 正在停止程序...\n")
                self.console_text.see(tk.END)
                
                # 先尝试温和地终止
                self.console_process.terminate()
                
                # 等待最多3秒
                try:
                    self.console_process.wait(timeout=3)
                    self.console_text.insert(tk.END, "✅ 程序已正常停止\n>>> ")
                except subprocess.TimeoutExpired:
                    # 如果不响应，强制杀死
                    self.console_text.insert(tk.END, "⚠️ 程序无响应，强制终止...\n")
                    self.console_process.kill()
                    self.console_process.wait()
                    self.console_text.insert(tk.END, "✅ 程序已强制终止\n>>> ")
            else:
                self.console_text.insert(tk.END, "\nℹ️ 程序已经结束运行\n>>> ")
            
            self.running[0] = False
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            
        except Exception as e:
            self.console_text.insert(tk.END, f"\n❌ 停止失败: {str(e)}\n>>> ")
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)

    def force_stop_all(self):
        """强制停止所有Python进程（紧急情况使用）"""
        try:
            import psutil
            current_pid = os.getpid()
            
            # 查找并终止所有Python进程（除了编辑器本身）
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        if proc.info['pid'] != current_pid and proc.info['pid'] != self.console_process.pid if self.console_process else True:
                            proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            self.console_text.insert(tk.END, "\n🚨 已强制停止所有Python进程\n>>> ")
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            
        except ImportError:
            # 如果没有psutil，使用系统命令
            if sys.platform == "win32":
                os.system("taskkill /f /im python.exe")
            else:
                os.system("pkill -f python")
            
            self.console_text.insert(tk.END, "\n🚨 已强制停止Python进程\n>>> ")
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)

    def safe_close(self):
        """安全关闭应用程序"""
        try:
            # 停止所有运行的进程
            self.stop_code()
            
            # 关闭终端进程
            if self.terminal_process and self.terminal_process.poll() is None:
                self.terminal_process.terminate()
                try:
                    self.terminal_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.terminal_process.kill()
            
            # 关闭控制台进程
            if self.console_process and self.console_process.poll() is None:
                self.console_process.terminate()
                try:
                    self.console_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.console_process.kill()
            
        except Exception as e:
            print(f"关闭过程中出现错误: {e}")
        finally:
            # 确保主窗口被销毁
            self.root.quit()
            self.root.destroy()

    def open_system_terminal(self):
        """打开系统终端（增强版）"""
        try:
            # 获取要在其中打开终端的目录
            target_dir = self.project_root
            if self.current_file:
                # 如果有当前文件，在其所在目录打开
                target_dir = os.path.dirname(self.current_file)
            
            # 确保目录存在
            if not os.path.exists(target_dir):
                target_dir = self.project_root
            
            self.console_text.insert(tk.END, f"\n🔧 在目录打开终端: {target_dir}\n>>> ", 'Terminal')
            
            if sys.platform == 'win32':
                # Windows - 优先使用PowerShell，其次cmd
                try:
                    # 使用start命令在新窗口中打开
                    subprocess.Popen(f'start powershell -NoExit -Command "cd \'{target_dir}\'"', 
                                shell=True)
                    self.console_text.insert(tk.END, "\n✅ 已在新窗口打开PowerShell\n>>> ", 'Terminal')
                except Exception:
                    try:
                        subprocess.Popen(f'start cmd /K "cd /d \"{target_dir}\""', 
                                    shell=True)
                        self.console_text.insert(tk.END, "\n✅ 已在新窗口打开命令提示符\n>>> ", 'Terminal')
                    except Exception as e:
                        raise e
            
            elif sys.platform == 'darwin':
                # macOS
                applescript = f'''
                tell application "Terminal"
                    activate
                    do script "cd '{target_dir}' && clear"
                end tell
                '''
                subprocess.Popen(['osascript', '-e', applescript])
                self.console_text.insert(tk.END, "\n✅ 已打开Terminal\n>>> ", 'Terminal')
            
            else:
                # Linux
                terminals = [
                    ('gnome-terminal', ['--working-directory', target_dir]),
                    ('konsole', ['--workdir', target_dir]),
                    ('xfce4-terminal', ['--default-working-directory', target_dir]),
                    ('terminator', ['--working-directory', target_dir]),
                    ('xterm', ['-e', f'bash -c "cd \\"{target_dir}\\"; bash"'])
                ]
                
                terminal_found = False
                for terminal, args in terminals:
                    try:
                        subprocess.Popen([terminal] + args)
                        self.console_text.insert(tk.END, f"\n✅ 已打开{terminal}\n>>> ", 'Terminal')
                        terminal_found = True
                        break
                    except FileNotFoundError:
                        continue
                
                if not terminal_found:
                    # 最后尝试使用桌面环境的默认终端
                    try:
                        subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "cd \\"{target_dir}\\"; bash"'])
                        self.console_text.insert(tk.END, "\n✅ 已打开系统默认终端\n>>> ", 'Terminal')
                    except FileNotFoundError:
                        raise FileNotFoundError("未找到可用的终端程序")
            
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)
            
        except Exception as e:
            self.console_text.insert(tk.END, f"\n❌ 打开系统终端失败: {str(e)}\n>>> ", 'Error')
            self.console_text.mark_set("input_start", "end-1c")
            self.console_text.mark_gravity("input_start", "left")
            self.console_text.see(tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = CodeEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.safe_close)
    root.mainloop()