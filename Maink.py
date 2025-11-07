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
        self.root.title("聚源仓-Version1.0.2")
        self.root.geometry("1440x900")
        if os.path.exists("./Resources/app.ico"):
            self.root.iconbitmap("./Resources/app.ico")
        
        # 设置API密钥
        self.setup_api_key()
        
        # 比例系数，用于等比例缩放
        self.scale_ratio = 1.0
    
        self.toolbar_items = [
            ("新建", './Resources/new.png', self.new_file),
            ("打开", './Resources/open.png', self.open_file),
            ("保存", './Resources/save.png', self.save_file),
            ("运行", './Resources/run.png', self.run_code_in_terminal),
            ("停止", './Resources/stop.png', self.stop_code), 
            ("AI助手", './Resources/ai.png', self.open_chat),
            ("打开系统终端", './Resources/run.png', self.open_system_terminal),
            ("关于", './Resources/info.png', self.show_about),
        ]
        
        # 当前打开的文件路径
        self.current_file = None
        self.console_process = None
        self.running = [False]
        
        # 聊天相关属性
        self.chat_history = []
        
        self.setup_ui()
        
        self.root.bind("<Configure>", self.on_resize)
        
        # 初始时扫描当前目录
        self.project_root = os.getcwd()
        self.populate_tree(self.project_root)

    def setup_api_key(self):
        """设置DeepSeek API密钥"""
        try:
            import ai_compiler
            # 在这里设置你的API密钥
            api_key = "你的Deepseek API"
            ai_compiler.set_api_key(api_key)
            print("API密钥设置成功")
        except ImportError as e:
            print(f"导入ai_compiler失败: {e}")
        except Exception as e:
            print(f"设置API密钥失败: {e}")


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
        
        # 右侧代码编辑区域
        self.edit_frame = ttk.Frame(self.main_container)
        self.edit_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        self.code_text = scrolledtext.ScrolledText(self.edit_frame, wrap=tk.WORD, font=("Consolas", 12))
        self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 底部信息显示区域（不再是交互式终端）
        self.info_frame = ttk.Frame(self.root, height=150)
        self.info_frame.pack(fill=tk.BOTH, side=tk.BOTTOM)
        
        info_header = ttk.Frame(self.info_frame)
        info_header.pack(fill=tk.X, padx=5, pady=5)
        tk.Label(info_header, text="运行信息", font=('Consolas', 13)).pack(side=tk.LEFT)
        
        # 添加清空按钮
        ttk.Button(info_header, text='清空信息', command=self.clear_info).pack(side=tk.RIGHT, padx=2)
        
        self.info_text = scrolledtext.ScrolledText(self.info_frame, wrap=tk.WORD, font=("Consolas", 11))
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.info_text.config(state=tk.DISABLED)  # 设置为只读

    def clear_info(self):
        """清空信息显示区域"""
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        self.info_text.config(state=tk.DISABLED)

    def add_info_message(self, message, message_type="info"):
        """添加信息到信息显示区域"""
        self.info_text.config(state=tk.NORMAL)
        
        if message_type == "error":
            self.info_text.insert(tk.END, f"❌ {message}\n", "error")
            self.info_text.tag_configure("error", foreground="red")
        elif message_type == "success":
            self.info_text.insert(tk.END, f"✅ {message}\n", "success")
            self.info_text.tag_configure("success", foreground="green")
        elif message_type == "warning":
            self.info_text.insert(tk.END, f"⚠️ {message}\n", "warning")
            self.info_text.tag_configure("warning", foreground="orange")
        else:
            self.info_text.insert(tk.END, f"ℹ️ {message}\n")
        
        self.info_text.config(state=tk.DISABLED)
        self.info_text.see(tk.END)

    def run_code_in_terminal(self):
        """在外部系统终端中运行代码"""
        if not self.current_file:
            # 如果没有保存的文件，先保存
            if not self.save_file():
                messagebox.showwarning("警告", "请先保存文件")
                return
        
        try:
            # 确保文件已保存
            self.save_file()
            
            # 获取文件所在目录
            file_dir = os.path.dirname(self.current_file)
            file_name = os.path.basename(self.current_file)
            
            self.add_info_message(f"正在在系统终端中运行: {file_name}")
            
            if sys.platform == 'win32':
                # Windows系统：使用cmd或PowerShell
                try:
                    # 尝试使用PowerShell
                    cmd = f'start powershell -NoExit -Command "cd \'{file_dir}\'; python \'{file_name}\'; echo \'程序执行完毕，按任意键退出...\'; pause"'
                    subprocess.Popen(cmd, shell=True)
                    self.add_info_message("已在PowerShell中启动程序", "success")
                except Exception as e:
                    # 如果PowerShell失败，尝试使用cmd
                    try:
                        cmd = f'start cmd /K "cd /d \"{file_dir}\" && python \"{file_name}\" && pause"'
                        subprocess.Popen(cmd, shell=True)
                        self.add_info_message("已在命令提示符中启动程序", "success")
                    except Exception as e2:
                        self.add_info_message(f"启动终端失败: {str(e2)}", "error")
            else:
                # 非Windows系统：使用系统默认终端
                try:
                    if sys.platform == 'darwin':  # macOS
                        applescript = f'''
                        tell application "Terminal"
                            activate
                            do script "cd '{file_dir}' && python3 '{file_name}' && echo '程序执行完毕，按任意键退出...' && read"
                        end tell
                        '''
                        subprocess.Popen(['osascript', '-e', applescript])
                    else:  # Linux
                        terminals = [
                            ('gnome-terminal', ['--', 'bash', '-c', f'cd "{file_dir}" && python3 "{file_name}" && echo "程序执行完毕，按任意键退出..." && read']),
                            ('konsole', ['-e', 'bash', '-c', f'cd "{file_dir}" && python3 "{file_name}" && echo "程序执行完毕，按任意键退出..." && read']),
                            ('xfce4-terminal', ['-x', 'bash', '-c', f'cd "{file_dir}" && python3 "{file_name}" && echo "程序执行完毕，按任意键退出..." && read']),
                            ('xterm', ['-e', f'bash -c "cd \\"{file_dir}\\" && python3 \\"{file_name}\\" && echo \\"程序执行完毕，按任意键退出...\\" && read"'])
                        ]
                        
                        terminal_found = False
                        for terminal, args in terminals:
                            try:
                                subprocess.Popen([terminal] + args)
                                terminal_found = True
                                self.add_info_message(f"已在{terminal}中启动程序", "success")
                                break
                            except FileNotFoundError:
                                continue
                        
                        if not terminal_found:
                            # 使用系统默认终端
                            subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "cd \\"{file_dir}\\" && python3 \\"{file_name}\\" && echo \\"程序执行完毕，按任意键退出...\\" && read"'])
                            self.add_info_message("已在系统默认终端中启动程序", "success")
                
                except Exception as e:
                    self.add_info_message(f"启动终端失败: {str(e)}", "error")
                    
        except Exception as e:
            self.add_info_message(f"运行失败: {str(e)}", "error")

    def open_chat(self):
        """打开AI聊天窗口"""
        chat_window = tk.Toplevel(self.root)
        chat_window.title("AI智能编程助手")
        chat_window.geometry("700x600")
        chat_window.transient(self.root)
        
        # 设置当前代码上下文
        current_code = self.code_text.get(1.0, tk.END).strip()
        if current_code:
            try:
                import ai_compiler
                ai_compiler.set_current_code(current_code)
            except:
                pass
        
        # 聊天历史显示区域
        chat_history_frame = ttk.Frame(chat_window)
        chat_history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 工具栏
        toolbar = ttk.Frame(chat_history_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(toolbar, text="🤖 AI智能编程助手", font=('等线', 14, 'bold')).pack(side=tk.LEFT)
        
        # 功能按钮
        button_frame = ttk.Frame(toolbar)
        button_frame.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="分析代码", 
                  command=lambda: self.analyze_current_code(chat_window)).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="优化建议", 
                  command=lambda: self.suggest_improvements(chat_window)).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="解释代码", 
                  command=lambda: self.explain_current_code(chat_window)).pack(side=tk.LEFT, padx=2)
        
        self.chat_history_text = scrolledtext.ScrolledText(
            chat_history_frame, 
            wrap=tk.WORD, 
            font=("等线", 11),
            height=20
        )
        self.chat_history_text.pack(fill=tk.BOTH, expand=True)
        self.chat_history_text.config(state=tk.DISABLED)
        
        # 输入区域
        input_frame = ttk.Frame(chat_window)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.chat_input = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            font=("等线", 11),
            height=4
        )
        self.chat_input.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        ttk.Button(button_frame, text="发送", 
                  command=lambda: self.send_chat_message(chat_window)).pack(pady=2)
        ttk.Button(button_frame, text="清空", 
                  command=self.clear_chat).pack(pady=2)
        ttk.Button(button_frame, text="插入代码", 
                  command=self.insert_chat_code).pack(pady=2)
        ttk.Button(button_frame, text="清空历史", 
                  command=self.clear_chat_history).pack(pady=2)
        
        # 绑定快捷键
        self.chat_input.bind("<Control-Return>", lambda e: self.send_chat_message(chat_window))
        
        # 显示欢迎消息
        welcome_msg = """🤖 欢迎使用AI智能编程助手！

我可以帮助您：
• 📊 深度分析代码质量和性能
• ⚡ 提供专业的优化建议
• 📝 详细解释代码逻辑
• 🔧 调试和修复问题
• 💡 教学编程概念和最佳实践
• 🔍 进行代码审查

请描述您的问题或需要帮助的代码部分。"""
        self.add_chat_message("AI", welcome_msg)

    def analyze_current_code(self, chat_window):
        """分析当前代码"""
        current_code = self.code_text.get(1.0, tk.END).strip()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请分析当前编辑器的代码")
        self.add_chat_message("AI", "正在深度分析代码...")
        
        threading.Thread(target=self.analyze_code_thread, args=(current_code,), daemon=True).start()

    def suggest_improvements(self, chat_window):
        """获取改进建议"""
        current_code = self.code_text.get(1.0, tk.END).strip()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请为当前代码提供改进建议")
        self.add_chat_message("AI", "正在分析改进机会...")
        
        threading.Thread(target=self.suggest_improvements_thread, args=(current_code,), daemon=True).start()

    def explain_current_code(self, chat_window):
        """解释当前代码"""
        current_code = self.code_text.get(1.0, tk.END).strip()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请详细解释当前代码")
        self.add_chat_message("AI", "正在分析代码逻辑...")
        
        threading.Thread(target=self.explain_code_thread, args=(current_code,), daemon=True).start()

    def analyze_code_thread(self, code):
        """分析代码线程"""
        try:
            import ai_compiler
            response = ai_compiler.analyze(code)
            self.root.after(0, lambda: self.add_chat_message("AI", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("AI", f"分析失败：{str(e)}"))

    def suggest_improvements_thread(self, code):
        """改进建议线程"""
        try:
            import ai_compiler
            response = ai_compiler.suggest_improvements(code)
            self.root.after(0, lambda: self.add_chat_message("AI", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("AI", f"获取建议失败：{str(e)}"))

    def explain_code_thread(self, code):
        """解释代码线程"""
        try:
            import ai_compiler
            response = ai_compiler.explain(code)
            self.root.after(0, lambda: self.add_chat_message("AI", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("AI", f"解释失败：{str(e)}"))

    def send_chat_message(self, chat_window):
        """发送聊天消息"""
        message = self.chat_input.get(1.0, tk.END).strip()
        if not message:
            return
            
        # 添加用户消息到聊天历史
        self.add_chat_message("你", message)
        
        # 清空输入框
        self.chat_input.delete(1.0, tk.END)
        
        # 显示思考中消息
        self.add_chat_message("AI", "思考中...")
        
        # 获取当前代码上下文
        current_code = self.code_text.get(1.0, tk.END).strip()
        if not current_code:
            current_code = None
        
        # 在新线程中调用AI
        threading.Thread(target=self.chat_with_ai, args=(message, current_code), daemon=True).start()

    def chat_with_ai(self, message, code_context):
        """与AI对话"""
        try:
            import ai_compiler
            response = ai_compiler.chat(message, code_context)
            self.root.after(0, lambda: self.add_chat_message("AI", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("AI", f"对话失败：{str(e)}"))

    def clear_chat_history(self):
        """清空聊天历史"""
        try:
            import ai_compiler
            ai_compiler.clear_chat_history()
            self.chat_history_text.config(state=tk.NORMAL)
            self.chat_history_text.delete(1.0, tk.END)
            self.chat_history_text.config(state=tk.DISABLED)
            self.add_chat_message("AI", "对话历史已清空！")
        except Exception as e:
            self.add_chat_message("AI", f"清空历史失败：{str(e)}")

    def add_chat_message(self, sender, message):
        """添加消息到聊天历史"""
        self.chat_history_text.config(state=tk.NORMAL)
        
        # 如果是思考中消息，先删除上一条思考中消息
        if message == "思考中...":
            # 查找并删除上一条思考中消息
            content = self.chat_history_text.get(1.0, tk.END)
            if "思考中..." in content:
                # 简单实现：删除最后一条消息
                lines = content.strip().split('\n')
                new_lines = [line for line in lines if "思考中..." not in line]
                self.chat_history_text.delete(1.0, tk.END)
                self.chat_history_text.insert(tk.END, '\n'.join(new_lines) + '\n')
        
        if sender == "AI":
            self.chat_history_text.insert(tk.END, f"\n🤖 {sender}: {message}\n", "ai_message")
            self.chat_history_text.tag_configure("ai_message", foreground="blue")
        else:
            self.chat_history_text.insert(tk.END, f"\n👤 {sender}: {message}\n", "user_message")
            self.chat_history_text.tag_configure("user_message", foreground="green")
        
        self.chat_history_text.config(state=tk.DISABLED)
        self.chat_history_text.see(tk.END)
        
        # 保存到聊天历史
        self.chat_history.append({"sender": sender, "message": message, "timestamp": time.time()})

    def clear_chat(self):
        """清空聊天输入"""
        self.chat_input.delete(1.0, tk.END)

    def insert_chat_code(self):
        """将聊天中的代码插入到编辑器"""
        # 获取聊天历史中最后一条AI消息
        ai_messages = [msg for msg in self.chat_history if msg["sender"] == "AI"]
        if not ai_messages:
            messagebox.showinfo("提示", "没有找到AI生成的代码")
            return
            
        last_ai_message = ai_messages[-1]["message"]
        
        # 提取代码块（假设代码在```python和```之间）
        if "```python" in last_ai_message:
            code_start = last_ai_message.find("```python") + 9
            code_end = last_ai_message.find("```", code_start)
            code = last_ai_message[code_start:code_end].strip()
            
            # 插入到代码编辑器
            self.code_text.insert(tk.END, f"\n\n# AI生成的代码\n{code}\n")
            self.add_info_message("AI生成的代码已插入到编辑器中", "success")
        else:
            messagebox.showinfo("提示", "未找到可插入的代码块")

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
                
                # 在信息显示区域显示提示
                self.add_info_message(f"已打开文件: {file_path}")
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

    def update_layout(self):
        # 根据比例系数调整各部分大小
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # 左侧树宽度占总宽度的20%
        tree_width = int(window_width * 0.2)
        self.ast_frame.config(width=tree_width)
        
        # 信息显示区域高度占总高度的20%
        info_height = int(window_height * 0.2)
        self.info_frame.config(height=info_height)

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
        self.add_info_message("已创建新文件")

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if file_path:
            self.current_file = file_path
            with open(file_path, "r", encoding="utf-8") as f:
                self.code_text.delete(1.0, tk.END)
                self.code_text.insert(1.0, f.read())
            self.add_info_message(f"已打开文件: {file_path}")

    def save_file(self):
        if self.current_file:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.code_text.get(1.0, tk.END))
            self.add_info_message(f"已保存文件: {self.current_file}", "success")
            return True
        else:
            return self.save_file_as()

    def save_file_as(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Files", "*.py"), ("All Files", "*.*")])
        if file_path:
            self.current_file = file_path
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.code_text.get(1.0, tk.END))
            self.add_info_message(f"已保存文件: {file_path}", "success")
            return True
        return False

    def run_code(self):
        """保留原有的运行功能（不使用）"""
        pass

    def analyze_syntax(self):
        """AI分析代码"""
        # 获取当前编辑的代码
        code = self.code_text.get(1.0, tk.END)
        
        if not code.strip():
            messagebox.showwarning("警告", "请先输入代码")
            return
        
        # 检查是否设置了API密钥
        try:
            # 在 Maink.py 的适当位置添加
            import ai_compiler
            ai_compiler.set_api_key("你的Deepseek API")
            
            # 显示等待提示
            self.add_info_message("AI正在分析代码...")
            
            # 调用AI分析
            result = ai_compiler.analyze(code)
            
            # 显示结果
            self.add_info_message(f"分析结果：{result}")
            
        except ImportError:
            messagebox.showerror("错误", "找不到AI编译器模块")
        except Exception as e:
            messagebox.showerror("错误", f"分析失败：{str(e)}")

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

    def stop_code(self):
        """停止正在运行的代码"""
        self.add_info_message("停止功能：请在打开的终端窗口中手动停止程序", "warning")

    def safe_close(self):
        """安全关闭应用程序"""
        try:
            # 如果有未保存的更改，提示保存
            if self.current_file:
                # 这里可以添加检查文件是否已修改的逻辑
                pass
            
        except Exception as e:
            print(f"关闭过程中出现错误: {e}")
        finally:
            # 确保主窗口被销毁
            self.root.quit()
            self.root.destroy()

    def open_system_terminal(self):
        """打开系统终端"""
        try:
            # 获取要在其中打开终端的目录
            target_dir = self.project_root
            if self.current_file:
                # 如果有当前文件，在其所在目录打开
                target_dir = os.path.dirname(self.current_file)
            
            # 确保目录存在
            if not os.path.exists(target_dir):
                target_dir = self  
            
            self.add_info_message(f"在目录打开终端: {target_dir}")
            
            if sys.platform == 'win32':
                # Windows - 优先使用PowerShell，其次cmd
                try:
                    # 使用start命令在新窗口中打开
                    subprocess.Popen(f'start powershell -NoExit -Command "cd \'{target_dir}\'"', 
                                shell=True)
                    self.add_info_message("已在新窗口打开PowerShell", "success")
                except Exception:
                    try:
                        subprocess.Popen(f'start cmd /K "cd /d \"{target_dir}\""', 
                                    shell=True)
                        self.add_info_message("已在新窗口打开命令提示符", "success")
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
                self.add_info_message("已打开Terminal", "success")
            
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
                        terminal_found = True
                        self.add_info_message(f"已打开{terminal}", "success")
                        break
                    except FileNotFoundError:
                        continue
                
                if not terminal_found:
                    # 最后尝试使用桌面环境的默认终端
                    try:
                        subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "cd \\"{target_dir}\\"; bash"'])
                        self.add_info_message("已打开系统默认终端", "success")
                    except FileNotFoundError:
                        raise FileNotFoundError("未找到可用的终端程序")
            
        except Exception as e:
            self.add_info_message(f"打开系统终端失败: {str(e)}", "error")

if __name__ == "__main__":
    root = tk.Tk()
    app = CodeEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.safe_close)
    root.mainloop()