# ai_compiler.py
import datetime

import requests
import json
import os
import re

from openai import OpenAI
import sqlite3
import textwrap #使"""格式的字符串符合缩进，不然读起代码太痛苦了
from typing import List, Dict, Any
testApi = "sk-1bae42c249c54cb1b40aaac2458cddbe"
class SmartAICompilerError(Exception):
    pass
class SmartAICompiler:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.conversation_history = []
        self.code_context = ""
        
        # 更智能的系统提示
        self.system_prompt = textwrap.dedent("""你是一个专业的Python编程助手，具有以下特点：

                                                1. 代码理解能力强，能深入分析代码逻辑和结构
                                                2. 提供实用的优化建议和最佳实践
                                                3. 能够生成高质量、可运行的代码示例
                                                4. 对Python标准库和流行框架有深入了解
                                                5. 回答友好、详细且专业

                                                请按照以下格式提供代码：
                                                ```python
                                                # 清晰的注释说明
                                                你的代码
                                                对于复杂问题，请分步骤解释。""")

        self.EditedByAI_prompt = textwrap.dedent("""
                                                    你是一个代码生成工具，仅返回纯源码，不添加任何额外内容：
                                                    1. 在第一行注明文件名与扩展名。格式为./文件名.扩展名
                                                    2. 不写解释、不写注释、不说明思路；
                                                    3. 不使用 ``` 代码块包裹，直接返回代码文本；
                                                    4. 确保代码可运行，语法正确；
                                                    5. 严格按照用户需求生成对应语言的代码（优先选择主流语言，如python、java、c++）。
                                                    
                                                    当前项目框架与源码如下：
                                                """)#使用该变量时加上源码与框架
        self._createSQLdb_config_init()#初始化数据库
        self.conn_config = sqlite3.connect("configs/config.db")
        self.cu_config = self.conn_config.cursor()#专门操控config.db的游标
        self.conversation_history_FBEBAI = [] #不存储提示词，只存储纯粹的上下文字典
        self.using_database_FBEBAI = None # 指示当前使用中的database/所在的聊天界面/开发中的project   建议每次窗口变为前台窗口（对话界面被点击）时修改

    def set_api_key(self, api_key):
        """设置API密钥"""
        self.api_key = api_key

    def set_code_context(self, code):
        """设置当前代码上下文"""
        self.code_context = code

    def analyze_code_quality(self, code):
        """深度分析代码质量"""
        analysis_prompt = textwrap.dedent(f"""
                                        请深度分析这段Python代码：
                                        {code}

                                        请从以下方面分析：

                                        1、代码结构和可读性

                                        2、算法效率和性能

                                        3、错误处理和边界情况

                                        4、代码风格和最佳实践

                                        5、潜在的安全问题

                                        6、具体的改进建议

                                        请给出详细的评分（1-10分）和具体建议。""")
        return self._call_api(analysis_prompt)

    def explain_code_detailed(self, code):
        """详细解释代码"""
        explanation_prompt = textwrap.dedent(f"""
                                                请详细解释这段代码：
                                                {code}

                                                请包括：

                                                1、代码的总体功能和目的

                                                2、关键函数和类的作用

                                                3、算法逻辑和流程

                                                4、重要的变量和数据结构

                                                5、可能的用例和应用场景

                                                6、学习要点和关键概念""")
        
        return self._call_api(explanation_prompt)
    
    def optimize_code(self, code):
        """优化代码并提供多种方案"""
        optimization_prompt = textwrap.dedent(f"""
                                                请优化这段代码：
                                                {code}

                                                请提供：

                                                1、性能优化方案

                                                2、可读性改进

                                                3、错误处理增强

                                                4、代码重构建议

                                                5、最佳实践应用

                                                对于每个优化点，请说明：

                                                ·优化前的问题

                                                ·优化后的改进

                                                ·为什么这样优化更好""")
        
        return self._call_api(optimization_prompt)
    
    def generate_code(self, requirements):
        """根据需求生成代码"""
        generation_prompt = textwrap.dedent(f"""
                                            根据以下需求生成Python代码：

                                            {requirements}

                                            请生成：

                                            1、完整可运行的代码

                                            2、清晰的注释说明

                                            3、使用示例

                                            4、必要的错误处理

                                            5、符合Python最佳实践

                                            确保代码：

                                            ·结构清晰

                                            ·易于理解

                                            ·可扩展

                                            ·有适当的文档字符串""")
        return self._call_api(generation_prompt)

    def debug_code(self, code, error_message=None):
        """调试代码问题"""
        if error_message:
            debug_prompt = textwrap.dedent(f"""
                                            请帮助调试这段代码：
                                            {code}

                                            遇到的错误：
                                            {error_message}
    
                                            请：

                                            1、分析错误原因

                                            2、提供修复方案

                                            3、解释修复原理

                                            4、提供完整的修复后代码

                                            5、建议如何避免类似错误""")
        else:
            debug_prompt = textwrap.dedent(f"""
                                            请检查这段代码的潜在问题：

                                            {code}

                                            请：

                                            1、找出可能的bug和问题

                                            2、提供修复建议

                                            3、解释问题原因

                                            4、提供改进后的代码

                                            5、给出测试建议""")
        return self._call_api(debug_prompt)
    
    def chat_with_context(self, message, code_context=None):
        """带上下文的智能对话"""
        if code_context:
            context =textwrap.dedent(f"""
                                    当前代码上下文：
                                    {code_context}
                                    用户问题：{message}""")
        else:
            context = f"用户问题：{message}"
            chat_prompt =textwrap.dedent(f"""
                                        基于当前对话上下文，回答用户问题：
                                        {context}

                                        请提供：

                                        1、直接、准确的回答

                                        2、相关的代码示例（如适用）

                                        3、最佳实践建议

                                        4、进一步的学习资源（如需要）

                                        5、友好的语气和专业的表达""")
        return self._call_api(chat_prompt)
    
    def suggest_improvements(self, code):
        """提供代码改进建议"""
        improvement_prompt = textwrap.dedent(f"""
                                            为这段代码提供改进建议：
                                            {code}

                                            请从以下角度提供具体建议：

                                            1、代码结构和组织

                                            2、函数设计和模块化

                                            3、性能优化机会

                                            4、错误处理完善

                                            5、代码可测试性

                                            6、可维护性提升

                                            7、安全性考虑

                                            对每个建议，请提供：

                                            ·当前问题描述

                                            ·改进方案

                                            ·改进后的代码示例

                                            ·改进带来的好处""")
        return self._call_api(improvement_prompt)
    
    def teach_concept(self, concept, level="beginner"):
        """教学特定编程概念"""
        teaching_prompt = textwrap.dedent(f"""
                                        请以{level}级别讲解以下编程概念：
                                        {concept}

                                        请提供：

                                        1、清晰的概念定义

                                        2、实际应用场景

                                        3、代码示例

                                        4、常见误区

                                        5、最佳实践

                                        6、进一步学习路径

                                        使用通俗易懂的语言，配合具体例子。""")
        return self._call_api(teaching_prompt)

    def code_review(self, code):
        """代码审查"""
        review_prompt = textwrap.dedent(f"""
                                        对以下代码进行专业审查：
                                        请提供详细的代码审查报告，包括：

                                        1、代码质量评分（1-10）

                                        2、优点和亮点

                                        3、存在的问题和改进点

                                        4、安全考虑

                                        5、性能建议

                                        6、可维护性评估

                                        7、具体的修改建议

                                        格式化为清晰的报告形式。""")
        
        return self._call_api(review_prompt)

    def _call_api(self, prompt):
        """调用API的统一方法"""
        if not self.api_key:
            return "错误：请先设置Deepseek API密钥"
        
        # 构建消息历史
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # 添加上下文对话历史（限制长度）
        for msg in self.conversation_history[-6:]:  # 保留最近6条对话
            messages.insert(1, msg)
        
        data = {
            "model": "deepseek-coder",
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            ai_reply = result["choices"][0]["message"]["content"]
            
            # 保存到对话历史
            self.conversation_history.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": ai_reply}
            ])
            
            # 限制对话历史长度
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return ai_reply
            
        except requests.exceptions.Timeout:
            return "请求超时，请稍后重试。"
        except requests.exceptions.RequestException as e:
            return f"API调用失败：{str(e)}"
        except Exception as e:
            return f"处理响应时出错：{str(e)}"

    def createProjectStruct_FBEBAI(self,path="E:/Juyuan_Warehouse_Projects/",name="exampleProjcet"): #创建专为全ai开发流程提供的项目文件夹
        #工作流程  排查文件名合法性-在config表格中注册项目-在指定的path处创建项目目录-在configs文件夹创建以项目名命名的db文件
        for keyWords in ["<",">",":","/","\\","|","?","*"]: #  检测有无非法字符出现在项目名称中  排查文件名合法性
            if keyWords in name:
                raise SmartAICompilerError(f"database创建时出现了非法字符{keyWords}")
        chat_log_base = f"{name}.db"

        self.cu_config.execute("insert into config_table (chat_log_base,create_time,bindProject) value(?,?,?)",(chat_log_base,datetime.datetime.now(),path)) #在config表中注册此项目

        os.makedirs(name=f"{path}{name}/",exist_ok=True) # 在指定的path处创建目录


        conn = sqlite3.connect(f"configs/conversation_history_dir_FBEBAI/{chat_log_base}") # 在configs文件夹创建以项目名命名的db文件
        cu = conn.cursor()
        try:
            cu.execute("create table chat_log(role text,log_time text,context text)") # 尝试创建表格，若表格存在则忽略
            cu.close()
            conn.commit()
            conn.close()

        except sqlite3.OperationalError:
            print("调试：configs/config.db 已经存在，config_table表格已存在于db文件中。")

    def _readProjectStruct_FBEBAI(self):#读取项目结构，用于向ai上传
        pass

    def _createMessageList_FBEBAI(self,prompt,askByUser,project_struct): #为_call_api_ForBeEditedByAI方法准备message列表
        #缺少上传项目结构
        prompt += prompt+ textwrap.dedent(project_struct)

        sys_dic = {"role": "system", "content": prompt}
        mes = [sys_dic]
        for i in self.conversation_history_FBEBAI:#遍历历史记录列表
            mes.append(i)#向his列表添加字典
        usr_dic = {"role":"user","content":askByUser}
        mes.append(usr_dic)  # 加入用户发问
        # 形成  系统提示
        #      历史记录
        #      新的请求  的三层结构
        return mes
    def check_Conversation_history_FBEBAI(self,message):
        temp_i = None  # 检查聊天记录合法性
        for i in self.conversation_history_FBEBAI:

            temp =  None
            for x,y in enumerate(i.keys()):

                if x > 1:#键值只应有2个
                    raise SmartAICompilerError(f"聊天记录每个片段只因有2个键，{i}中出现了错误")
                if y != "role" or y != "content": #如果出现了未知的键值
                    raise  SmartAICompilerError(f"聊天记录片段中出现了未知的键，{i}中出现了错误")
                if x == 0:#记录第一个键
                    temp = y
                if y == temp:
                    raise  SmartAICompilerError(f"聊天记录片段中出现了重复的键，{i}中出现了错误")
                temp = None
            if i["role"] == temp_i:
                raise SmartAICompilerError(f"聊天记录中出现了2个连续的角色对话，{i}中出现了错误")




    def _call_api_FBEBAI(self,message:list ,api = None,using_database = None): #message必须使用_createMessageList_FBEBAI
        #全新的升级后的 Api调用方法
        if api == None:#api默认为空，方便测试填写api或其它用途 api不被填入时，自动使用类属性api_key
            api = self.api_key
        if using_database == None: # using_database默认为空，方便测试填写使用中的database  using_database不被填入时，自动使用类属性using_database
            using_database = self.using_database_FBEBAI


        client = OpenAI(
            api_key=api,
            base_url="https://api.deepseek.com")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=message,
            stream=False,
            temperature=0.1
        )

        return response.choices[0].message.content

    def _createSQLdb_config_init(self):#当数据库损坏，或初始化数据库时，调用该函数


        fix_dic = {False:lambda :os.mkdir(path="./configs") ,True: lambda :print("调试：configs文件夹存在")}
        fix_dic[os.path.isdir("configs")]()#检测是否存在configs文件夹，存在输出调试信息，不存在则创建。
        conn =  sqlite3.connect("configs/config.db")
        cu = conn.cursor()
        try:#尝试创建表格，若表格存在则忽略
            cu.execute("create table config_table(chat_log_base text,create_time text,bindProject text)")
            #chat_log_base应存储聊天记录的db文件相对位置，create_time以20251205为格式存储创建日期，bindProject存储AI项目的文件夹相对位置
            # ### 相对位置是指，本文件所在目录的相对路径，如本文件工作于F:\allProjectsFrom20250907\Juyuan_Warehouse103，项目存储于Juyuan_Warehouse103\projectFiles\f"{projectName}"\
            #则存储f"{projectName}"\
            #读取后f"{os.getcwd()}\projectFiles\f{projectName}"以拼接获得完整路径
            cu.close()
            conn.commit()
            conn.close()

        except sqlite3.OperationalError:
            print("调试：configs/config.db 已经存在，config_table表格已存在于db文件中。")

    def createNewConversation(self,conversation_name:str):
        if "\\"  in conversation_name or "/" in conversation_name:#这里回头改成正则表达式处理，先这样
            return TypeError("不应存在斜杠或反斜杠等特殊字符")
        self.cu_config.execute("insert into config_table(chat_log_base,create_time,bindProject) values(?,?,?)",conversation_name)
    def extract_code_blocks(self, text):
        """从回复中提取代码块"""
        code_blocks = re.findall(r'```python\n(.*?)\n```', text, re.DOTALL)
        return code_blocks

    def clear_conversation(self):
        """清空对话历史"""
        self.conversation_history = []

