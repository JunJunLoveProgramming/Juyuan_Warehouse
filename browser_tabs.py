import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import threading
from PIL import Image, ImageTk
import markdown
import html2text
import webbrowser
import tempfile

class BrowserTabSystem:
    def __init__(self, parent, code_editor_ref):
        self.parent = parent
        self.code_editor_ref = code_editor_ref
        self.tabs = {}
        self.current_tab = None
        
        # 创建标签栏容器
        self.tab_frame = ttk.Frame(parent)
        self.tab_frame.pack(fill=tk.X, side=tk.TOP)
        
        # 标签栏
        self.tab_bar = ttk.Frame(self.tab_frame)
        self.tab_bar.pack(fill=tk.X, side=tk.TOP)
        
        # 添加标签按钮
        self.add_tab_btn = tk.Button(self.tab_bar, text="+", font=('等线', 12, 'bold'),
                                   command=self.add_new_tab, width=3, relief='flat')
        self.add_tab_btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 标签容器
        self.tab_container = ttk.Frame(self.tab_frame)
        self.tab_container.pack(fill=tk.X, side=tk.TOP)
        
        # 内容区域
        self.content_frame = ttk.Frame(parent)
        self.content_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        
        # 默认添加一个Python标签
        self.add_new_tab("Python文件", "python")
    
    def add_new_tab(self, title=None, tab_type="python"):
        """添加新标签页"""
        if not title:
            tab_count = len(self.tabs) + 1
            title = f"新标签 {tab_count}"
        
        # 创建标签按钮
        tab_btn = ttk.Frame(self.tab_container)
        tab_btn.pack(side=tk.LEFT, padx=1, pady=2)
        
        # 标签文本
        tab_label = tk.Label(tab_btn, text=title, font=('等线', 10), 
                           padx=8, pady=4, relief='raised', bg='#f0f0f0')
        tab_label.pack(side=tk.LEFT)
        
        # 关闭按钮
        close_btn = tk.Label(tab_btn, text="×", font=('等线', 12, 'bold'),
                           padx=4, pady=2, fg='red', cursor='hand2')
        close_btn.pack(side=tk.LEFT, padx=(2, 0))
        
        # 创建内容区域
        content_area = ttk.Frame(self.content_frame)
        
        if tab_type == "python":
            # Python代码编辑器
            text_widget = scrolledtext.ScrolledText(content_area, wrap=tk.WORD, 
                                                  font=("Consolas", 12))
            text_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # 配置语法高亮
            text_widget.tag_configure("keyword", foreground="blue", 
                                    font=("Consolas", 12, "bold"))
            
            # 绑定语法高亮
            text_widget.bind("<KeyRelease>", lambda e: self.code_editor_ref.apply_syntax_highlighting())
            
        elif tab_type == "html":
            # HTML编辑器 - 分屏显示
            html_frame = ttk.Frame(content_area)
            html_frame.pack(fill=tk.BOTH, expand=True)
            
            # 左侧HTML编辑器
            left_frame = ttk.Frame(html_frame)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            ttk.Label(left_frame, text="HTML编辑器", font=('等线', 11)).pack(pady=2)
            html_editor = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD,
                                                  font=("Consolas", 11))
            html_editor.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # 右侧预览
            right_frame = ttk.Frame(html_frame)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            
            preview_header = ttk.Frame(right_frame)
            preview_header.pack(fill=tk.X, pady=2)
            ttk.Label(preview_header, text="实时预览", font=('等线', 11)).pack(side=tk.LEFT)
            
            preview_btn = ttk.Button(preview_header, text="刷新预览",
                                  command=lambda: self.refresh_html_preview(html_editor, html_preview))
            preview_btn.pack(side=tk.RIGHT, padx=5)
            
            html_preview = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD,
                                                   font=("等线", 11))
            html_preview.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            text_widget = html_editor
            
            # 绑定实时预览
            html_editor.bind("<KeyRelease>", 
                           lambda e: self.refresh_html_preview(html_editor, html_preview))
            
        elif tab_type == "markdown":
            # Markdown编辑器 - 分屏显示
            md_frame = ttk.Frame(content_area)
            md_frame.pack(fill=tk.BOTH, expand=True)
            
            # 左侧Markdown编辑器
            left_frame = ttk.Frame(md_frame)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            ttk.Label(left_frame, text="Markdown编辑器", font=('等线', 11)).pack(pady=2)
            md_editor = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD,
                                                font=("Consolas", 11))
            md_editor.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            # 右侧HTML预览
            right_frame = ttk.Frame(md_frame)
            right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
            
            preview_header = ttk.Frame(right_frame)
            preview_header.pack(fill=tk.X, pady=2)
            ttk.Label(preview_header, text="HTML预览", font=('等线', 11)).pack(side=tk.LEFT)
            
            preview_btn = ttk.Button(preview_header, text="刷新预览",
                                  command=lambda: self.refresh_markdown_preview(md_editor, md_preview))
            preview_btn.pack(side=tk.RIGHT, padx=5)
            
            md_preview = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD,
                                                 font=("等线", 11))
            md_preview.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
            
            text_widget = md_editor
            
            # 绑定实时预览
            md_editor.bind("<KeyRelease>", 
                         lambda e: self.refresh_markdown_preview(md_editor, md_preview))
        
        # 隐藏所有内容区域
        content_area.pack_forget()
        
        # 存储标签信息
        tab_id = len(self.tabs)
        self.tabs[tab_id] = {
            'frame': tab_btn,
            'label': tab_label,
            'close_btn': close_btn,
            'content': content_area,
            'text_widget': text_widget,
            'title': title,
            'type': tab_type,
            'file_path': None,
            'modified': False
        }
        
        # 绑定事件
        tab_label.bind("<Button-1>", lambda e, tid=tab_id: self.switch_tab(tid))
        close_btn.bind("<Button-1>", lambda e, tid=tab_id: self.close_tab(tid))
        
        # 切换到新标签
        self.switch_tab(tab_id)
        
        return tab_id
    
    def switch_tab(self, tab_id):
        """切换到指定标签页"""
        # 隐藏当前标签内容
        if self.current_tab is not None:
            self.tabs[self.current_tab]['content'].pack_forget()
            self.tabs[self.current_tab]['label'].config(bg='#f0f0f0')
        
        # 显示新标签内容
        self.tabs[tab_id]['content'].pack(fill=tk.BOTH, expand=True)
        self.tabs[tab_id]['label'].config(bg='#d0d0d0')
        self.current_tab = tab_id
        
        # 更新主编辑器的引用
        if hasattr(self.code_editor_ref, 'code_text'):
            current_text_widget = self.tabs[tab_id]['text_widget']
            self.code_editor_ref.code_text = current_text_widget
            
            # 应用语法高亮
            if self.tabs[tab_id]['type'] == 'python':
                self.code_editor_ref.apply_syntax_highlighting()
    
    def close_tab(self, tab_id):
        """关闭标签页"""
        if len(self.tabs) <= 1:
            messagebox.showinfo("提示", "至少保留一个标签页")
            return
        
        # 检查是否有未保存的修改
        if self.tabs[tab_id]['modified']:
            result = messagebox.askyesnocancel("保存文件", 
                                             "文件已修改，是否保存？",
                                             icon=messagebox.WARNING)
            if result is None:  # 取消
                return
            elif result:  # 是，保存
                self.save_tab_file(tab_id)
        
        # 移除标签
        self.tabs[tab_id]['frame'].destroy()
        self.tabs[tab_id]['content'].destroy()
        
        # 从字典中移除
        del self.tabs[tab_id]
        
        # 切换到其他标签
        remaining_tabs = list(self.tabs.keys())
        if remaining_tabs:
            self.switch_tab(remaining_tabs[0])
    
    def refresh_html_preview(self, editor, preview):
        """刷新HTML预览"""
        try:
            html_content = editor.get(1.0, tk.END)
            preview.config(state=tk.NORMAL)
            preview.delete(1.0, tk.END)
            preview.insert(1.0, html_content)
            preview.config(state=tk.DISABLED)
        except Exception as e:
            preview.config(state=tk.NORMAL)
            preview.delete(1.0, tk.END)
            preview.insert(1.0, f"预览错误: {str(e)}")
            preview.config(state=tk.DISABLED)
    
    def refresh_markdown_preview(self, editor, preview):
        """刷新Markdown预览"""
        try:
            md_content = editor.get(1.0, tk.END)
            html_content = markdown.markdown(md_content)
            preview.config(state=tk.NORMAL)
            preview.delete(1.0, tk.END)
            preview.insert(1.0, html_content)
            preview.config(state=tk.DISABLED)
        except Exception as e:
            preview.config(state=tk.NORMAL)
            preview.delete(1.0, tk.END)
            preview.insert(1.0, f"预览错误: {str(e)}")
            preview.config(state=tk.DISABLED)
    
    def open_file_in_tab(self, file_path):
        """在标签页中打开文件"""
        if not os.path.exists(file_path):
            return
        
        # 根据文件类型确定标签类型
        if file_path.endswith('.html') or file_path.endswith('.htm'):
            tab_type = "html"
        elif file_path.endswith('.md') or file_path.endswith('.markdown'):
            tab_type = "markdown"
        else:
            tab_type = "python"
        
        # 创建新标签
        file_name = os.path.basename(file_path)
        tab_id = self.add_new_tab(file_name, tab_type)
        
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
        
        # 设置内容
        text_widget = self.tabs[tab_id]['text_widget']
        text_widget.delete(1.0, tk.END)
        text_widget.insert(1.0, content)
        
        # 更新标签信息
        self.tabs[tab_id]['file_path'] = file_path
        self.tabs[tab_id]['modified'] = False
        
        # 应用语法高亮
        if tab_type == 'python':
            self.code_editor_ref.apply_syntax_highlighting()
        
        # 如果是HTML或Markdown，刷新预览
        if tab_type == 'html':
            self.refresh_html_preview(text_widget, self.tabs[tab_id]['content'].winfo_children()[0].winfo_children()[1].winfo_children()[1])
        elif tab_type == 'markdown':
            self.refresh_markdown_preview(text_widget, self.tabs[tab_id]['content'].winfo_children()[0].winfo_children()[1].winfo_children()[1])
    
    def save_current_tab(self):
        """保存当前标签页"""
        if self.current_tab is None:
            return False
        
        tab = self.tabs[self.current_tab]
        if tab['file_path']:
            return self.save_tab_file(self.current_tab)
        else:
            return self.save_tab_file_as(self.current_tab)
    
    def save_tab_file(self, tab_id):
        """保存标签页文件"""
        try:
            tab = self.tabs[tab_id]
            content = tab['text_widget'].get(1.0, tk.END)
            
            with open(tab['file_path'], 'w', encoding='utf-8') as f:
                f.write(content)
            
            tab['modified'] = False
            self.update_tab_title(tab_id, os.path.basename(tab['file_path']))
            
            # 显示保存成功消息
            if hasattr(self.code_editor_ref, 'add_info_message'):
                self.code_editor_ref.add_info_message(f"已保存文件: {tab['file_path']}", "success")
                
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            return False
    
    def save_tab_file_as(self, tab_id):
        """另存为标签页文件"""
        try:
            tab = self.tabs[tab_id]
            file_types = []
            
            if tab['type'] == 'html':
                file_types = [("HTML文件", "*.html"), ("所有文件", "*.*")]
            elif tab['type'] == 'markdown':
                file_types = [("Markdown文件", "*.md"), ("所有文件", "*.*")]
            else:
                file_types = [("Python文件", "*.py"), ("所有文件", "*.*")]
            
            file_path = tk.filedialog.asksaveasfilename(
                defaultextension=file_types[0][1].replace("*", ""),
                filetypes=file_types
            )
            
            if file_path:
                tab['file_path'] = file_path
                return self.save_tab_file(tab_id)
            return False
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")
            return False
    
    def update_tab_title(self, tab_id, title):
        """更新标签标题"""
        tab = self.tabs[tab_id]
        tab['title'] = title
        tab['label'].config(text=title)
    
    def get_current_text_widget(self):
        """获取当前标签页的文本组件"""
        if self.current_tab is not None:
            return self.tabs[self.current_tab]['text_widget']
        return None
    
    def get_current_tab_type(self):
        """获取当前标签页类型"""
        if self.current_tab is not None:
            return self.tabs[self.current_tab]['type']
        return None
    
    def get_current_tab_content(self):
        """获取当前标签页内容"""
        if self.current_tab is not None:
            tab = self.tabs[self.current_tab]
            return tab['text_widget'].get(1.0, tk.END).strip()
        return ""
    
    def run_html_in_browser(self, tab_id=None):
        """在系统浏览器中运行HTML"""
        if tab_id is None:
            tab_id = self.current_tab
        
        if tab_id is None or self.tabs[tab_id]['type'] != 'html':
            messagebox.showwarning("警告", "请先打开或切换到HTML文件")
            return False
        
        try:
            tab = self.tabs[tab_id]
            html_content = tab['text_widget'].get(1.0, tk.END)
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(html_content)
                temp_file = f.name
            
            # 在系统默认浏览器中打开
            webbrowser.open(f'file://{temp_file}')
            
            # 显示成功消息
            if hasattr(self.code_editor_ref, 'add_info_message'):
                self.code_editor_ref.add_info_message("已在浏览器中打开HTML文件", "success")
            
            # 稍后删除临时文件
            threading.Timer(5.0, lambda: os.unlink(temp_file) if os.path.exists(temp_file) else None).start()
            
            return True
            
        except Exception as e:
            messagebox.showerror("错误", f"运行HTML失败: {str(e)}")
            return False