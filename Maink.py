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
    lock_socket.bind(('localhost', 47291))
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
        self.root.title("聚源仓-Version 1.0.6-开源版本")  # 更新版本号
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
        
        # 工具栏项目（新增三个功能）
        self.toolbar_items = [
            ("新建", './Resources/new.png', self.new_file_dialog),
            ("打开", './Resources/open.png', self.open_file),
            ("保存", './Resources/save.png', self.save_file),
            ("AI助手", './Resources/ai.png', self.toggle_ai_panel),
            ("运行", './Resources/run.png', self.run_current_file),
            ("打包exe", './Resources/open.png', self.package_to_exe),
            ("安装库", './Resources/open.png', self.install_library),
            ("打开终端", './Resources/run.png', self.open_terminal),
            ("关于", './Resources/info.png', self.show_about)
        ]
        
        # 初始化后端和API
        self.setup_api_key()
        self.setup_backend()
        
        # 启动简化界面
        self.setup_simple_ui()
        
        # 显示欢迎消息
        self.show_welcome_message()

    def setup_api_key(self):
        """设置DeepSeek API密钥（主备双API）"""
        try:
            import ai_compiler
            
            primary_api_key = "你的Deepseek API"  # 主API
            backup_api_key = "你的备用Deepseek API"  # 备用API
            
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
        """初始化简化用户界面"""
        try:
            # 清除现有界面
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # 创建主容器（左右分栏）
            self.main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
            self.main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 左侧编辑器区域
            self.editor_frame = ttk.Frame(self.main_container)
            self.main_container.add(self.editor_frame, stretch='always')
            
            # 右侧AI面板
            self.ai_panel = ttk.Frame(self.main_container, width=400)
            self.main_container.add(self.ai_panel, stretch='never')
            
            # 设置初始分割比例 (70% 编辑器, 30% AI面板)
            self.root.update()
            self.main_container.sash_place(0, int(self.root.winfo_width() * 0.7), 0)
            
            # 设置编辑器区域
            self.setup_editor_area(self.editor_frame)
            
            # 设置AI面板
            self.setup_ai_panel(self.ai_panel)
            
            print("简化界面初始化完成")
            
        except Exception as e:
            print(f"UI初始化失败: {e}")
            # 创建紧急备用界面
            emergency_frame = ttk.Frame(self.root)
            emergency_frame.pack(fill=tk.BOTH, expand=True)
            self.code_text = scrolledtext.ScrolledText(emergency_frame, wrap=tk.WORD, font=("Consolas", 12))
            self.code_text.pack(fill=tk.BOTH, expand=True)

    def setup_editor_area(self, parent):
        """设置编辑器区域"""
        # 顶部工具栏
        self.toolbar = ttk.Frame(parent)
        self.toolbar.pack(fill=tk.X, side=tk.TOP, padx=5, pady=5)
        
        # 批量注册工具栏项目
        self.image = []

        if os.path.exists('./Resources/app.jpg'):
            try:
                img = Image.open('./Resources/app.jpg')
                img = img.resize((60, 60))
                self.image.append(ImageTk.PhotoImage(img))
                tk.Button(self.toolbar, image=self.image[0], relief="flat", command=self.hidden_easter_egg).pack(side='left')
            except Exception as e:
                print(f"加载logo图片失败: {e}")
                
        for name, icon, command in self.toolbar_items:
            try:
                if icon is not None and os.path.exists(icon):
                    ico = Image.open(icon).resize((30, 30))
                    self.image.append(ImageTk.PhotoImage(ico))
                    tk.Button(self.toolbar, text=name, command=command, font=('等线', 10),
                              relief='flat', image=self.image[-1], compound='top').pack(side=tk.LEFT, padx=2, pady=2)
                else:
                    tk.Button(self.toolbar, text=name, command=command, font=('等线', 10),
                              relief='flat').pack(side=tk.LEFT, padx=2, pady=2)
            except Exception as e:
                print(f"加载工具栏按钮失败 {name}: {e}")
                tk.Button(self.toolbar, text=name, command=command, font=('等线', 10),
                          relief='flat').pack(side=tk.LEFT, padx=2, pady=2)
        
        # 文件类型显示
        file_info_frame = ttk.Frame(parent)
        file_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.file_type_label = ttk.Label(file_info_frame, text="Python文件", font=('等线', 12, 'bold'))
        self.file_type_label.pack(side=tk.LEFT)
        
        # 主编辑器
        editor_container = ttk.Frame(parent)
        editor_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.code_text = scrolledtext.ScrolledText(
            editor_container, 
            wrap=tk.WORD, 
            font=("Consolas", 12)
        )
        self.code_text.pack(fill=tk.BOTH, expand=True)
        
        # 配置语法高亮
        self.code_text.tag_configure("keyword", foreground="blue", font=("Consolas", 12, "bold"))
        
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
        self.right_click_menu.add_command(label="AI分析选中代码", command=self.analyze_selected_code)
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

    def setup_ai_panel(self, parent):
        """设置右侧AI面板"""
        # AI面板标题
        ai_header = ttk.Frame(parent)
        ai_header.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(ai_header, text="聚源仓AI助手\nVersion1.0.6", font=('等线', 14, 'bold')).pack()
        
        # 隐藏/显示AI面板按钮
        self.toggle_ai_btn = ttk.Button(ai_header, text="◀", width=3, command=self.toggle_ai_panel)
        self.toggle_ai_btn.pack(side=tk.RIGHT)
        
        # AI功能按钮区域
        ai_buttons_frame = ttk.Frame(parent)
        ai_buttons_frame.pack(fill=tk.X, padx=15, pady=10)
        
        ai_functions = [
            ("分析代码", self.analyze_current_code),
            ("优化建议", self.suggest_improvements),
            ("解释代码", self.explain_current_code),
            ("生成HTML", self.generate_html_template),
            ("调试代码", self.debug_current_code),
            ("代码审查", self.review_current_code),
            ("设置API密钥", self.setup_api_dialog),  # 新增API设置
            ("打包exe", self.package_to_exe),
            ("安装库", self.install_library_dialog),
            ("打开终端", self.open_terminal)
        ]
        
        for text, command in ai_functions:
            btn = ttk.Button(ai_buttons_frame, text=text, command=command)
            btn.pack(fill=tk.X, pady=3)
        
        # 分隔线
        separator = ttk.Separator(parent, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, padx=15, pady=10)
        
        # 快速聊天区域
        chat_frame = ttk.Frame(parent)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        tk.Label(chat_frame, text="快速对话:", font=('等线', 11, 'bold')).pack(anchor='w')
        
        self.quick_chat_input = ttk.Entry(chat_frame, font=('等线', 10))
        self.quick_chat_input.pack(fill=tk.X, pady=(5, 5))
        self.quick_chat_input.bind("<Return>", self.send_quick_chat)
        
        send_btn = ttk.Button(chat_frame, text="发送", command=self.send_quick_chat)
        send_btn.pack(fill=tk.X, pady=(0, 10))
        
        # 聊天历史显示
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, 
            wrap=tk.WORD, 
            font=("等线", 9),
            height=15
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # 显示欢迎消息
        welcome_msg = """欢迎使用聚源仓AI助手！

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

请描述您的问题或需要帮助的代码部分。"""
        self.add_chat_message("AI", welcome_msg)

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
        if self.ai_panel.winfo_ismapped():
            # 隐藏AI面板
            self.main_container.remove(self.ai_panel)
            self.toggle_ai_btn.config(text="▶")
        else:
            # 显示AI面板
            self.main_container.add(self.ai_panel, stretch='never')
            self.toggle_ai_btn.config(text="◀")
            # 恢复分割比例
            self.root.update()
            self.main_container.sash_place(0, int(self.root.winfo_width() * 0.7), 0)

    def show_welcome_message(self):
        """显示欢迎消息"""
        welcome_code = '''# 欢迎使用聚源仓 AI IDE！

# 这是一个智能代码编辑器，支持：
# • Python、HTML、Markdown等多种语言
# • AI智能代码分析和生成
# • 语法高亮显示
# • 一键运行代码
# • 一键打包为exe文件
# • 一键安装第三方库
# • 打开系统终端
# • 右键菜单操作（新增功能）
# • 主备双API支持（新增功能）

# 右键菜单功能：
# 在编辑器中右键点击可打开快捷菜单，包含：
# - 复制、粘贴、剪切
# - 全选
# - 运行选中代码
# - AI分析选中代码
# - 注释/取消注释

# 新建Python文件时显示的示例代码：

def package_to_exe():
    """一键打包为exe文件"""
    import subprocess
    import os
    
    # 获取当前文件路径
    current_file = __file__
    
    # 使用PyInstaller打包
    cmd = f'pyinstaller --onefile --windowed "{current_file}"'
    
    # 在终端中执行打包命令
    if os.name == 'nt':  # Windows
        subprocess.Popen(f'start cmd /K "{cmd}"', shell=True)
    else:  # Linux/Mac
        subprocess.Popen(f'xterm -e "{cmd}"', shell=True)

def install_library():
    """一键安装第三方库"""
    import subprocess
    import os
    
    # 要安装的库列表
    libraries = ["requests", "pillow", "openai"]
    
    for lib in libraries:
        cmd = f'pip install {lib}'
        
        # 在终端中执行安装命令
        if os.name == 'nt':  # Windows
            subprocess.Popen(f'start cmd /K "{cmd}"', shell=True)
        else:  # Linux/Mac
            subprocess.Popen(f'xterm -e "{cmd}"', shell=True)

def open_terminal():
    """打开系统终端"""
    import subprocess
    import os
    
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 打开终端
    if os.name == 'nt':  # Windows
        subprocess.Popen(f'start cmd /K "cd /d "{current_dir}""', shell=True)
    elif os.name == 'posix':  # Linux/Mac
        if sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', '-a', 'Terminal', current_dir])
        else:  # Linux
            subprocess.Popen(['gnome-terminal', '--working-directory', current_dir])

# 使用示例
if __name__ == "__main__":
    print("Hello, World!")
    
    # 取消注释以下行来测试功能
    # package_to_exe()    # 打包为exe
    # install_library()   # 安装第三方库  
    # open_terminal()     # 打开终端
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
        if not self.backend_processor or not hasattr(self, 'code_text') or self.code_text is None:
            return
            
        try:
            # 获取当前文本
            text_content = self.code_text.get("1.0", "end-1c")
            self.code_text.tag_remove("keyword", "1.0", "end")
            
            # 自动检测文件类型并应用语法高亮
            if self.detect_file_type(text_content) == "python":
                self.backend_processor.insertColorTag(text_content, self.code_text)
            
        except Exception as e:
            print(f"语法高亮错误: {e}")

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
            self.add_chat_message("AI", "请先在编辑器中输入一些代码。")
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
            self.add_chat_message("AI", response)
        except Exception as e:
            self.add_chat_message("AI", f"调试失败：{str(e)}")

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
            self.add_chat_message("AI", response)
        except Exception as e:
            self.add_chat_message("AI", f"代码审查失败：{str(e)}")

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
                
            response = ai_compiler.chat(enhanced_message, code_context)
            
            # 自动提取并插入代码
            self.auto_insert_code(response, file_type)
            
            self.add_chat_message("AI", response)
        except Exception as e:
            self.add_chat_message("AI", f"对话失败：{str(e)}")

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
            
            # 根据语言添加适当的注释
            if lang == 'python':
                separator = f"\n\n# ===== AI生成的Python代码 =====\n{code}\n# ===== 代码结束 =====\n"
            elif lang == 'html':
                separator = f"\n\n<!-- ===== AI生成的HTML代码 ===== -->\n{code}\n<!-- ===== 代码结束 ===== -->\n"
            elif lang == 'css':
                separator = f"\n\n/* ===== AI生成的CSS代码 ===== */\n{code}\n/* ===== 代码结束 ===== */\n"
            elif lang == 'javascript':
                separator = f"\n\n// ===== AI生成的JavaScript代码 =====\n{code}\n// ===== 代码结束 =====\n"
            else:
                separator = f"\n\n{code}\n"
            
            self.code_text.insert(tk.END, separator)
            self.code_text.see(tk.END)
            
            # 应用语法高亮
            if self.syntax_highlight_enabled:
                self.apply_syntax_highlighting()
            
            return True
        
        return False

    def add_chat_message(self, sender, message):
        """添加消息到聊天显示"""
        self.chat_display.config(state=tk.NORMAL)
        
        if sender == "AI":
            self.chat_display.insert(tk.END, f"\n🤖 {sender}: {message}\n", "ai_message")
            self.chat_display.tag_configure("ai_message", foreground="blue")
        else:
            self.chat_display.insert(tk.END, f"\n👤 {sender}: {message}\n", "user_message")
            self.chat_display.tag_configure("user_message", foreground="green")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

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
        """新建文件对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("新建文件")
        dialog.geometry("300x250")
        dialog.iconbitmap("./Resources/app.ico")
        dialog.resizable(False,False)
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="选择文件类型:", font=('等线', 12)).pack(pady=10)
        
        file_types = [
            ("Python文件 (.py)", "python"),
            ("HTML文件 (.html)", "html"), 
            ("Markdown文件 (.md)", "markdown")
        ]
        
        for text, file_type in file_types:
            btn = ttk.Button(main_frame, text=text, 
                           command=lambda ft=file_type: self.create_new_file(ft, dialog))
            btn.pack(fill=tk.X, pady=5)

    def create_new_file(self, file_type, dialog):
        """创建新文件"""
        dialog.destroy()
        self.new_file(file_type)

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
            else:
                # Python文件 - 包含三个新功能的示例代码
                initial_content = '''# 欢迎使用聚源仓 AI IDE！