# 创建全局实例
_global_compiler = SmartAICompiler()

# 提供顶层函数接口
def set_api_key(api_key):
    """设置API密钥"""
    _global_compiler.set_api_key(api_key)

def set_current_code(code):
    """设置当前代码上下文"""
    _global_compiler.set_code_context(code)

def analyze(code):
    """分析代码质量"""
    return _global_compiler.analyze_code_quality(code)

def explain(code):
    """解释代码"""
    return _global_compiler.explain_code_detailed(code)

def optimize(code):
    """优化代码"""
    return _global_compiler.optimize_code(code)

def chat(message, code_context=None):
    """AI聊天"""
    return _global_compiler.chat_with_context(message, code_context)

def suggest_improvements(code):
    """提供改进建议"""
    return _global_compiler.suggest_improvements(code)

def debug(code, error_message=None):
    """调试代码"""
    return _global_compiler.debug_code(code, error_message)

def generate(requirements):
    """生成代码"""
    return _global_compiler.generate_code(requirements)

def teach(concept, level="beginner"):
    """教学概念"""
    return _global_compiler.teach_concept(concept, level)

def review(code):
    """代码审查"""
    return _global_compiler.code_review(code)

def clear_chat_history():
    """清空对话历史"""
    _global_compiler.clear_conversation()

def extract_code(text):
    """提取代码块"""
    return _global_compiler.extract_code_blocks(text)

if  __name__ == "__main__":
    #以下为全AI编写程序接口调用示例
    sac = SmartAICompiler()
