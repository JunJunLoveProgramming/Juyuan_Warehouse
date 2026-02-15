try:
    from fix_encoding import fix_all_encoding
    fix_all_encoding()
except ImportError:
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
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lock_socket.bind(('localhost', 47294))
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
        self.root.title("聚源仓-Version 1.0.8")  # 更新版本号
        self.root.geometry("1200x800")
        
        if os.path.exists("./Resources/app.ico"):
            self.root.iconbitmap("./Resources/app.ico")
        
        # 初始化属性
        self.current_file = None
        self.current_file_type = "python"
        self.chat_history = []
        self.syntax_highlight_enabled = True
        self.project_root = os.getcwd()
        
        # 初始化组件
        self.info_text = None
        self.code_text = None
        self.file_type_label = None
        self.backend_processor = None
        self.toolbar = None
        self.main_container = None
        self.ai_panel = None
        self.right_click_menu = None
        self.main_content_container = None
        
        # VS Code界面新增组件
        self.menu_bar = None
        self.status_bar = None
        self.file_explorer = None
        self.terminal_panel = None
        
        # 流式响应相关
        self.streaming_response = ""
        
        # VS Code主题颜色配置 - 浅色主题
        self.vscode_theme = {
            'background': '#FFFFFF',
            'foreground': '#000000',
            'border': '#CCCCCC',
            'titlebar': '#F3F3F3',
            'toolbar': '#F3F3F3',
            'button': '#FFFFFF',
            'button_hover': '#E6E6E6',
            'editor_bg': '#FFFFFF',
            'editor_fg': '#000000',
            'panel_bg': '#F3F3F3',
            'input_bg': '#FFFFFF',
            'input_fg': '#000000',
            'scrollbar_bg': '#F3F3F3',
            'scrollbar_fg': '#CCCCCC',
            # 语法高亮颜色 - 浅色主题适配
            'keyword': '#0000FF',
            'string': '#A31515',
            'comment': '#008000',
            'function': '#795E26',
            'number': '#098658',
            'operator': '#000000',
            'class_name': '#2B91AF'
        }
        
        # 工具栏项目（移除文件资源管理器和终端相关功能）
        self.toolbar_items = [
            ("新建", './Resources/new.png', self.new_file_dialog),
            ("打开", './Resources/open.png', self.open_file),
            ("保存", './Resources/save.png', self.save_file),
            ("小源", './Resources/ai.png', self.toggle_ai_panel),
            ("运行", './Resources/run.png', self.run_current_file),
            ("Python专区", './Resources/open.png', self.show_python_zone),
            ("关于", './Resources/info.png', self.show_about)
        ]
        
        # 初始化后端和API
        self.setup_api_key()
        self.setup_backend()
        
        # 启动简化界面
        self.setup_simple_ui()
        
        # 显示欢迎消息
        self.show_welcome_message()

    def create_menu_bar(self):
        """创建VS Code风格的顶部菜单栏"""
        self.menu_bar = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=self.menu_bar)
        
        # 文件菜单
        file_menu = tk.Menu(self.menu_bar, tearoff=0,
                          bg=self.vscode_theme['toolbar'],
                          fg=self.vscode_theme['foreground'])
        file_menu.add_command(label="新建", command=self.new_file_dialog, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        self.menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 编辑菜单
        edit_menu = tk.Menu(self.menu_bar, tearoff=0,
                          bg=self.vscode_theme['toolbar'],
                          fg=self.vscode_theme['foreground'])
        edit_menu.add_command(label="撤销", command=lambda: self.code_text.edit_undo(), accelerator="Ctrl+Z")
        edit_menu.add_command(label="重做", command=lambda: self.code_text.edit_redo(), accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="复制", command=self.copy_text, accelerator="Ctrl+C")
        edit_menu.add_command(label="粘贴", command=self.paste_text, accelerator="Ctrl+V")
        edit_menu.add_command(label="剪切", command=self.cut_text, accelerator="Ctrl+X")
        edit_menu.add_separator()
        edit_menu.add_command(label="全选", command=self.select_all, accelerator="Ctrl+A")
        self.menu_bar.add_cascade(label="编辑", menu=edit_menu)
        
        # 运行菜单
        run_menu = tk.Menu(self.menu_bar, tearoff=0,
                         bg=self.vscode_theme['toolbar'],
                         fg=self.vscode_theme['foreground'])
        run_menu.add_command(label="运行当前文件", command=self.run_current_file, accelerator="F5")
        run_menu.add_command(label="运行选中代码", command=self.run_selected_code)
        self.menu_bar.add_cascade(label="运行", menu=run_menu)
        
        # Python专区菜单
        python_menu = tk.Menu(self.menu_bar, tearoff=0,
                            bg=self.vscode_theme['toolbar'],
                            fg=self.vscode_theme['foreground'])
        python_menu.add_command(label="Python专区", command=self.show_python_zone)
        self.menu_bar.add_cascade(label="Python专区", menu=python_menu)
        
        # 视图菜单
        view_menu = tk.Menu(self.menu_bar, tearoff=0,
                          bg=self.vscode_theme['toolbar'],
                          fg=self.vscode_theme['foreground'])
        view_menu.add_command(label="切换AI面板", command=self.toggle_ai_panel)
        self.menu_bar.add_cascade(label="视图", menu=view_menu)
        
        # 帮助菜单
        help_menu = tk.Menu(self.menu_bar, tearoff=0,
                          bg=self.vscode_theme['toolbar'],
                          fg=self.vscode_theme['foreground'])
        help_menu.add_command(label="关于", command=self.show_about)
        self.menu_bar.add_cascade(label="帮助", menu=help_menu)
        
        # 绑定快捷键
        self.root.bind("<Control-n>", lambda e: self.new_file_dialog())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-z>", lambda e: self.code_text.edit_undo())
        self.root.bind("<Control-y>", lambda e: self.code_text.edit_redo())
        self.root.bind("<Control-a>", lambda e: self.select_all())
        self.root.bind("<F5>", lambda e: self.run_current_file())
    
    def setup_api_key(self):
        """设置DeepSeek API密钥（主备双API）"""
        try:
            import ai_compiler
            
            primary_api_key = ""  # 主API
            backup_api_key = ""  # 备用API
            
            if (not primary_api_key or primary_api_key == "你的Deepseek API") and \
               (not backup_api_key or backup_api_key == "你的备用Deepseek API"):
                print("警告: 未设置有效的API密钥")
                return False
                
            success = ai_compiler.set_api_keys(primary_api_key, backup_api_key)
            if success:
                print("API密钥设置成功 - 主备双API模式")
                os.environ['DEEPSEEK_API_KEY'] = primary_api_key
                os.environ['DEEPSEEK_BACKUP_API_KEY'] = backup_api_key or ""
                return True
            else:
                print("API密钥设置失败，请检查密钥是否正确")
                return False
                
        except ImportError as e:
            print(f"导入ai_compiler失败: {e}")
            return False
        except Exception as e:
            print(f"设置API密钥失败: {e}")
            return False

    def get_api_key(self):
        """获取API密钥"""
        try:
            import ai_compiler
            return ai_compiler._global_compiler.primary_api_key
        except:
            return None

    def setup_backend(self):
        """初始化backend处理引擎"""
        try:
            self.backend_processor = backend.backEndprocessing()
            self.backend_processor.setTagKeyWord("keyword")
            print("Backend语法高亮引擎初始化成功")
        except Exception as e:
            print(f"Backend初始化失败: {e}")
            self.backend_processor = None

    def setup_simple_ui(self):
        """初始化VS Code风格界面"""
        try:
            # 清除现有界面
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # 应用VS Code主题到主窗口
            self.root.configure(background=self.vscode_theme['background'])
            
            # 创建顶部菜单栏
            # self.create_menu_bar()  # 移除菜单栏
            
            # 创建主布局容器
            main_frame = tk.Frame(self.root, 
                               bg=self.vscode_theme['background'])
            main_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # 创建内容区域分隔
            content_paned = tk.PanedWindow(main_frame, 
                                         orient=tk.HORIZONTAL, 
                                         sashrelief=tk.RAISED, 
                                         sashwidth=4,
                                         bg=self.vscode_theme['background'],
                                         bd=0,
                                         relief=tk.FLAT)
            content_paned.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
            
            # 中间编辑器区域
            editor_container = tk.Frame(content_paned, 
                                     bg=self.vscode_theme['background'])
            content_paned.add(editor_container, stretch='always')
            
            # 移除标签栏功能
            
            # 主编辑器区域
            self.setup_editor_area(editor_container)
            
            # 右侧AI面板
            self.setup_ai_panel(content_paned)
            
            # 设置初始分割比例 - 一半编辑器，一半小源
            self.root.update()
            content_paned.sash_place(0, int(content_paned.winfo_width() * 0.5), 0)
            
            # 创建状态栏
            self.create_status_bar()
            
            print("VS Code风格界面初始化完成")
            
        except Exception as e:
            print(f"UI初始化失败: {e}")
            # 创建紧急备用界面
            emergency_frame = ttk.Frame(self.root)
            emergency_frame.pack(fill=tk.BOTH, expand=True)
            self.code_text = scrolledtext.ScrolledText(emergency_frame, wrap=tk.WORD, font=("Consolas", 12))
            self.code_text.pack(fill=tk.BOTH, expand=True)

    def setup_editor_area(self, parent):
        """设置编辑器区域"""
        # ttk.Frame不支持直接设置background，需要通过style设置
        
        # 顶部工具栏
        self.toolbar = ttk.Frame(parent)
        self.toolbar.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        # 创建工具栏按钮
        self.create_toolbar_buttons()
        
        # 创建主内容区域容器
        self.main_content_container = ttk.Frame(parent)
        self.main_content_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 显示VS Code风格的启动界面
        self.show_vscode_startup_screen()
    
    def show_vscode_startup_screen(self):
        """显示VS Code风格的启动界面"""
        # 清空主内容区域
        for widget in self.main_content_container.winfo_children():
            widget.destroy()
        
        # 创建VS Code风格的启动界面 - 白色背景
        startup_frame = tk.Frame(self.main_content_container, bg="#FFFFFF")
        startup_frame.pack(fill=tk.BOTH, expand=True)
        
        # VS Code标题
        title_label = tk.Label(startup_frame, text="聚源仓", font=('Consolas', 24, 'bold'), fg="#000000", bg="#FFFFFF")
        title_label.pack(pady=(100, 10))
        
        subtitle_label = tk.Label(startup_frame, text="万物聚源 AI共生", font=('Consolas', 14), fg="#666666", bg="#FFFFFF")
        subtitle_label.pack(pady=(0, 50))
        
        # 启动选项列表
        options_frame = tk.Frame(startup_frame, bg="#FFFFFF")
        options_frame.pack()
        
        # 新建文件
        new_file_btn = tk.Button(options_frame, text="新建文件...", font=('Consolas', 12), fg="#0066CC", bg="#FFFFFF",
                                 relief=tk.FLAT, anchor=tk.W, width=25, command=self.new_file_from_startup)
        new_file_btn.pack(fill=tk.X, pady=(5, 5))
        
        # 打开文件
        open_file_btn = tk.Button(options_frame, text="打开文件...", font=('Consolas', 12), fg="#0066CC", bg="#FFFFFF",
                                 relief=tk.FLAT, anchor=tk.W, width=25, command=self.open_file_from_startup)
        open_file_btn.pack(fill=tk.X, pady=(5, 5))
            
    def new_file_from_startup(self, file_type="txt"):
        """从启动界面创建新文件"""
        # 显示编辑器界面
        self.show_editor_screen()
        # 创建新文件
        self.new_file(file_type)
    
    def open_file_from_startup(self):
        """从启动界面打开文件"""
        # 先打开文件选择对话框
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
            # 如果用户选择了文件，才显示编辑器界面并打开文件
            self.show_editor_screen()
            self.open_file_from_path(file_path)
    
    def open_folder_from_startup(self):
        """从启动界面打开文件夹"""
        # 显示编辑器界面
        self.show_editor_screen()
        # 这里可以添加打开文件夹的逻辑
        messagebox.showinfo("提示", "打开文件夹功能开发中")
    
    def create_toolbar_buttons(self):
        """创建工具栏按钮"""
        # 批量注册工具栏项目
        self.image = []

        if os.path.exists('./Resources/app.jpg'):
            try:
                img = Image.open('./Resources/app.jpg')
                img = img.resize((60, 60))
                self.image.append(ImageTk.PhotoImage(img))
                tk.Button(self.toolbar, image=self.image[0], relief="flat", command=self.hidden_easter_egg,
                         bg=self.vscode_theme['toolbar']).pack(side='left')
            except Exception as e:
                print(f"加载logo图片失败: {e}")
                
        for name, icon, command in self.toolbar_items:
            try:
                if name == "Python专区":
                    if not self.current_file or not self.current_file.endswith('.py'):
                        continue
                if icon is not None and os.path.exists(icon):
                    ico = Image.open(icon).resize((30, 30))
                    self.image.append(ImageTk.PhotoImage(ico))
                    tk.Button(self.toolbar, text=name, command=command, font=('Consolas', 10),
                              relief='flat', image=self.image[-1], compound='top',
                              bg=self.vscode_theme['toolbar'],
                              fg=self.vscode_theme['foreground'],
                              activebackground=self.vscode_theme['button_hover'],
                              activeforeground=self.vscode_theme['foreground']).pack(side=tk.LEFT, padx=2, pady=2)
                else:
                    tk.Button(self.toolbar, text=name, command=command, font=('Consolas', 10),
                              relief='flat',
                              bg=self.vscode_theme['toolbar'],
                              fg=self.vscode_theme['foreground'],
                              activebackground=self.vscode_theme['button_hover'],
                              activeforeground=self.vscode_theme['foreground']).pack(side=tk.LEFT, padx=2, pady=2)
            except Exception as e:
                print(f"加载工具栏按钮失败 {name}: {e}")
                tk.Button(self.toolbar, text=name, command=command, font=('Consolas', 10),
                          relief='flat',
                          bg=self.vscode_theme['toolbar'],
                          fg=self.vscode_theme['foreground'],
                          activebackground=self.vscode_theme['button_hover'],
                          activeforeground=self.vscode_theme['foreground']).pack(side=tk.LEFT, padx=2, pady=2)
    
    def refresh_toolbar(self):
        """刷新工具栏以显示/隐藏Python专区按钮"""
        if self.toolbar and hasattr(self, 'code_text') and self.code_text:
            for widget in self.toolbar.winfo_children():
                widget.destroy()
            self.create_toolbar_buttons()
    
    def show_editor_screen(self):
        """显示编辑器界面"""
        # 清空主内容区域
        for widget in self.main_content_container.winfo_children():
            widget.destroy()
        
        # 创建编辑器容器
        editor_container = ttk.Frame(self.main_content_container)
        editor_container.pack(fill=tk.BOTH, expand=True)
        
        # 创建代码编辑器
        self.code_text = scrolledtext.ScrolledText(
            editor_container,
            wrap=tk.WORD,
            font=("Consolas", 12),
            bg=self.vscode_theme['editor_bg'],
            fg=self.vscode_theme['editor_fg'],
            insertbackground=self.vscode_theme['foreground'],
            selectbackground="#264F78",
            selectforeground=self.vscode_theme['foreground'],
            bd=1,
            relief=tk.SOLID,
            highlightbackground=self.vscode_theme['border']
        )
        self.code_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置VS Code风格语法高亮
        self.code_text.tag_configure("keyword", foreground=self.vscode_theme['keyword'], font=('Consolas', 12, "bold"))
        self.code_text.tag_configure("string", foreground=self.vscode_theme['string'])
        self.code_text.tag_configure("comment", foreground=self.vscode_theme['comment'], font=('Consolas', 11, "italic"))
        self.code_text.tag_configure("function", foreground=self.vscode_theme['function'])
        self.code_text.tag_configure("number", foreground=self.vscode_theme['number'])
        self.code_text.tag_configure("operator", foreground=self.vscode_theme['operator'])
        self.code_text.tag_configure("class_name", foreground=self.vscode_theme['class_name'], font=('Consolas', 12, "bold"))
        
        # 绑定事件
        self.code_text.bind("<KeyRelease>", self.on_code_change)
        
        # 添加右键菜单
        self.setup_right_click_menu()

    def setup_right_click_menu(self):
        """设置右键菜单"""
        # 创建右键菜单
        self.right_click_menu = tk.Menu(self.code_text, tearoff=0)
        
        # 添加菜单项
        self.right_click_menu.add_command(label="复制", command=self.copy_text)
        self.right_click_menu.add_command(label="粘贴", command=self.paste_text)
        self.right_click_menu.add_command(label="剪切", command=self.cut_text)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="全选", command=self.select_all)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="运行选中代码", command=self.run_selected_code)
        self.right_click_menu.add_command(label="小源分析选中代码", command=self.analyze_selected_code)
        self.right_click_menu.add_separator()
        self.right_click_menu.add_command(label="注释/取消注释", command=self.toggle_comment)
        
        # 绑定右键点击事件
        self.code_text.bind("<Button-3>", self.show_right_click_menu)  # Button-3 是右键

    def show_right_click_menu(self, event):
        """显示右键菜单"""
        try:
            self.right_click_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.right_click_menu.grab_release()

    def copy_text(self):
        """复制文本"""
        try:
            selected_text = self.code_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
        except tk.TclError:
            # 没有选中文本
            pass

    def paste_text(self):
        """粘贴文本"""
        try:
            clipboard_text = self.root.clipboard_get()
            self.code_text.insert(tk.INSERT, clipboard_text)
        except tk.TclError:
            pass

    def cut_text(self):
        """剪切文本"""
        try:
            selected_text = self.code_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.code_text.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except tk.TclError:
            # 没有选中文本
            pass

    def select_all(self):
        """全选文本"""
        self.code_text.tag_add(tk.SEL, "1.0", tk.END)
        self.code_text.mark_set(tk.INSERT, "1.0")
        self.code_text.see(tk.INSERT)

    def run_selected_code(self):
        """运行选中的代码"""
        try:
            selected_text = self.code_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                # 创建临时文件运行选中的代码
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                    f.write(selected_text)
                    temp_file = f.name
                
                # 在终端中运行
                if sys.platform == 'win32':
                    cmd = f'start cmd /K "python \"{temp_file}\" && pause && del \"{temp_file}\""'
                    subprocess.Popen(cmd, shell=True)
                else:
                    cmd = f'python3 "{temp_file}"'
                    if sys.platform == 'darwin':  # macOS
                        applescript = f'''
                        tell application "Terminal"
                            activate
                            do script "{cmd} && echo '程序执行完毕，按任意键退出...' && read && rm \"{temp_file}\""
                        end tell
                        '''
                        subprocess.Popen(['osascript', '-e', applescript])
                    else:  # Linux
                        subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'{cmd} && echo "程序执行完毕，按任意键退出..." && read && rm "{temp_file}"'])
                
                self.show_info_message("正在运行选中代码...")
            else:
                self.show_info_message("请先选择要运行的代码")
        except Exception as e:
            self.show_info_message(f"运行选中代码失败: {str(e)}", "error")

    def analyze_selected_code(self):
        """AI分析选中的代码"""
        try:
            selected_text = self.code_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text:
                self.add_chat_message("你", "请分析以下代码：\n" + selected_text)
                threading.Thread(target=self.analyze_code_thread, 
                               args=(selected_text,), daemon=True).start()
            else:
                self.show_info_message("请先选择要分析的代码")
        except Exception as e:
            self.show_info_message(f"分析代码失败: {str(e)}", "error")

    def toggle_comment(self):
        """注释/取消注释选中的代码"""
        try:
            selected_text = self.code_text.get(tk.SEL_FIRST, tk.SEL_LAST)
            if not selected_text:
                return
            
            lines = selected_text.split('\n')
            all_commented = all(line.strip().startswith('#') for line in lines if line.strip())
            
            new_lines = []
            for line in lines:
                if all_commented:
                    # 取消注释
                    if line.strip().startswith('#') and line.strip()[1:].strip():
                        new_lines.append(line.replace('#', '', 1))
                    else:
                        new_lines.append(line)
                else:
                    # 添加注释
                    if line.strip():
                        new_lines.append('# ' + line)
                    else:
                        new_lines.append(line)
            
            new_text = '\n'.join(new_lines)
            
            # 替换选中的文本
            self.code_text.delete(tk.SEL_FIRST, tk.SEL_LAST)
            self.code_text.insert(tk.SEL_FIRST, new_text)
            
        except tk.TclError:
            # 没有选中文本
            pass

    def create_file_explorer(self, parent):
        """创建左侧文件资源管理器"""
        # 创建文件资源管理器容器
        explorer_frame = tk.Frame(parent, 
                               bg=self.vscode_theme['panel_bg'],
                               bd=1,
                               relief=tk.SOLID)
        parent.add(explorer_frame, stretch='never', width=250)
        
        # 标题栏
        explorer_header = tk.Frame(explorer_frame, 
                                bg=self.vscode_theme['toolbar'],
                                height=30)
        explorer_header.pack(fill=tk.X, side=tk.TOP)
        
        tk.Label(explorer_header, text="文件资源管理器", font=('Consolas', 10, 'bold'),
                bg=self.vscode_theme['toolbar'],
                fg=self.vscode_theme['foreground']).pack(side=tk.LEFT, padx=10, pady=5)
        
        # 刷新按钮
        refresh_btn = tk.Button(explorer_header, text="↻", font=('Consolas', 10),
                              bg=self.vscode_theme['toolbar'],
                              fg=self.vscode_theme['foreground'],
                              relief='flat',
                              command=self.refresh_file_explorer,
                              width=3)
        refresh_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 文件列表区域
        file_list_container = tk.Frame(explorer_frame, 
                                     bg=self.vscode_theme['panel_bg'])
        file_list_container.pack(fill=tk.BOTH, expand=True)
        
        # 项目根目录标签
        root_label = tk.Label(file_list_container, text=f"📁 {os.path.basename(self.project_root)}",
                            font=('Consolas', 10, 'bold'),
                            bg=self.vscode_theme['panel_bg'],
                            fg=self.vscode_theme['foreground'])
        root_label.pack(fill=tk.X, padx=10, pady=5)
        
        # 文件列表树
        self.file_explorer = scrolledtext.ScrolledText(
            file_list_container,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.vscode_theme['panel_bg'],
            fg=self.vscode_theme['foreground'],
            bd=0,
            relief=tk.FLAT
        )
        self.file_explorer.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始加载文件列表
        self.refresh_file_explorer()
    
    def refresh_file_explorer(self):
        """刷新文件资源管理器中的文件列表"""
        if not self.file_explorer:
            return
            
        # 清空文件列表
        self.file_explorer.delete(1.0, tk.END)
        
        # 遍历项目目录
        def traverse_directory(path, level=0):
            try:
                items = os.listdir(path)
                items.sort()
                
                for item in items:
                    # 跳过隐藏文件和目录
                    if item.startswith('.'):
                        continue
                    
                    item_path = os.path.join(path, item)
                    indent = '  ' * level
                    
                    if os.path.isdir(item_path):
                        self.file_explorer.insert(tk.END, f"{indent}📁 {item}\n", "directory")
                        traverse_directory(item_path, level + 1)
                    else:
                        self.file_explorer.insert(tk.END, f"{indent}📄 {item}\n", "file")
            except PermissionError:
                pass
        
        # 配置标签样式
        self.file_explorer.tag_configure("directory", foreground="#608B4E", font=('Consolas', 10, 'bold'))
        self.file_explorer.tag_configure("file", foreground=self.vscode_theme['foreground'])
        
        # 开始遍历
        traverse_directory(self.project_root)
    
    def create_terminal_panel(self):
        """创建底部终端区域"""
        # 创建终端面板容器
        terminal_frame = tk.Frame(self.root, 
                               bg=self.vscode_theme['panel_bg'],
                               bd=1,
                               relief=tk.SOLID,
                               height=200)
        terminal_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 终端标题栏
        terminal_header = tk.Frame(terminal_frame, 
                                bg=self.vscode_theme['toolbar'],
                                height=25)
        terminal_header.pack(fill=tk.X, side=tk.TOP)
        
        tk.Label(terminal_header, text="终端", font=('等线', 10, 'bold'),
                bg=self.vscode_theme['toolbar'],
                fg=self.vscode_theme['foreground']).pack(side=tk.LEFT, padx=10, pady=5)
        
        # 关闭按钮
        close_btn = tk.Button(terminal_header, text="×", font=('等线', 8),
                            bg=self.vscode_theme['toolbar'],
                            fg=self.vscode_theme['foreground'],
                            relief='flat',
                            width=2,
                            command=lambda: terminal_frame.pack_forget())
        close_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 终端输出区域
        self.terminal_panel = scrolledtext.ScrolledText(
            terminal_frame,
            wrap=tk.WORD,
            font=('Consolas', 10),
            bg=self.vscode_theme['editor_bg'],
            fg=self.vscode_theme['foreground'],
            bd=0,
            relief=tk.FLAT
        )
        self.terminal_panel.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # 初始显示终端信息
        self.terminal_panel.insert(tk.END, f"PS {self.project_root}> ", "prompt")
        
        # 配置标签样式
        self.terminal_panel.tag_configure("prompt", foreground="#4EC9B0", font=('Consolas', 10, 'bold'))
    
    def create_status_bar(self):
        """创建底部状态栏"""
        # 创建状态栏容器
        self.status_bar = tk.Frame(self.root, 
                               bg=self.vscode_theme['toolbar'],
                               height=25,
                               bd=1,
                               relief=tk.SOLID)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 左侧信息：欢迎信息
        self.file_type_label = tk.Label(self.status_bar, text="欢迎界面", font=('Consolas', 9),
                                      bg=self.vscode_theme['toolbar'],
                                      fg=self.vscode_theme['foreground'])
        self.file_type_label.pack(side=tk.LEFT, padx=10, pady=5)
                
        # 右侧信息：版本号
        self.version_label = tk.Label(self.status_bar, text="聚源仓 Version 1.0.8", font=('Consolas', 9),
                                   bg=self.vscode_theme['toolbar'],
                                   fg=self.vscode_theme['foreground'])
        self.version_label.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def save_file_as(self):
        """文件另存为"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Python文件", "*.py"), ("HTML文件", "*.html"), ("Markdown文件", "*.md"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.current_file = file_path
            return self.save_file()
        return False
    
    def setup_ai_panel(self, parent):
        """设置右侧AI面板"""
        # 创建主AI面板容器
        self.ai_panel = tk.Frame(parent,
                              bg=self.vscode_theme['panel_bg'],
                              bd=1,
                              relief=tk.SOLID)
        
        # AI面板标题
        ai_header = ttk.Frame(self.ai_panel)
        ai_header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(ai_header, text="小源\nVersion1.0.8", font=('Consolas', 14, 'bold'),
                bg=self.vscode_theme['panel_bg'],
                fg=self.vscode_theme['foreground']).pack()
        
        # 隐藏/显示AI面板按钮
        self.toggle_ai_btn = ttk.Button(ai_header, text="◀", width=3, command=self.toggle_ai_panel)
        self.toggle_ai_btn.pack(side=tk.RIGHT)
        
        # 聊天区域 - 占据大部分空间
        chat_frame = ttk.Frame(self.ai_panel)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # 聊天历史显示 - 占据主要区域
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            font=("Consolas", 10),
            bg=self.vscode_theme['input_bg'],
            fg=self.vscode_theme['input_fg'],
            insertbackground=self.vscode_theme['foreground'],
            selectbackground="#264F78",
            selectforeground=self.vscode_theme['foreground'],
            bd=1,
            relief=tk.SOLID
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # 输入区域 - 放在底部
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=10)
        
        self.quick_chat_input = ttk.Entry(input_frame, font=('Consolas', 10))
        self.quick_chat_input.pack(fill=tk.X, padx=(0, 5), side=tk.LEFT, expand=True)
        self.quick_chat_input.bind("<Return>", self.send_quick_chat)
        
        send_btn = ttk.Button(input_frame, text="发送", command=self.send_quick_chat)
        send_btn.pack(side=tk.RIGHT)
        
        # 显示欢迎消息
        welcome_msg = """欢迎使用小源！

