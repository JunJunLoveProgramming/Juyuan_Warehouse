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
import backend
import random
import tempfile
import webbrowser
import re

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

class CodeEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("聚源仓-Version1.0.4-开源版本")
        self.root.geometry("1440x900")
        if os.path.exists("./Resources/app.ico"):
            self.root.iconbitmap("./Resources/app.ico")
        
        # 先初始化所有属性
        self.current_file = None
        self.current_file_type = "python"
        self.console_process = None
        self.running = [False]
        self.chat_history = []
        self.syntax_highlight_enabled = True
        self.project_root = os.getcwd()
        self.scale_ratio = 1.0
        
        # 确保所有UI组件属性都有初始值
        self.info_text = None
        self.code_text = None
        self.file_type_label = None
        self.tree = None
        self.backend_processor = None
        self.toolbar = None
        self.main_container = None
        self.ast_frame = None
        self.edit_frame = None
        self.info_frame = None
        
        # 工具栏项目
        self.toolbar_items = [
            ("打开", './Resources/open.png', self.open_file),
            ("保存", './Resources/save.png', self.save_file),
            ("运行", './Resources/run.png', self.run_current_file),
            ("AI助手", './Resources/ai.png', self.open_chat),
            ("安装库", './Resources/open.png', self.install_library),
            ("打包EXE", './Resources/open.png', self.package_to_exe),
            ("打开系统终端", './Resources/run.png', self.open_system_terminal),
            ("关于", './Resources/info.png', self.show_about),
            ("新建Python文件",'./Resources/new.png',lambda: self.new_file("python")),
            ("新建HTML文件",'./Resources/new.png',lambda: self.new_file("html")),
            ("新建Markdown文件",'./Resources/new.png',lambda: self.new_file("markdown"))
        ]
        
        # 初始化UI组件
        self.setup_ui()
        
        # 初始化其他组件
        self.setup_api_key()
        self.setup_backend()
        
        self.root.bind("<Configure>", self.on_resize)
        
        # 初始时扫描当前目录
        self.populate_tree(self.project_root)

    def setup_api_key(self):
        """设置DeepSeek API密钥 - 修复版本"""
        try:
            import ai_compiler
            
            # 你的DeepSeek API密钥 - 请确保这是有效的密钥
            api_key = "你的Deepseek API"
            
            # 检查API密钥是否有效
            if not api_key or api_key == "你的Deepseek API":
                self.add_info_message("请先在代码中设置有效的DeepSeek API密钥", "warning")
                print("警告: 未设置有效的API密钥")
                return False
                
            # 使用新的验证设置方法
            success = ai_compiler.validate_and_set_api(api_key)
            if success:
                self.add_info_message("API密钥设置成功", "success")
                print("API密钥设置成功")
                
                # 设置环境变量以确保其他模块也能访问
                os.environ['DEEPSEEK_API_KEY'] = api_key
                os.environ['OPENAI_API_KEY'] = api_key
                
                return True
            else:
                self.add_info_message("API密钥设置失败，请检查密钥是否正确", "error")
                return False
                
        except ImportError as e:
            self.add_info_message(f"导入ai_compiler失败: {e}", "error")
            return False
        except Exception as e:
            self.add_info_message(f"设置API密钥失败: {e}", "error")
            return False

    def setup_backend(self):
        """初始化backend处理引擎"""
        try:
            self.backend_processor = backend.backEndprocessing()
            # 设置语法高亮标签
            self.backend_processor.setTagKeyWord("keyword")
            print("Backend语法高亮引擎初始化成功")
        except Exception as e:
            print(f"Backend初始化失败: {e}")
            self.backend_processor = None

    def setup_ui(self):
        """初始化用户界面 - 修复版本"""
        try:
            # 顶部工具栏
            self.toolbar = ttk.Frame(self.root)
            self.toolbar.pack(fill=tk.X, side=tk.TOP)
            
            # 批量注册工具栏项目
            self.image = []

            if os.path.exists('./Resources/app.jpg'):
                try:
                    img = Image.open('./Resources/app.jpg')
                    img = img.resize((80, 80))
                    self.image.append(ImageTk.PhotoImage(img))
                    tk.Button(self.toolbar, image=self.image[0], relief="flat", command=self.hidden_easter_egg).pack(side='left')
                except Exception as e:
                    print(f"加载logo图片失败: {e}")
                
            for name, icon, command in self.toolbar_items:
                try:
                    if icon is not None and os.path.exists(icon):
                        ico = Image.open(icon).resize((40, 40))
                        self.image.append(ImageTk.PhotoImage(ico))
                        tk.Button(self.toolbar, text=name, command=command, font=('等线', 12, 'bold'),
                                  relief='flat', image=self.image[-1], compound='top').pack(side=tk.LEFT, padx=2, pady=2)
                    else:
                        tk.Button(self.toolbar, text=name, command=command, font=('等线', 12, 'bold'),
                                  relief='flat').pack(side=tk.LEFT, padx=2, pady=2)
                except Exception as e:
                    print(f"加载工具栏按钮失败 {name}: {e}")
                    # 创建备用按钮
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
            
            # 单编辑器模式
            self.setup_single_editor()
            
            # 底部信息显示区域
            self.info_frame = ttk.Frame(self.root, height=150)
            self.info_frame.pack(fill=tk.BOTH, side=tk.BOTTOM)
            
            info_header = ttk.Frame(self.info_frame)
            info_header.pack(fill=tk.X, padx=5, pady=5)
            tk.Label(info_header, text="运行信息", font=('Consolas', 13)).pack(side=tk.LEFT)
                    
            # 添加清空按钮
            ttk.Button(info_header, text='清空信息', command=self.clear_info).pack(side=tk.RIGHT, padx=2)
            
            # 确保info_text被正确创建
            self.info_text = scrolledtext.ScrolledText(self.info_frame, wrap=tk.WORD, font=("Consolas", 11))
            self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.info_text.config(state=tk.DISABLED)  # 设置为只读
            
            print("UI初始化完成")
            
        except Exception as e:
            print(f"UI初始化失败: {e}")
            # 创建紧急备用信息显示
            self.info_text = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, font=("Consolas", 11))
            self.info_text.pack(fill=tk.BOTH, expand=True)
            self.info_text.config(state=tk.DISABLED)
            self.add_info_message(f"UI初始化错误: {e}", "error")

    def setup_single_editor(self):
        """设置单编辑器 - 修复版本"""
        try:
            # 编辑器类型显示
            self.file_type_label = ttk.Label(self.edit_frame, text="Python文件", font=('等线', 12, 'bold'))
            self.file_type_label.pack(fill=tk.X, padx=5, pady=2)
            
            # 主编辑器
            self.code_text = scrolledtext.ScrolledText(self.edit_frame, wrap=tk.WORD, font=("Consolas", 12))
            self.code_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            self.code_text.tag_configure("keyword", foreground="blue", font=("Consolas", 12, "bold"))
            self.code_text.bind("<KeyRelease>", self.on_code_change)
            
        except Exception as e:
            print(f"编辑器设置失败: {e}")

    def add_info_message(self, message, message_type="info"):
        """添加信息到信息显示区域 - 修复版本"""
        try:
            # 确保info_text存在
            if not hasattr(self, 'info_text') or self.info_text is None:
                print(f"信息显示区域未初始化: {message}")
                return
                
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
            
        except Exception as e:
            print(f"添加信息失败: {e} - 原始消息: {message}")

    def clear_info(self):
        """清空信息显示区域 - 修复版本"""
        try:
            if hasattr(self, 'info_text') and self.info_text is not None:
                self.info_text.config(state=tk.NORMAL)
                self.info_text.delete(1.0, tk.END)
                self.info_text.config(state=tk.DISABLED)
        except Exception as e:
            print(f"清空信息失败: {e}")

    def on_code_change(self, event=None):
        """当代码内容改变时触发的函数 - 修复版本"""
        try:
            if (self.syntax_highlight_enabled and self.backend_processor and 
                hasattr(self, 'code_text') and self.code_text is not None):
                self.apply_syntax_highlighting()
        except Exception as e:
            print(f"代码变更处理失败: {e}")

    def apply_syntax_highlighting(self):
        """应用语法高亮 - 修复版本"""
        if not self.backend_processor or not hasattr(self, 'code_text') or self.code_text is None:
            return
            
        try:
            # 获取当前文本
            text_content = self.code_text.get("1.0", "end-1c")
            self.code_text.tag_remove("keyword", "1.0", "end")
            
            # 只有Python文件才应用Python语法高亮
            if self.current_file_type == "python":
                self.backend_processor.insertColorTag(text_content, self.code_text)
            
        except Exception as e:
            # 语法高亮出错时不中断用户操作
            print(f"语法高亮错误: {e}")

    def run_current_file(self):
        """运行当前文件"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先打开或保存一个文件")
            return
        
        if self.current_file_type == "python":
            self.run_python_file()
        elif self.current_file_type == "html":
            self.run_html_file()
        else:
            messagebox.showinfo("提示", f"不支持运行 {self.current_file_type} 文件")

    def run_python_file(self):
        """运行Python文件"""
        # 先保存文件
        if not self.save_file():
            messagebox.showwarning("警告", "请先保存文件")
            return
        
        try:
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

    def run_html_file(self):
        """运行HTML文件"""
        # HTML文件需要先保存
        if not self.save_file():
            messagebox.showwarning("警告", "请先保存HTML文件")
            return
        
        try:
            # 在系统默认浏览器中打开HTML文件
            webbrowser.open(f'file://{self.current_file}')
            self.add_info_message("已在浏览器中打开HTML文件", "success")
        except Exception as e:
            self.add_info_message(f"打开HTML文件失败: {str(e)}", "error")

    def hidden_easter_egg(self):
        """隐藏彩蛋"""
        try:
            self.hidden_easter_egg_window = tk.Toplevel(self.root)
            self.hidden_easter_egg_window.title("聚源仓团队前端准备的彩蛋")
            self.hidden_easter_egg_window.geometry("400x500")
            self.hidden_easter_egg_window.transient(self.root)
            if os.path.exists("./Resources/app.ico"):
                self.hidden_easter_egg_window.iconbitmap("./Resources/app.ico")

            self.image_paths = [
                "./Resources/rehv/1.jpg",
                "./Resources/rehv/7.jpg",
                "./Resources/rehv/8.jpg",
                "./Resources/rehv/9.jpg",
                "./Resources/rehv/10.jpg",
                "./Resources/rehv/11.jpg",
                "./Resources/rehv/12.jpg",
                "./Resources/rehv/13.jpg",
                "./Resources/rehv/14.jpg",
                "./Resources/rehv/15.jpg",
                "./Resources/rehv/16.jpg",
                "./Resources/rehv/17.jpg",
                "./Resources/rehv/18.jpg",
                "./Resources/rehv/19.jpg",
                "./Resources/rehv/20.jpg",
                "./Resources/rehv/21.jpg",
                "./Resources/rehv/22.jpg",
                "./Resources/rehv/23.jpg",
                "./Resources/rehv/24.jpg",
                "./Resources/rehv/25.jpg",
                "./Resources/rehv/26.jpg",
                "./Resources/rehv/27.jpg",
                "./Resources/rehv/28.jpg",
                "./Resources/rehv/29.jpg",
                "./Resources/rehv/30.jpg",
                "./Resources/rehv/31.jpg",
                "./Resources/rehv/32.jpg",
                "./Resources/rehv/33.jpg", 
                "./Resources/rehv/34.jpg",
                "./Resources/rehv/35.jpg",
                "./Resources/rehv/36.jpg",
                "./Resources/rehv/37.jpg",
                "./Resources/rehv/38.jpg",  
                "./Resources/rehv/39.jpg",
                "./Resources/rehv/40.jpg",   
                "./Resources/rehv/41.jpg",       
                "./Resources/rehv/42.jpg",
                "./Resources/rehv/43.jpg",
                "./Resources/rehv/44.jpg",
                "./Resources/rehv/45.jpg",
                "./Resources/rehv/46.jpg",
                "./Resources/rehv/47.jpg",
                "./Resources/rehv/48.jpg",
                "./Resources/rehv/49.jpg",
                "./Resources/rehv/50.jpg",
                "./Resources/rehv/51.jpg",
                "./Resources/rehv/屏幕截图 2025-06-17 134644.png",
                "./Resources/rehv/屏幕截图 2025-06-17 134743.png",          
                "./Resources/rehv/屏幕截图 2025-06-23 133443.png",          
                "./Resources/rehv/屏幕截图 2025-06-23 133746.png",          
                "./Resources/rehv/屏幕截图 2025-07-09 205558.png",                                  
            ]

            self.create_widgets()
            
            self.show_random_image()
        except Exception as e:
            messagebox.showerror("错误", f"创建彩蛋窗口失败: {str(e)}")

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.hidden_easter_egg_window, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
                
        # 图片显示区域
        self.image_frame = ttk.Frame(main_frame, relief=tk.SUNKEN, width=400, height=300)
        self.image_frame.pack(pady=20, fill=tk.BOTH, expand=True)
        self.image_frame.pack_propagate(False)
        
        # 图片标签
        self.image_label = ttk.Label(self.image_frame)
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # 随机图片按钮
        random_button = ttk.Button(button_frame, text="随机图片", command=self.show_random_image)
        random_button.pack(side=tk.LEFT, padx=5)
        
        # 退出按钮
        exit_button = ttk.Button(button_frame, text="退出", command=self.hidden_easter_egg_window.destroy)
        exit_button.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def show_random_image(self):
        try:
            # 过滤出存在的图片路径
            existing_paths = [path for path in self.image_paths if os.path.exists(path)]
            
            if not existing_paths:
                self.status_var.set("错误: 未找到图片文件")
                return
                
            # 随机选择一个图片路径
            image_path = random.choice(existing_paths)
                
            # 打开并调整图片大小
            image = Image.open(image_path)
            image = self.resize_image(image, 400, 300)
                        
            # 转换为Tkinter可用的格式
            self.current_image = ImageTk.PhotoImage(image)
                        
            # 更新图片标签
            self.image_label.configure(image=self.current_image)
            self.status_var.set(f"已显示: {os.path.basename(image_path)}")
        except Exception as e:
            self.status_var.set(f"加载图片失败: {str(e)}")

    def resize_image(self, image, max_width, max_height):
        # 调整图片大小以适应显示区域
        width, height = image.size
        
        # 计算缩放比例
        ratio = min(max_width/width, max_height/height)
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        
        # 调整图片大小
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized_image

    def install_library(self):
        """一键安装第三方库 - 增强版本"""
        try:
            install_window = tk.Toplevel(self.root)
            install_window.title("一键安装第三方库")
            install_window.geometry("500x400")
            install_window.transient(self.root)
            
            # 主框架
            main_frame = ttk.Frame(install_window, padding=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 说明文字
            info_text = """🔧 智能库安装工具