# 这是一个智能代码编辑器，支持：
# • Python、HTML、Markdown等多种语言
# • AI智能代码分析和生成
# • 语法高亮显示
# • 一键运行代码
# • 一键打包为exe文件
# • 一键安装第三方库
# • 打开系统终端
# • 右键菜单操作（新增功能）
# • 主备双API支持（新增功能）

# 右键菜单功能：
# 在编辑器中右键点击可打开快捷菜单，包含：
# - 复制、粘贴、剪切
# - 全选
# - 运行选中代码
# - AI分析选中代码
# - 注释/取消注释

# 新建Python文件时显示的示例代码：

def package_to_exe():
    """一键打包为exe文件"""
    import subprocess
    import os
    
    # 获取当前文件路径
    current_file = __file__
    
    # 使用PyInstaller打包
    cmd = f'pyinstaller --onefile --windowed "{current_file}"'
    
    # 在终端中执行打包命令
    if os.name == 'nt':  # Windows
        subprocess.Popen(f'start cmd /K "{cmd}"', shell=True)
    else:  # Linux/Mac
        subprocess.Popen(f'xterm -e "{cmd}"', shell=True)

def install_library():
    """一键安装第三方库"""
    import subprocess
    import os
    
    # 要安装的库列表
    libraries = ["requests", "pillow", "openai"]
    
    for lib in libraries:
        cmd = f'pip install {lib}'
        
        # 在终端中执行安装命令
        if os.name == 'nt':  # Windows
            subprocess.Popen(f'start cmd /K "{cmd}"', shell=True)
        else:  # Linux/Mac
            subprocess.Popen(f'xterm -e "{cmd}"', shell=True)