我可以帮助您：
• 深度分析代码质量和性能
• 提供专业的优化建议
• 详细解释代码逻辑
• 调试和修复问题
• 进行代码审查
• 生成HTML、CSS、JavaScript代码
• 一键打包Python程序为exe
• 一键安装第三方库
• 打开系统终端
• 设置主备双API密钥（新增功能）
• 自动生成和编译代码，直到正常工作（新增功能）

请描述您的问题或需要帮助的代码部分。"""
        self.add_chat_message("小源", welcome_msg)
        
        # 将AI面板添加到父容器，设置为可拉伸
        parent.add(self.ai_panel, stretch='always')

    def setup_api_dialog(self):
        """打开API设置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("设置DeepSeek API密钥")
        dialog.geometry("500x300")
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="DeepSeek API密钥设置", 
                 font=('等线', 14, 'bold')).pack(pady=10)
        
        # 主API
        ttk.Label(main_frame, text="主API密钥:").pack(anchor='w', pady=(10, 5))
        primary_api_entry = ttk.Entry(main_frame, width=50, show="*")
        primary_api_entry.pack(fill=tk.X, pady=5)
        
        # 备用API
        ttk.Label(main_frame, text="备用API密钥 (可选):").pack(anchor='w', pady=(10, 5))
        backup_api_entry = ttk.Entry(main_frame, width=50, show="*")
        backup_api_entry.pack(fill=tk.X, pady=5)
        
        # 说明文字
        help_text = """说明：
• 主API密钥：必须填写，用于主要的AI功能
• 备用API密钥：可选，当主API出现问题时自动切换
• 获取API密钥：访问 https://platform.deepseek.com/
• 密钥安全：密钥仅保存在本地，不会上传到服务器"""
        
        help_label = tk.Label(main_frame, text=help_text, font=('等线', 9),
                             justify=tk.LEFT, foreground="gray")
        help_label.pack(anchor='w', pady=10)
        
        def save_api_keys():
            primary_key = primary_api_entry.get().strip()
            backup_key = backup_api_entry.get().strip()
            
            if not primary_key:
                messagebox.showwarning("警告", "请输入主API密钥")
                return
            
            try:
                import ai_compiler
                success = ai_compiler.set_api_keys(primary_key, backup_key)
                if success:
                    messagebox.showinfo("成功", "API密钥设置成功")
                    dialog.destroy()
                    # 更新环境变量
                    os.environ['DEEPSEEK_API_KEY'] = primary_key
                    if backup_key:
                        os.environ['DEEPSEEK_BACKUP_API_KEY'] = backup_key
                else:
                    messagebox.showerror("错误", "API密钥设置失败，请检查密钥是否正确")
            except Exception as e:
                messagebox.showerror("错误", f"设置API密钥失败: {str(e)}")
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="保存", command=save_api_keys).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 如果已有API密钥，预填充
        current_api = self.get_api_key()
        if current_api and current_api != "你的Deepseek API":
            primary_api_entry.insert(0, current_api)

    def toggle_ai_panel(self):
        """切换AI面板显示/隐藏"""
        if not hasattr(self, 'ai_panel') or not self.ai_panel:
            return
            
        try:
            parent = self.ai_panel.master
            if self.ai_panel.winfo_ismapped():
                # 隐藏AI面板
                parent.remove(self.ai_panel)
                self.toggle_ai_btn.config(text="▶")
            else:
                # 显示AI面板
                parent.add(self.ai_panel, stretch='always')
                self.toggle_ai_btn.config(text="◀")
                # 恢复分割比例 - 一半编辑器，一半小源
                self.root.update()
                parent.sash_place(0, int(parent.winfo_width() * 0.5), 0)
        except Exception as e:
            print(f"切换AI面板失败: {e}")

    def show_welcome_message(self):
        """显示欢迎消息"""
        # 只有当code_text组件存在时才显示欢迎消息
        if hasattr(self, 'code_text') and self.code_text is not None:
            welcome_code = '''# 欢迎使用聚源仓 AI IDE！

# 这是一个智能代码编辑器，支持：
# • Python、HTML、Markdown等多种语言
# • AI智能代码分析和生成
# • 语法高亮显示
# • 一键运行代码
# • 一键打包为exe文件
# • 一键安装第三方库
# • 打开系统终端
# • 右键菜单操作
# • 主备双API支持

# 开始编辑您的代码或与小源AI助手交流！
'''        
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, welcome_code)
            self.apply_syntax_highlighting()

    def on_code_change(self, event=None):
        """当代码内容改变时触发的函数"""
        try:
            if (self.syntax_highlight_enabled and self.backend_processor and 
                hasattr(self, 'code_text') and self.code_text is not None):
                self.apply_syntax_highlighting()
        except Exception as e:
            print(f"代码变更处理失败: {e}")

    def apply_syntax_highlighting(self):
        """应用语法高亮"""
        if not hasattr(self, 'code_text') or self.code_text is None:
            return
            
        try:
            # 获取当前文本
            text_content = self.code_text.get("1.0", "end-1c")
            
            # 移除所有现有标签
            self.code_text.tag_remove("keyword", "1.0", "end")
            self.code_text.tag_remove("string", "1.0", "end")
            self.code_text.tag_remove("comment", "1.0", "end")
            self.code_text.tag_remove("function", "1.0", "end")
            self.code_text.tag_remove("number", "1.0", "end")
            self.code_text.tag_remove("operator", "1.0", "end")
            self.code_text.tag_remove("class_name", "1.0", "end")
            
            # 自动检测文件类型并应用语法高亮
            if self.detect_file_type(text_content) == "python":
                # 使用backend_processor处理关键字
                if self.backend_processor:
                    self.backend_processor.insertColorTag(text_content, self.code_text)
                
                # 增强的语法高亮：字符串
                self._highlight_strings(text_content)
                
                # 增强的语法高亮：注释
                self._highlight_comments(text_content)
                
                # 增强的语法高亮：函数定义
                self._highlight_functions(text_content)
                
                # 增强的语法高亮：数字
                self._highlight_numbers(text_content)
                
                # 增强的语法高亮：类定义
                self._highlight_classes(text_content)
            
        except Exception as e:
            print(f"语法高亮错误: {e}")
    
    def _highlight_strings(self, text):
        """高亮字符串"""
        # 匹配单引号和双引号字符串
        string_pattern = r'"[^"]*"|\'[^\']*\''
        matches = re.finditer(string_pattern, text, re.DOTALL)
        for match in matches:
            start_line = text[:match.start()].count('\n') + 1
            start_col = match.start() - text[:match.start()].rfind('\n') - 1
            end_line = text[:match.end()].count('\n') + 1
            end_col = match.end() - text[:match.end()].rfind('\n') - 1
            
            self.code_text.tag_add("string", f"{start_line}.{start_col}", f"{end_line}.{end_col}")
    
    def _highlight_comments(self, text):
        """高亮注释"""
        # 匹配单行注释
        comment_pattern = r'#.*$'
        matches = re.finditer(comment_pattern, text, re.MULTILINE)
        for match in matches:
            start_line = text[:match.start()].count('\n') + 1
            start_col = match.start() - text[:match.start()].rfind('\n') - 1
            end_line = text[:match.end()].count('\n') + 1
            end_col = match.end() - text[:match.end()].rfind('\n') - 1
            
            self.code_text.tag_add("comment", f"{start_line}.{start_col}", f"{end_line}.{end_col}")
    
    def _highlight_functions(self, text):
        """高亮函数定义"""
        # 匹配def函数定义
        function_pattern = r'def\s+(\w+)\s*\('
        matches = re.finditer(function_pattern, text)
        for match in matches:
            # 提取函数名部分
            func_name_start = match.start(1)
            func_name_end = match.end(1)
            
            start_line = text[:func_name_start].count('\n') + 1
            start_col = func_name_start - text[:func_name_start].rfind('\n') - 1
            end_line = text[:func_name_end].count('\n') + 1
            end_col = func_name_end - text[:func_name_end].rfind('\n') - 1
            
            self.code_text.tag_add("function", f"{start_line}.{start_col}", f"{end_line}.{end_col}")
    
    def _highlight_numbers(self, text):
        """高亮数字"""
        # 匹配整数和浮点数
        number_pattern = r'\b\d+(\.\d+)?\b'
        matches = re.finditer(number_pattern, text)
        for match in matches:
            start_line = text[:match.start()].count('\n') + 1
            start_col = match.start() - text[:match.start()].rfind('\n') - 1
            end_line = text[:match.end()].count('\n') + 1
            end_col = match.end() - text[:match.end()].rfind('\n') - 1
            
            self.code_text.tag_add("number", f"{start_line}.{start_col}", f"{end_line}.{end_col}")
    
    def _highlight_classes(self, text):
        """高亮类定义"""
        # 匹配class定义
        class_pattern = r'class\s+(\w+)\s*'
        matches = re.finditer(class_pattern, text)
        for match in matches:
            # 提取类名部分
            class_name_start = match.start(1)
            class_name_end = match.end(1)
            
            start_line = text[:class_name_start].count('\n') + 1
            start_col = class_name_start - text[:class_name_start].rfind('\n') - 1
            end_line = text[:class_name_end].count('\n') + 1
            end_col = class_name_end - text[:class_name_end].rfind('\n') - 1
            
            self.code_text.tag_add("class_name", f"{start_line}.{start_col}", f"{end_line}.{end_col}")

    def detect_file_type(self, content):
        """自动检测文件类型"""
        if self.current_file:
            if self.current_file.endswith('.py'):
                return "python"
            elif self.current_file.endswith('.html') or self.current_file.endswith('.htm'):
                return "html"
            elif self.current_file.endswith('.md') or self.current_file.endswith('.markdown'):
                return "markdown"
        
        # 通过内容分析文件类型
        if re.search(r'<!DOCTYPE html|<\s*html|<\s*head|<\s*body', content, re.IGNORECASE):
            return "html"
        elif re.search(r'^#+ |^\* |^\- |^```', content, re.MULTILINE):
            return "markdown"
        elif re.search(r'^(import|def|class|print)\s', content, re.MULTILINE):
            return "python"
        else:
            return "python"  # 默认

    def run_current_file(self):
        """运行当前文件"""
        if not self.current_file:
            messagebox.showwarning("警告", "请先打开或保存一个文件")
            return
        
        file_type = self.detect_file_type(self.get_current_editor_content())
        
        if file_type == "python":
            self.run_python_file()
        elif file_type == "html":
            self.run_html_file()
        else:
            messagebox.showinfo("提示", f"不支持运行 {file_type} 文件")

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
            
            if sys.platform == 'win32':
                # Windows系统
                try:
                    cmd = f'start powershell -NoExit -Command "cd \'{file_dir}\'; python \'{file_name}\'; echo \'程序执行完毕，按任意键退出...\'; pause"'
                    subprocess.Popen(cmd, shell=True)
                    self.show_info_message("已在PowerShell中启动程序")
                except Exception as e:
                    try:
                        cmd = f'start cmd /K "cd /d \"{file_dir}\" && python \"{file_name}\" && pause"'
                        subprocess.Popen(cmd, shell=True)
                        self.show_info_message("已在命令提示符中启动程序")
                    except Exception as e2:
                        self.show_info_message(f"启动终端失败: {str(e2)}", "error")
            else:
                # 非Windows系统
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
                        subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', f'cd "{file_dir}" && python3 "{file_name}" && echo "程序执行完毕，按任意键退出..." && read'])
                    
                    self.show_info_message("已在系统终端中启动程序")
                except Exception as e:
                    self.show_info_message(f"启动终端失败: {str(e)}", "error")
                    
        except Exception as e:
            self.show_info_message(f"运行失败: {str(e)}", "error")

    def run_html_file(self):
        """运行HTML文件"""
        # HTML文件需要先保存
        if not self.save_file():
            messagebox.showwarning("警告", "请先保存HTML文件")
            return
        
        try:
            # 在系统默认浏览器中打开HTML文件
            webbrowser.open(f'file://{self.current_file}')
            self.show_info_message("已在浏览器中打开HTML文件")
        except Exception as e:
            self.show_info_message(f"打开HTML文件失败: {str(e)}", "error")

    def show_info_message(self, message, message_type="info"):
        """显示信息消息"""
        if message_type == "error":
            messagebox.showerror("信息", message)
        else:
            messagebox.showinfo("信息", message)

    # === 新增功能：一键打包exe ===
    def package_to_exe(self):
        """一键打包当前Python文件为exe"""
        if not self.current_file or not self.current_file.endswith('.py'):
            messagebox.showwarning("警告", "请先打开或保存一个Python文件")
            return
        
        # 确认打包
        if not messagebox.askyesno("确认", "确定要将当前Python文件打包为exe吗？"):
            return
        
        try:
            # 保存当前文件
            self.save_file()
            
            # 获取文件信息
            file_dir = os.path.dirname(self.current_file)
            file_name = os.path.basename(self.current_file)
            exe_name = os.path.splitext(file_name)[0]
            
            # 构建打包命令
            if sys.platform == 'win32':
                # Windows系统
                cmd = f'python.exe -m PyInstaller --onefile --windowed --name "{exe_name}" "{self.current_file}"'
                terminal_cmd = f'start cmd /K "cd /d "{file_dir}" && {cmd} && echo 打包完成！ && pause"'
            else:
                # Linux/Mac系统
                cmd = f'pyinstaller --onefile --windowed --name "{exe_name}" "{self.current_file}"'
                if sys.platform == 'darwin':  # macOS
                    applescript = f'''
                    tell application "Terminal"
                        activate
                        do script "cd '{file_dir}' && {cmd} && echo '打包完成！' && read"
                    end tell
                    '''
                    terminal_cmd = ['osascript', '-e', applescript]
                else:  # Linux
                    terminal_cmd = ['gnome-terminal', '--', 'bash', '-c', f'cd "{file_dir}" && {cmd} && echo "打包完成！" && read']
            
            # 在终端中执行打包命令
            if sys.platform == 'win32':
                subprocess.Popen(terminal_cmd, shell=True)
            else:
                subprocess.Popen(terminal_cmd)
            
            self.show_info_message("已在终端中启动打包过程，请稍候...")
            
        except Exception as e:
            self.show_info_message(f"打包失败: {str(e)}", "error")

    # === 新增功能：一键安装第三方库 ===
    def install_library_dialog(self):
        """打开安装库的对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("安装第三方库")
        dialog.geometry("400x350")
        dialog.resizable(False,False)
        dialog.iconbitmap("./Resources/app.ico")
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="输入要安装的库名（多个库用空格分隔）:", 
                font=('等线', 12)).pack(pady=10)
        
        library_entry = ttk.Entry(main_frame, font=('等线', 12), width=40)
        library_entry.pack(pady=10)
        library_entry.insert(0, "requests pillow openai")
        library_entry.focus_set()
        
        tk.Label(main_frame, text="常用库示例:", font=('等线', 10)).pack(anchor='w', pady=5)
        common_libs = "requests - HTTP请求库\npillow - 图像处理库\nopenai - OpenAI API库\nnumpy - 科学计算库\npandas - 数据分析库"
        tk.Label(main_frame, text=common_libs, font=('等线', 9), 
                justify=tk.LEFT).pack(anchor='w', pady=5)
        
        def do_install():
            libraries = library_entry.get().strip()
            if not libraries:
                messagebox.showwarning("警告", "请输入要安装的库名")
                return
            
            dialog.destroy()
            self.install_library(libraries)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text="安装", command=do_install).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # 绑定回车键
        library_entry.bind("<Return>", lambda e: do_install())

    def install_library(self, libraries=None):
        """一键安装第三方库"""
        if not libraries:
            self.install_library_dialog()
            return
        
        try:
            # 分割库名
            lib_list = libraries.split()
            
            # 构建安装命令
            if sys.platform == 'win32':
                # Windows系统
                cmd = " && ".join([f'pip install {lib}' for lib in lib_list])
                terminal_cmd = f'start cmd /K "{cmd} && echo 安装完成！ && pause"'
            else:
                # Linux/Mac系统
                cmd = " && ".join([f'pip install {lib}' for lib in lib_list])
                if sys.platform == 'darwin':  # macOS
                    applescript = f'''
                    tell application "Terminal"
                        activate
                        do script "{cmd} && echo '安装完成！' && read"
                    end tell
                    '''
                    terminal_cmd = ['osascript', '-e', applescript]
                else:  # Linux
                    terminal_cmd = ['gnome-terminal', '--', 'bash', '-c', f'{cmd} && echo "安装完成！" && read']
            
            # 在终端中执行安装命令
            if sys.platform == 'win32':
                subprocess.Popen(terminal_cmd, shell=True)
            else:
                subprocess.Popen(terminal_cmd)
            
            self.show_info_message("已在终端中启动库安装过程...")
            
        except Exception as e:
            self.show_info_message(f"安装失败: {str(e)}", "error")

    # === Python专区 ===
    def show_python_zone(self):
        """打开Python专区子窗口"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Python专区")
        dialog.geometry("600x500")
        dialog.resizable(False, False)
        dialog.iconbitmap("./Resources/app.ico")
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Python专区", font=('等线', 18, 'bold')).pack(pady=10)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="打包为EXE", command=lambda: [dialog.destroy(), self.package_to_exe()], 
                  width=20).pack(pady=10, ipadx=10, ipady=5)
        ttk.Button(button_frame, text="安装第三方库", command=lambda: [dialog.destroy(), self.install_library_dialog()], 
                  width=20).pack(pady=10, ipadx=10, ipady=5)
        
        info_frame = ttk.LabelFrame(main_frame, text="功能说明", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        info_text = "打包为EXE：将Python文件打包成独立的可执行文件，无需安装Python环境即可运行。\n\n安装第三方库：快速安装Python第三方库，支持批量安装多个库。"
        tk.Label(info_frame, text=info_text, font=('等线', 10), justify=tk.LEFT, wraplength=550).pack(anchor='w')

    # === 新增功能：打开系统终端 ===
    def open_terminal(self):
        """打开系统终端"""
        try:
            current_dir = os.getcwd()
            if self.current_file:
                current_dir = os.path.dirname(self.current_file)
            
            if sys.platform == 'win32':
                # Windows系统
                cmd = f'start cmd /K "cd /d "{current_dir}""'
                subprocess.Popen(cmd, shell=True)
            elif sys.platform == 'darwin':  # macOS
                applescript = f'''
                tell application "Terminal"
                    activate
                    do script "cd '{current_dir}'"
                end tell
                '''
                subprocess.Popen(['osascript', '-e', applescript])
            else:  # Linux
                subprocess.Popen(['gnome-terminal', '--working-directory', current_dir])
            
            self.show_info_message("已打开系统终端")
            
        except Exception as e:
            self.show_info_message(f"打开终端失败: {str(e)}", "error")

    # AI功能方法
    def analyze_current_code(self):
        """分析当前代码"""
        current_code = self.get_current_editor_content()
        if not current_code:
            self.add_chat_message("小源", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请分析当前代码")
        threading.Thread(target=self.analyze_code_thread, 
                        args=(current_code,), daemon=True).start()

    def suggest_improvements(self):
        """获取改进建议"""
        current_code = self.get_current_editor_content()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请提供代码改进建议")
        threading.Thread(target=self.suggest_improvements_thread, 
                        args=(current_code,), daemon=True).start()

    def explain_current_code(self):
        """解释当前代码"""
        current_code = self.get_current_editor_content()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请解释当前代码")
        threading.Thread(target=self.explain_code_thread, 
                        args=(current_code,), daemon=True).start()

    def generate_html_template(self):
        """生成HTML模板"""
        self.add_chat_message("你", "请生成HTML模板")
        threading.Thread(target=self.generate_html_thread, 
                        daemon=True).start()

    def debug_current_code(self):
        """调试当前代码"""
        current_code = self.get_current_editor_content()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请调试当前代码")
        try:
            import ai_compiler
            response = ai_compiler.debug(current_code)
            self.add_chat_message("小源", response)
        except Exception as e:
            self.add_chat_message("小源", f"调试失败：{str(e)}")

    def review_current_code(self):
        """代码审查"""
        current_code = self.get_current_editor_content()
        if not current_code:
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
            return
        
        self.add_chat_message("你", "请对当前代码进行审查")
        try:
            import ai_compiler
            response = ai_compiler.review(current_code)
            self.add_chat_message("小源", response)
        except Exception as e:
            self.add_chat_message("小源", f"代码审查失败：{str(e)}")
    
    def auto_generate_compile(self):
        """自动生成并编译代码，直到正常工作"""
        # 获取用户需求
        user_requirement = self.get_user_requirement()
        if not user_requirement:
            return
        
        self.add_chat_message("小源", f"开始自动生成代码，需求：{user_requirement}")
        
        # 在新线程中执行自动生成和编译过程
        threading.Thread(target=self.auto_generate_compile_thread,
                        args=(user_requirement,), daemon=True).start()
    
    def get_user_requirement(self):
        """获取用户的代码生成需求"""
        dialog = tk.Toplevel(self.root)
        dialog.title("自动代码生成")
        dialog.geometry("500x300")
        dialog.iconbitmap("./Resources/app.ico")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="请输入您的代码需求：", font=('等线', 12)).pack(pady=10)
        
        # 需求输入框
        requirement_entry = scrolledtext.ScrolledText(main_frame, font=('等线', 12),
                                                     width=60, height=8, wrap=tk.WORD)
        requirement_entry.pack(pady=10, fill=tk.BOTH, expand=True)
        
        # 默认需求示例
        default_requirement = "请生成一个简单的Python计算器程序，可以进行加减乘除运算"
        requirement_entry.insert(tk.END, default_requirement)
        
        # 结果变量
        result = {"requirement": ""}
        
        def on_ok():
            result["requirement"] = requirement_entry.get(1.0, tk.END).strip()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # 按钮框架
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        # 等待对话框关闭
        dialog.grab_set()
        dialog.wait_window()
        
        return result["requirement"]
    
    def auto_generate_compile_thread(self, requirement):
        """自动生成和编译代码的线程函数"""
        max_attempts = 10  # 最大尝试次数
        attempt = 0
        success = False
        
        while attempt < max_attempts and not success:
            attempt += 1
            self.add_chat_message("小源", f"第 {attempt} 次尝试生成代码...")
            
            try:
                # 生成代码
                generated_code = self.generate_code_with_ai(requirement)
                if not generated_code:
                    self.add_chat_message("小源", "代码生成失败，继续尝试...")
                    continue
                
                # 保存临时文件
                temp_file_path = self.save_temp_code(generated_code)
                
                # 编译和运行代码
                success, output = self.compile_and_run(temp_file_path)
                
                if success:
                    self.add_chat_message("小源", f"代码生成和运行成功！\n\n{generated_code}")
                    self.add_chat_message("小源", f"运行结果：\n{output}")
                    
                    # 将生成的代码插入到编辑器
                    self.root.after(0, lambda: self.insert_generated_code(generated_code))
                    break
                else:
                    self.add_chat_message("小源", f"代码运行失败，错误信息：\n{output}")
                    
                    # 修复代码
                    requirement = f"之前的代码运行出错，请修复：\n\n代码：{generated_code}\n\n错误：{output}\n\n请重新生成可以正常运行的代码"
                    
            except Exception as e:
                self.add_chat_message("小源", f"自动生成编译过程出错：{str(e)}")
        
        if not success:
            self.add_chat_message("小源", f"已尝试 {max_attempts} 次，仍无法生成可正常运行的代码，请尝试调整需求。")
    
    def generate_code_with_ai(self, requirement):
        """使用AI生成代码"""
        try:
            import ai_compiler
            response = ai_compiler.generate(requirement)  # 使用正确的函数名
            
            # 提取代码块
            code_blocks = ai_compiler.extract_code(response)
            if code_blocks:
                return code_blocks[0]["code"]  # 返回第一个代码块
            return response
        except Exception as e:
            self.add_chat_message("小源", f"代码生成失败：{str(e)}")
            return None
    
    def save_temp_code(self, code):
        """保存临时代码文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            return f.name
    
    def compile_and_run(self, file_path):
        """编译和运行代码"""
        try:
            # 使用Python运行代码
            result = subprocess.run([sys.executable, file_path],
                                  capture_output=True,
                                  text=True,
                                  timeout=30)  # 30秒超时
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "运行超时（30秒）"
        except Exception as e:
            return False, str(e)
    
    def insert_generated_code(self, code):
        """将生成的代码插入到编辑器"""
        if self.code_text:
            # 清空当前内容并插入新代码
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, code)
            self.apply_syntax_highlighting()
            self.show_info_message("已将生成的代码插入到编辑器")

    def send_quick_chat(self, event=None):
        """发送快速聊天消息"""
        message = self.quick_chat_input.get().strip()
        if not message:
            return
        
        self.quick_chat_input.delete(0, tk.END)
        self.add_chat_message("你", message)
        
        # 获取当前代码上下文
        current_content = self.get_current_editor_content()
        current_type = self.detect_file_type(current_content)
        
        # 在新线程中调用AI
        threading.Thread(target=self.chat_with_ai, 
                        args=(message, current_content, current_type), 
                        daemon=True).start()

    def chat_with_ai(self, message, code_context, file_type):
        """与AI对话，自动插入生成的代码"""
        try:
            import ai_compiler
            
            if file_type and code_context:
                enhanced_message = f"当前正在编辑{file_type.upper()}文件:\n\n{message}\n\n当前内容:\n{code_context}"
            else:
                enhanced_message = message
            
            # 先显示AI开始输入的提示
            self.root.after(0, self.start_streaming_response)
            
            # 定义流式回调函数
            def stream_callback(chunk):
                self.root.after(0, self.streaming_response_chunk, chunk)
            
            # 使用流式API调用
            response = ai_compiler.chat(enhanced_message, code_context, stream_callback=stream_callback)
            
            # 自动提取并插入代码
            self.root.after(0, self.auto_insert_code, response, file_type)
            
            # 结束流式响应
            self.root.after(0, self.end_streaming_response)
            
        except Exception as e:
            self.root.after(0, self.add_chat_message, "小源", f"对话失败：{str(e)}")

    def auto_insert_code(self, ai_response, current_file_type):
        """自动从AI响应中提取代码并插入到编辑器"""
        try:
            import ai_compiler
            
            # 提取代码块
            code_blocks = ai_compiler.extract_code(ai_response)
            if not code_blocks:
                return
                
            # 根据当前文件类型智能选择代码块
            inserted = self.smart_insert_code(code_blocks, current_file_type)
            
            if inserted:
                self.show_info_message("已自动插入AI生成的代码")
                
        except Exception as e:
            print(f"自动插入代码失败: {e}")

    def smart_insert_code(self, code_blocks, current_file_type):
        """智能插入代码，根据文件类型选择最佳匹配"""
        if not code_blocks:
            return False
            
        # 优先级匹配
        priority_order = [
            current_file_type,  # 1. 完全匹配当前文件类型
            'python',          # 2. Python代码
            'html',            # 3. HTML代码  
            'javascript',      # 4. JavaScript代码
            'css',             # 5. CSS代码
            'markdown',        # 6. Markdown代码
            'text'             # 7. 纯文本
        ]
        
        # 按优先级查找匹配的代码块
        selected_block = None
        for lang in priority_order:
            for block in code_blocks:
                if block['language'] == lang:
                    selected_block = block
                    break
            if selected_block:
                break
        
        # 如果没有找到匹配的，使用第一个代码块
        if not selected_block:
            selected_block = code_blocks[0]
        
        # 插入代码
        if selected_block and hasattr(self, 'code_text') and self.code_text is not None:
            lang = selected_block['language']
            code = selected_block['code']
            
            # 完全清除编辑框代码
            self.code_text.delete(1.0, tk.END)
            
            # 插入完整的新代码
            self.code_text.insert(tk.END, code)
            
            # 应用语法高亮
            if self.syntax_highlight_enabled:
                self.apply_syntax_highlighting()
            
            return True
        
        return False

    def add_chat_message(self, sender, message):
        """添加消息到聊天显示"""
        self.chat_display.config(state=tk.NORMAL)
        
        if sender == "小源":
            # 为AI消息添加打字机效果
            self.chat_display.insert(tk.END, f"\n🤖 {sender}: ", "ai_message")
            self.chat_display.tag_configure("ai_message", foreground="blue")
            self.chat_display.config(state=tk.DISABLED)
            # 使用after方法逐字显示消息
            self.typewriter_effect(message, "ai_message")
        else:
            # 用户消息直接显示
            self.chat_display.insert(tk.END, f"\n👤 {sender}: {message}\n", "user_message")
            self.chat_display.tag_configure("user_message", foreground="green")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
    
    def start_streaming_response(self):
        """开始流式响应，显示AI开始输入的提示"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n🤖 小源: ", "ai_message")
        self.chat_display.tag_configure("ai_message", foreground="blue")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        # 初始化流式响应状态
        self.streaming_response = ""
    
    def streaming_response_chunk(self, chunk):
        """处理流式响应块，实时显示"""
        try:
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, chunk, "ai_message")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            # 保存当前响应内容
            self.streaming_response += chunk
        except Exception as e:
            # 记录错误但不中断流式处理
            print(f"流式响应UI更新错误: {str(e)}")
    
    def end_streaming_response(self):
        """结束流式响应"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def typewriter_effect(self, message, tag, index=0):
        """打字机效果显示消息（用于非流式响应）"""
        if index < len(message):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, message[index], tag)
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            # 递归调用after方法，实现打字机效果
            self.root.after(20, self.typewriter_effect, message, tag, index+1)
        else:
            # 消息显示完毕，添加换行
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, "\n")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)

    def analyze_code_thread(self, code):
        """分析代码线程"""
        try:
            import ai_compiler
            response = ai_compiler.analyze(code)
            self.root.after(0, lambda: self.add_chat_message("小源", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("小源", f"分析失败：{str(e)}"))

    def suggest_improvements_thread(self, code):
        """改进建议线程"""
        try:
            import ai_compiler
            response = ai_compiler.suggest_improvements(code)
            self.root.after(0, lambda: self.add_chat_message("小源", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("小源", f"获取建议失败：{str(e)}"))

    def explain_code_thread(self, code):
        """解释代码线程"""
        try:
            import ai_compiler
            response = ai_compiler.explain(code)
            self.root.after(0, lambda: self.add_chat_message("小源", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("小源", f"解释失败：{str(e)}"))

    def generate_html_thread(self):
        """生成HTML线程"""
        try:
            import ai_compiler
            response = ai_compiler.generate_html("生成一个完整的HTML5模板，包含基本的页面结构和样式")
            self.root.after(0, lambda: self.add_chat_message("小源", response))
        except Exception as e:
            self.root.after(0, lambda: self.add_chat_message("小源", f"生成HTML失败：{str(e)}"))

    def get_current_editor_content(self):
        """获取当前编辑器内容"""
        try:
            if hasattr(self, 'code_text') and self.code_text is not None:
                return self.code_text.get(1.0, tk.END).strip()
            return ""
        except Exception as e:
            print(f"获取编辑器内容失败: {e}")
            return ""

    def new_file_dialog(self):
        """新建文件"""
        self.new_file()
    
    def create_new_file(self, file_type, dialog):
        """创建新文件"""
        dialog.destroy()
        self.new_file(file_type)

    def new_file(self, file_type="txt"):
        """新建文件"""
        try:
            self.current_file = None
            self.current_file_type = file_type
            
            # 确保编辑器界面已显示
            if not hasattr(self, 'code_text') or self.code_text is None:
                self.show_editor_screen()
            
            # 删除现有内容
            self.code_text.delete(1.0, tk.END)
            
            # 更新文件类型标签（如果存在）
            if hasattr(self, 'file_type_label') and self.file_type_label is not None:
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
            elif file_type == "txt":
                initial_content = """欢迎使用聚源仓