功能特点：
• 使用清华源加速下载
• 可视化安装进度
• 自动处理依赖关系
• 支持批量安装多个库

在下方输入要安装的库名（多个库用空格分隔）

示例：
requests pandas numpy matplotlib
"""
            info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT, font=('等线', 10))
            info_label.pack(fill=tk.X, pady=(0, 15))
            
            # 输入框
            input_frame = ttk.Frame(main_frame)
            input_frame.pack(fill=tk.X, pady=10)
            
            ttk.Label(input_frame, text="库名称:", font=('等线', 11)).pack(side=tk.LEFT)
            self.lib_entry = ttk.Entry(input_frame, width=35, font=('等线', 11))
            self.lib_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0))
            self.lib_entry.bind("<Return>", lambda e: self.start_visual_install())
            
            # 常用库快速选择
            common_frame = ttk.LabelFrame(main_frame, text="常用库快速安装", padding=10)
            common_frame.pack(fill=tk.X, pady=10)
            
            common_libs = [
                "requests - HTTP请求库",
                "pandas - 数据分析",
                "numpy - 数值计算", 
                "matplotlib - 数据可视化",
                "pillow - 图像处理",
                "opencv-python - 计算机视觉",
                "django - Web框架",
                "flask - 轻量Web框架"
            ]
            
            for i in range(0, len(common_libs), 2):
                row_frame = ttk.Frame(common_frame)
                row_frame.pack(fill=tk.X, pady=2)
                
                for j in range(2):
                    if i + j < len(common_libs):
                        lib_info = common_libs[i + j]
                        lib_name = lib_info.split(' - ')[0]
                        tk.Button(row_frame, text=lib_info, font=('等线', 9),
                                 command=lambda name=lib_name: self.quick_install_lib(name),
                                 relief='flat', bg='#e8f4fd').pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # 安装选项
            options_frame = ttk.Frame(main_frame)
            options_frame.pack(fill=tk.X, pady=10)
            
            self.upgrade_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(options_frame, text="升级到最新版本", 
                           variable=self.upgrade_var).pack(side=tk.LEFT)
            
            self.user_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(options_frame, text="用户安装(无需管理员权限)", 
                           variable=self.user_var).pack(side=tk.LEFT)
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=15)
            
            ttk.Button(button_frame, text="🎯 开始安装", 
                      command=self.start_visual_install).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="📋 复制命令", 
                      command=self.copy_install_command).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="❌ 关闭", 
                      command=install_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"创建安装窗口失败: {str(e)}")

    def start_visual_install(self):
        """可视化安装库"""
        libraries = self.lib_entry.get().strip()
        if not libraries:
            messagebox.showwarning("警告", "请输入要安装的库名称")
            return
        
        # 创建进度窗口
        progress_window = tk.Toplevel(self.root)
        progress_window.title("安装进度")
        progress_window.geometry("400x200")
        progress_window.transient(self.root)
        
        main_frame = ttk.Frame(progress_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text=f"正在安装: {libraries}", font=('等线', 12, 'bold')).pack(pady=10)
        
        progress = ttk.Progressbar(main_frame, mode='indeterminate')
        progress.pack(fill=tk.X, pady=10)
        progress.start()
        
        output_text = scrolledtext.ScrolledText(main_frame, height=8, font=('Consolas', 9))
        output_text.pack(fill=tk.BOTH, expand=True)
        output_text.config(state=tk.DISABLED)
        
        def run_installation():
            try:
                # 构建pip命令
                cmd = [sys.executable, "-m", "pip", "install"]
                
                if self.upgrade_var.get():
                    cmd.append("--upgrade")
                
                if self.user_var.get():
                    cmd.append("--user")
                
                cmd.extend([
                    "-i", "https://pypi.tuna.tsinghua.edu.cn/simple/",
                    "--trusted-host", "pypi.tuna.tsinghua.edu.cn"
                ])
                
                cmd.extend(libraries.split())
                
                # 执行安装
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # 实时输出
                for line in process.stdout:
                    output_text.config(state=tk.NORMAL)
                    output_text.insert(tk.END, line)
                    output_text.see(tk.END)
                    output_text.config(state=tk.DISABLED)
                    progress_window.update()
                
                process.wait()
                
                # 安装完成
                progress.stop()
                progress.config(mode='determinate', value=100)
                
                if process.returncode == 0:
                    output_text.config(state=tk.NORMAL)
                    output_text.insert(tk.END, "\n\n✅ 安装成功！")
                    output_text.config(state=tk.DISABLED)
                else:
                    output_text.config(state=tk.NORMAL)
                    output_text.insert(tk.END, f"\n\n❌ 安装失败，返回码: {process.returncode}")
                    output_text.config(state=tk.DISABLED)
                    
            except Exception as e:
                output_text.config(state=tk.NORMAL)
                output_text.insert(tk.END, f"\n\n❌ 安装出错: {str(e)}")
                output_text.config(state=tk.DISABLED)
        
        # 在新线程中运行安装
        threading.Thread(target=run_installation, daemon=True).start()

    def quick_install_lib(self, lib_name):
        """快速安装常用库"""
        self.lib_entry.delete(0, tk.END)
        self.lib_entry.insert(0, lib_name)
        self.start_visual_install()

    def copy_install_command(self):
        """复制安装命令到剪贴板"""
        libraries = self.lib_entry.get().strip()
        if not libraries:
            messagebox.showwarning("警告", "请输入要安装的库名称")
            return
        
        cmd = f'pip install {libraries} -i https://pypi.tuna.tsinghua.edu.cn/simple/ --trusted-host pypi.tuna.tsinghua.edu.cn'
        
        if self.upgrade_var.get():
            cmd += " --upgrade"
        
        if self.user_var.get():
            cmd += " --user"
        
        pyperclip.copy(cmd)
        messagebox.showinfo("成功", "安装命令已复制到剪贴板")

    def package_to_exe(self):
        """一键打包为EXE文件 - 直接在系统终端中运行"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先打开或保存一个Python文件")
            return
        
        if self.current_file_type != "python":
            messagebox.showwarning("警告", "只能打包Python文件")
            return
        
        try:
            # 创建简单的选项窗口
            package_window = tk.Toplevel(self.root)
            package_window.title("一键打包为EXE")
            package_window.geometry("500x300")
            package_window.transient(self.root)
            
            # 主框架
            main_frame = ttk.Frame(package_window, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 说明文字
            info_text = """使用说明：
选择打包选项，将在系统终端中使用PyInstaller进行打包

注意：首次使用需要安装PyInstaller
运行命令：pip install pyinstaller
"""
            info_label = ttk.Label(main_frame, text=info_text, justify=tk.LEFT)
            info_label.pack(fill=tk.X, pady=(0, 10))
            
            # 选项框架
            options_frame = ttk.LabelFrame(main_frame, text="打包选项")
            options_frame.pack(fill=tk.X, pady=5)
            
            # 控制台选项
            console_frame = ttk.Frame(options_frame)
            console_frame.pack(fill=tk.X, pady=2)
            self.console_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(console_frame, text="显示控制台窗口", 
                           variable=self.console_var).pack(side=tk.LEFT)
            
            # 单文件选项
            single_frame = ttk.Frame(options_frame)
            single_frame.pack(fill=tk.X, pady=2)
            self.single_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(single_frame, text="打包为单个EXE文件", 
                           variable=self.single_var).pack(side=tk.LEFT)
            
            # 图标选项
            icon_frame = ttk.Frame(options_frame)
            icon_frame.pack(fill=tk.X, pady=2)
            ttk.Label(icon_frame, text="图标文件:").pack(side=tk.LEFT)
            self.icon_entry = ttk.Entry(icon_frame, width=30)
            self.icon_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
            self.icon_entry.insert(0, "./Resources/app.ico")
            ttk.Button(icon_frame, text="浏览", 
                      command=self.browse_icon).pack(side=tk.LEFT, padx=(5, 0))
            
            # 按钮框架
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            ttk.Button(button_frame, text="在终端中打包", 
                      command=self.start_terminal_package).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="安装PyInstaller", 
                      command=self.install_pyinstaller_terminal).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="关闭", 
                      command=package_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            messagebox.showerror("错误", f"创建打包窗口失败: {str(e)}")

    def start_terminal_package(self):
        """在系统终端中开始打包"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先打开或保存一个Python文件")
            return
        
        try:
            # 构建PyInstaller命令
            cmd = ["python.exe -m PyInstaller"]
            
            # 控制台选项
            if not self.console_var.get():
                cmd.append("--noconsole")
            
            # 单文件选项
            if self.single_var.get():
                cmd.append("--onefile")
            
            # 图标选项
            icon_file = self.icon_entry.get().strip()
            if icon_file and os.path.exists(icon_file):
                cmd.extend(["--icon", icon_file])
            
            # 添加文件
            cmd.append(os.path.basename(self.current_file))
            
            # 在文件所在目录打开终端并执行命令
            file_dir = os.path.dirname(self.current_file)
            self.run_command_in_terminal(cmd, f"打包文件: {os.path.basename(self.current_file)}", file_dir)
            
        except Exception as e:
            messagebox.showerror("错误", f"启动打包失败: {str(e)}")

    def install_pyinstaller_terminal(self):
        """在终端中安装PyInstaller"""
        pip_command = [
            sys.executable, "-m", "pip", "install",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple/",
            "--trusted-host", "pypi.tuna.tsinghua.edu.cn",
            "pyinstaller"
        ]
        self.run_command_in_terminal(pip_command, "安装PyInstaller")

    def run_command_in_terminal(self, command, description, work_dir=None):
        """在系统终端中运行命令"""
        try:
            if work_dir is None:
                work_dir = os.getcwd()
            
            # 确保目录存在
            if not os.path.exists(work_dir):
                work_dir = os.getcwd()
            
            # 根据平台构建终端命令
            if sys.platform == 'win32':
                # Windows - 使用PowerShell
                cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in command)
                full_command = f'powershell -NoExit -Command "cd \'{work_dir}\'; {cmd_str}; echo \'命令执行完毕，按任意键退出...\'; pause"'
                subprocess.Popen(full_command, shell=True)
                
            elif sys.platform == 'darwin':
                # macOS - 使用Terminal
                cmd_str = " ".join(command)
                applescript = f'''
                tell application "Terminal"
                    activate
                    do script "cd '{work_dir}' && {cmd_str} && echo '命令执行完毕，按任意键退出...' && read"
                end tell
                '''
                subprocess.Popen(['osascript', '-e', applescript])
                
            else:
                # Linux - 尝试多种终端
                cmd_str = " ".join(command)
                terminals = [
                    ('gnome-terminal', ['--', 'bash', '-c', f'cd "{work_dir}" && {cmd_str} && echo "命令执行完毕，按任意键退出..." && read']),
                    ('konsole', ['-e', 'bash', '-c', f'cd "{work_dir}" && {cmd_str} && echo "命令执行完毕，按任意键退出..." && read']),
                    ('xfce4-terminal', ['-x', 'bash', '-c', f'cd "{work_dir}" && {cmd_str} && echo "命令执行完毕，按任意键退出..." && read']),
                    ('xterm', ['-e', f'bash -c "cd \\"{work_dir}\\" && {cmd_str} && echo \\"命令执行完毕，按任意键退出...\\" && read"'])
                ]
                
                terminal_found = False
                for terminal, args in terminals:
                    try:
                        subprocess.Popen([terminal] + args)
                        terminal_found = True
                        break
                    except FileNotFoundError:
                        continue
                
                if not terminal_found:
                    # 使用系统默认终端
                    subprocess.Popen(['x-terminal-emulator', '-e', f'bash -c "cd \\"{work_dir}\\" && {cmd_str} && echo \\"命令执行完毕，按任意键退出...\\" && read"'])
            
            self.add_info_message(f"已在系统终端中启动: {description}", "success")
            
        except Exception as e:
            self.add_info_message(f"启动终端失败: {str(e)}", "error")
            messagebox.showerror("错误", f"无法在终端中运行命令: {str(e)}")

    def browse_icon(self):
        """浏览图标文件"""
        icon_file = filedialog.askopenfilename(
            filetypes=[("ICO files", "*.ico"), ("All files", "*.*")]
        )
        if icon_file:
            self.icon_entry.delete(0, tk.END)
            self.icon_entry.insert(0, icon_file)

    def open_chat(self):
        """打开AI聊天窗口"""
        try:
            chat_window = tk.Toplevel(self.root)
            chat_window.title("聚源仓AI助手-Version 1.0.4")
            chat_window.geometry("700x600")
            chat_window.transient(self.root)
            if os.path.exists("./Resources/app.ico"):
                chat_window.iconbitmap("./Resources/app.ico")
            
            # 设置当前代码上下文
            current_code = self.get_current_editor_content()
            current_type = self.current_file_type
                
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
            
            ttk.Label(toolbar, text="聚源仓AI助手-Version 1.0.4", font=('等线', 14, 'bold')).pack(side=tk.LEFT)
            
            # 功能按钮
            button_frame = ttk.Frame(toolbar)
            button_frame.pack(side=tk.RIGHT)
            
            ttk.Button(button_frame, text="分析代码", 
                      command=lambda: self.analyze_current_code(chat_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="优化建议", 
                      command=lambda: self.suggest_improvements(chat_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="解释代码", 
                      command=lambda: self.explain_current_code(chat_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="生成HTML", 
                      command=lambda: self.generate_html_template(chat_window)).pack(side=tk.LEFT, padx=2)
            
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
            welcome_msg = """欢迎使用AI智能编程助手！