def open_terminal():
    """打开系统终端"""
    import subprocess
    import os
    
    # 获取当前工作目录
    current_dir = os.getcwd()
    
    # 打开终端
    if os.name == 'nt':  # Windows
        subprocess.Popen(f'start cmd /K "cd /d "{current_dir}""', shell=True)
    elif os.name == 'posix':  # Linux/Mac
        if sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', '-a', 'Terminal', current_dir])
        else:  # Linux
            subprocess.Popen(['gnome-terminal', '--working-directory', current_dir])

# 使用示例
if __name__ == "__main__":
    print("Hello, World!")
    
    # 取消注释以下行来测试功能
    # package_to_exe()    # 打包为exe
    # install_library()   # 安装第三方库  
    # open_terminal()     # 打开终端
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
            
            self.show_info_message(f"已打开文件: {file_path}")
                
        except Exception as e:
            messagebox.showerror("错误", f"无法打开文件: {str(e)}")

    def save_file(self):
        """保存文件"""
        try:
            if self.current_file:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.code_text.get(1.0, tk.END))
                self.show_info_message(f"已保存文件: {self.current_file}")
                return True
            else:
                return self.save_file_as()
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            return False

    def save_file_as(self):
        """另存为文件 - 修复版本"""
        try:
            # 修复：直接使用当前文件类型，而不是通过内容检测
            file_type = self.current_file_type
            
            if file_type == "html":
                filetypes = [("HTML Files", "*.html"), ("All Files", "*.*")]
                defaultextension = ".html"
            elif file_type == "markdown":
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
        dialog = tk.Toplevel(self.root)
        dialog.title("关于")
        dialog.geometry("550x400")
        dialog.iconbitmap("./Resources/app.ico")
        dialog.resizable(False,False)
        dialog.transient(self.root)
        
        main_frame = ttk.Frame(dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Python聚源仓项目，是一款AI智能编译器，由骏骏\n爱编程开发，其他人辅助帮忙开发，具有AI分析代码，A\nI优化代码，AI上下文理解等功能，完全免费，完全\n免费开源。\n官网：https://www.juyuancang.cn\n反馈邮箱：junjunloveprogramming@juyuancang.cn\n当前版本：1.0.6", font=('等线', 12)).pack(pady=10)

        about_button = [
            ("打开官网", self.open_official_website),
            ("复制邮箱", self.copy_email), 
        ]
        
        for text,command in about_button:
            btn = ttk.Button(main_frame, text=text, command=command).pack(pady=10)

    def open_official_website(self):
        os.startfile("https://www.juyuancang.cn")

    def copy_email(self):
        pyperclip.copy("junjunloveprogramming@juyuancang.cn")

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