这是一个普通的文本文件，您可以在这里输入任何语言的内容。

- 功能1: 文本编辑
- 功能2: 支持多种格式换行
- 功能3: AI功能增强

开始编写您的内容！"""
                self.code_text.insert(1.0, initial_content)
            else:
                # Python文件 - 简洁的初始内容
                initial_content = '''# 欢迎使用聚源仓 AI IDE！

# 开始编辑您的Python代码...

# 提示：
# • 可以使用小源AI助手帮助您生成和优化代码
# • 支持语法高亮显示
# • 右键点击可打开快捷菜单
'''
                self.code_text.insert(1.0, initial_content)
            
            self.show_info_message(f"已创建新{file_type}文件")
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
                self.open_file_from_path(file_path)
        except Exception as e:
            messagebox.showerror("错误", f"打开文件失败: {str(e)}")

    def open_file_from_path(self, file_path):
        """从路径打开文件"""
        try:
            # 根据文件扩展名确定文件类型
            if file_path.endswith('.py'):
                file_type = "python"
            elif file_path.endswith('.html') or file_path.endswith('.htm'):
                file_type = "html"
            elif file_path.endswith('.md') or file_path.endswith('.markdown'):
                file_type = "markdown"
            elif file_path.endswith('.txt'):
                file_type = "txt"
            else:
                file_type = "txt"  # 默认文本文件，避免乱码
            
            # 尝试不同编码读取文件 - 优先使用utf-8
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
            content = ""
            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            # 如果都失败，尝试使用errors='replace'模式
            if not content:
                try:
                    with open(file_path, "r", encoding='utf-8', errors='replace') as f:
                        content = f.read()
                except Exception as e:
                    print(f"读取文件失败: {e}")
            
            # 直接在编辑器中显示文件内容
            filename = os.path.basename(file_path)
            self.current_file = file_path
            self.current_file_type = file_type
            
            # 确保代码编辑器存在
            if not hasattr(self, 'code_text') or not self.code_text:
                # 如果编辑器不存在，先显示编辑器界面
                self.show_editor_screen()
            
            # 更新编辑器内容
            self.code_text.delete(1.0, tk.END)
            self.code_text.insert(1.0, content)
            
            # 更新文件类型标签
            self.file_type_label.config(text=f"{file_type.upper()}文件: {filename}")
            
            # 刷新工具栏以显示/隐藏Python专区按钮
            self.refresh_toolbar()
            
            self.show_info_message(f"已打开文件: {file_path}")
            if self.syntax_highlight_enabled:
                self.apply_syntax_highlighting()
                
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def save_file(self):
        """保存文件"""
        try:
            if self.current_file:
                # 如果有当前文件路径，直接保存
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.code_text.get(1.0, tk.END))
                self.show_info_message(f"已保存文件: {self.current_file}")
                return True
            else:
                # 否则使用另存为
                return self.save_file_as()
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            return False

    def save_file_as(self):
        """另存为文件 - 修复版本"""
        try:
            # 确定默认文件类型
            file_type = self.current_file_type
            
            # 统一的文件类型列表，包含所有四种格式
            all_filetypes = [("Python文件", "*.py"), ("HTML文件", "*.html"), ("Markdown文件", "*.md"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
            
            if file_type == "html":
                defaultextension = ".html"
            elif file_type == "markdown":
                defaultextension = ".md"
            elif file_type == "python":
                defaultextension = ".py"
            else:
                defaultextension = ".txt"
            
            filetypes = all_filetypes
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=defaultextension, 
                filetypes=filetypes,
                initialfile=os.path.basename(self.current_file) if self.current_file else "untitled"
            )
            if file_path:
                self.current_file = file_path
                # 根据文件扩展名更新文件类型
                if file_path.endswith('.html') or file_path.endswith('.htm'):
                    self.current_file_type = "html"
                elif file_path.endswith('.md') or file_path.endswith('.markdown'):
                    self.current_file_type = "markdown"
                elif file_path.endswith('.py'):
                    self.current_file_type = "python"
                elif file_path.endswith('.txt'):
                    self.current_file_type = "txt"
                else:
                    self.current_file_type = "txt"
                
                self.file_type_label.config(text=f"{self.current_file_type.upper()}文件: {os.path.basename(file_path)}")
                
                return self.save_file()
            return False
        except Exception as e:
            messagebox.showerror("错误", f"另存为文件失败: {str(e)}")
            return False

    def show_about(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("关于")
        dialog.geometry("550x400")
        dialog.iconbitmap("./Resources/app.ico")
        dialog.resizable(False,False)
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Python聚源仓项目，是一款AI IDE，由骏骏爱编程开发，其\n他人辅助帮忙开发，具有AI分析代码，AI优化代码，AI上下\n文理解等功能，完全免费，完全免费开源。\n官网：https://www.juyuancang.cn\n反馈邮箱：junjunloveprogramming@juyuancang.cn\n当前版本：1.0.8", font=('等线', 12)).pack(pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        about_button = [
            ("打开官网", self.open_official_website),
            ("复制邮箱", self.copy_email), 
            ("投喂小源", self.give_reward),
            ("意见反馈", self.feedback),
        ]
        
        for i, (text, command) in enumerate(about_button):
            btn = ttk.Button(button_frame, text=text, command=command)
            btn.grid(row=i//2, column=i%2, padx=10, pady=10, ipadx=10, ipady=5)

    def open_official_website(self):
        os.startfile("https://www.juyuancang.cn")

    def copy_email(self):
        pyperclip.copy("junjunloveprogramming@juyuancang.cn")

    def give_reward(self):
        os.startfile("https://www.juyuancang.cn/image/zanshang.jpg")

    def feedback(self):
        os.startfile("https://v.wjx.cn/vm/exWh0RW.aspx#")

    def hidden_easter_egg(self):
        """隐藏彩蛋"""
        try:
            self.hidden_easter_egg_window = tk.Toplevel(self.root)
            self.hidden_easter_egg_window.title("隐藏彩蛋")
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

if __name__ == "__main__":
    root = tk.Tk()
    app = CodeEditorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.safe_close)
    root.mainloop()