我可以帮助您：
• 深度分析代码质量和性能
• 提供专业的优化建议
• 详细解释代码逻辑
• 调试和修复问题
• 教学编程概念和最佳实践
• 进行代码审查
• 生成HTML、CSS、JavaScript代码

请描述您的问题或需要帮助的代码部分。"""
            self.add_chat_message("AI", welcome_msg)
        except Exception as e:
            messagebox.showerror("错误", f"打开聊天窗口失败: {str(e)}")

    def analyze_current_code(self, chat_window):
        """分析当前代码"""
        current_code = self.get_current_editor_content()
            
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请分析当前编辑器的代码")
        self.add_chat_message("AI", "正在深度分析代码...")
        
        threading.Thread(target=self.analyze_code_thread, args=(current_code,), daemon=True).start()

    def suggest_improvements(self, chat_window):
        """获取改进建议"""
        current_code = self.get_current_editor_content()
            
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请为当前代码提供改进建议")
        self.add_chat_message("AI", "正在分析改进机会...")
        
        threading.Thread(target=self.suggest_improvements_thread, args=(current_code,), daemon=True).start()

    def explain_current_code(self, chat_window):
        """解释当前代码"""
        current_code = self.get_current_editor_content()
            
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请详细解释当前代码")
        self.add_chat_message("AI", "正在分析代码逻辑...")
        
        threading.Thread(target=self.explain_code_thread, args=(current_code,), daemon=True).start()

    def generate_html_template(self, chat_window):
        """生成HTML模板"""
        self.add_chat_message("你", "请生成一个完整的HTML模板")
        self.add_chat_message("AI", "正在生成HTML模板...")
        
        threading.Thread(target=self.generate_html_thread, daemon=True).start()

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

    def generate_html_thread(self):
        """生成HTML线程"""
        try:
            import ai_compiler
            response = ai_compiler.generate_html("生成一个完整的HTML5模板，包含基本的页面结构和样式")
            self.root.after(0, lambda: self.add_chat_message("AI", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("AI", f"生成HTML失败：{str(e)}"))

    def send_chat_message(self, chat_window):
        """发送聊天消息"""
        message = self.chat_input.get(1.0, tk.END).strip()
        if not message:
            return
            
        # 添加用户消息到聊天历史
        self.add_chat_message("你", message)
        
        # 清空输入框
        self.chat_input.delete(1.0, tk.END)
        
        # 检查API是否可用
        try:
            import ai_compiler
            if ai_compiler._global_compiler.client is None:
                self.add_chat_message("AI", "AI功能暂不可用，请检查API密钥设置")
                return
        except:
            self.add_chat_message("AI", "AI模块加载失败")
            return
        
        # 显示思考中消息
        self.add_chat_message("AI", "思考中...")
        
        # 获取当前代码上下文和文件类型
        current_content = self.get_current_editor_content()
        current_type = self.current_file_type
        
        # 在新线程中调用AI
        threading.Thread(target=self.chat_with_ai, args=(message, current_content, current_type), daemon=True).start()

    def chat_with_ai(self, message, code_context, file_type):
        """与AI对话，支持多种文件类型"""
        try:
            import ai_compiler
            
            # 根据文件类型调整提示
            if file_type == "html" and code_context:
                enhanced_message = f"当前正在编辑HTML文件，请优先提供HTML相关的帮助:\n\n{message}\n\n当前HTML内容:\n{code_context}"
            elif file_type == "markdown" and code_context:
                enhanced_message = f"当前正在编辑Markdown文件:\n\n{message}\n\n当前Markdown内容:\n{code_context}"
            else:
                enhanced_message = message
                
            response = ai_compiler.chat(enhanced_message, code_context)
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
        try:
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
        except Exception as e:
            print(f"添加聊天消息失败: {e}")

    def clear_chat(self):
        """清空聊天输入"""
        try:
            self.chat_input.delete(1.0, tk.END)
        except Exception as e:
            print(f"清空聊天输入失败: {e}")

    def insert_chat_code(self):
        """将聊天中的代码插入到编辑器"""
        try:
            # 获取聊天历史中最后一条AI消息
            ai_messages = [msg for msg in self.chat_history if msg["sender"] == "AI"]
            if not ai_messages:
                messagebox.showinfo("提示", "没有找到AI生成的代码")
                return
                
            last_ai_message = ai_messages[-1]["message"]
            
            # 提取代码块（支持多种语言）
            code_blocks = []
            patterns = [
                (r'```python\n(.*?)\n```', 'python'),
                (r'```html\n(.*?)\n```', 'html'),
                (r'```css\n(.*?)\n```', 'css'),
                (r'```javascript\n(.*?)\n```', 'javascript'),
                (r'```js\n(.*?)\n```', 'javascript')
            ]
            
            for pattern, lang in patterns:
                matches = re.findall(pattern, last_ai_message, re.DOTALL)
                for match in matches:
                    code_blocks.append((lang, match.strip()))
            
            if code_blocks:
                # 插入第一个代码块到编辑器
                lang, code = code_blocks[0]
                
                # 插入到代码编辑器
                self.code_text.insert(tk.END, f"\n\n# AI生成的{lang.upper()}代码\n{code}\n")
                    
                self.add_info_message(f"AI生成的{lang.upper()}代码已插入到编辑器中", "success")
                
                # 应用语法高亮
                if self.syntax_highlight_enabled:
                    self.apply_syntax_highlighting()
            else:
                messagebox.showinfo("提示", "未找到可插入的代码块")
        except Exception as e:
            messagebox.showerror("错误", f"插入代码失败: {str(e)}")

    def get_current_editor_content(self):
        """获取当前编辑器内容"""
        try:
            if hasattr(self, 'code_text') and self.code_text is not None:
                return self.code_text.get(1.0, tk.END).strip()
            return ""
        except Exception as e:
            print(f"获取编辑器内容失败: {e}")
            return ""

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
                if file.endswith('.py') or file.endswith('.txt') or file.endswith('.md') or file.endswith('.html') or file.endswith('.htm'):
                    file_path = os.path.join(path, file)
                    self.tree.insert(parent, tk.END, text=file, values=[file_path, 'file'])
                    
        except PermissionError:
            # 跳过没有权限的文件夹
            pass
        except Exception as e:
            print(f"加载目录错误: {e}")

    def on_tree_double_click(self, event):
        """处理树节点的双击事件"""
        try:
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
        except Exception as e:
            print(f"处理树节点双击事件失败: {e}")

    def load_subdirectory(self, parent_node, path):
        """加载子目录"""
        try:
            # 删除"加载中..."占位符
            children = self.tree.get_children(parent_node)
            for child in children:
                self.tree.delete(child)
            
            # 加载实际内容
            self.populate_tree(path, parent_node, deepth=1)
        except Exception as e:
            print(f"加载子目录失败: {e}")

    def open_file_from_tree(self, file_path):
        """从文件树打开文件"""
        try:
            # 根据文件扩展名确定文件类型
            if file_path.endswith('.py'):
                file_type = "python"
            elif file_path.endswith('.html') or file_path.endswith('.htm'):
                file_type = "html"
            elif file_path.endswith('.md') or file_path.endswith('.markdown'):
                file_type = "markdown"
            else:
                file_type = "python"  # 默认
            
            self.current_file = file_path
            self.current_file_type = file_type
            
            # 更新文件类型标签
            self.file_type_label.config(text=f"{file_type.upper()}文件: {os.path.basename(file_path)}")
            
            # 尝试不同编码读取文件
            encodings = ['utf-8', 'gbk', 'latin-1']
            content = ""
            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, content)
            
            # 应用语法高亮
            if self.syntax_highlight_enabled:
                self.apply_syntax_highlighting()
            
            # 在信息显示区域显示提示
            self.add_info_message(f"已打开文件: {file_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def refresh_tree(self):
        """刷新文件树"""
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.populate_tree(self.project_root)
        except Exception as e:
            print(f"刷新文件树失败: {e}")

    def open_folder(self):
        """打开文件夹"""
        try:
            folder_path = filedialog.askdirectory()
            if folder_path:
                self.project_root = folder_path
                self.refresh_tree()
        except Exception as e:
            messagebox.showerror("错误", f"打开文件夹失败: {str(e)}")

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
    def new_file(self, file_type="python"):
        """新建文件"""
        try:
            self.current_file = None
            self.current_file_type = file_type
            self.code_text.delete(1.0, tk.END)
            
            # 更新文件类型标签
            self.file_type_label.config(text=f"新建{file_type.upper()}文件")
            
            # 根据文件类型插入初始内容
            if file_type == "html":
                initial_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>新建HTML文档</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
        }
    </style>
</head>
<body>
    <h1>欢迎使用HTML编辑器</h1>
    <p>这是一个新的HTML文档。</p>
</body>
</html>"""
                self.code_text.insert(1.0, initial_content)
            elif file_type == "markdown":
                initial_content = """# 新建Markdown文档

欢迎使用Markdown编辑器！

## 功能特点
- 支持标准的Markdown语法
- 实时预览功能
- 代码高亮

## 开始编写
在这里输入您的Markdown内容..."""
                self.code_text.insert(1.0, initial_content)
            
            self.add_info_message(f"已创建新{file_type}文件")
            if self.syntax_highlight_enabled:
                self.apply_syntax_highlighting()
        except Exception as e:
            messagebox.showerror("错误", f"创建新文件失败: {str(e)}")

    def open_file(self):
        """打开文件"""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("Python Files", "*.py"),
                    ("HTML Files", "*.html;*.htm"),
                    ("Markdown Files", "*.md;*.markdown"),
                    ("Text Files", "*.txt"),
                    ("All Files", "*.*")
                ]
            )
            if file_path:
                self.open_file_from_tree(file_path)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")

    def save_file(self):
        """保存文件"""
        try:
            if self.current_file:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.code_text.get(1.0, tk.END))
                self.add_info_message(f"已保存文件: {self.current_file}", "success")
                return True
            else:
                return self.save_file_as()
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            return False

    def save_file_as(self):
        """另存为文件"""
        try:
            # 根据当前文件类型设置默认扩展名
            if self.current_file_type == "html":
                filetypes = [("HTML Files", "*.html"), ("All Files", "*.*")]
                defaultextension = ".html"
            elif self.current_file_type == "markdown":
                filetypes = [("Markdown Files", "*.md"), ("All Files", "*.*")]
                defaultextension = ".md"
            else:
                filetypes = [("Python Files", "*.py"), ("All Files", "*.*")]
                defaultextension = ".py"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=defaultextension, 
                filetypes=filetypes
            )
            if file_path:
                self.current_file = file_path
                # 根据文件扩展名更新文件类型
                if file_path.endswith('.html') or file_path.endswith('.htm'):
                    self.current_file_type = "html"
                elif file_path.endswith('.md') or file_path.endswith('.markdown'):
                    self.current_file_type = "markdown"
                else:
                    self.current_file_type = "python"
                
                self.file_type_label.config(text=f"{self.current_file_type.upper()}文件: {os.path.basename(file_path)}")
                
                return self.save_file()
            return False
        except Exception as e:
            messagebox.showerror("错误", f"另存为文件失败: {str(e)}")
            return False

    def show_about(self):
        about_text = """Python聚源仓项目，是一款AI智能编译器，目前支持Python、HTML、Markdown，制作团队基本都是学生。

功能特点：
• AI分析代码、优化代码、上下文理解
• 语法高亮显示
• 在系统终端中运行代码
• 文件管理功能
• 一键安装第三方库（清华源）
• 一键打包为EXE文件
• 单编辑器多文件类型支持
• HTML/Markdown文件支持
• 完全免费开源

语法高亮功能由backend引擎提供支持。"""
        messagebox.showinfo("关于", about_text)

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
                target_dir = self.project_root
            
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