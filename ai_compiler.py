# ai_compiler.py
import requests
import json
import os

class SimpleAICompiler:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('DEEPSEEK_API_KEY')
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.conversation = []
        
        # 添加系统提示
        self.add_system_message("你是一个Python专家，帮助分析代码、找错误、优化代码和回答问题。")
    
    def set_api_key(self, api_key):
        """设置API密钥"""
        self.api_key = api_key
    
    def add_system_message(self, message):
        """添加系统消息"""
        self.conversation.append({"role": "system", "content": message})
    
    def ask_ai(self, question, code=None):
        """向AI提问"""
        if not self.api_key:
            return "错误：请先设置Deepseek API密钥"
        
        # 如果有代码，把代码也发送给AI
        if code:
            full_question = f"{question}\n\n相关代码：\n```python\n{code}\n```"
        else:
            full_question = question
        
        # 添加用户问题到对话
        self.conversation.append({"role": "user", "content": full_question})
        
        # 准备请求数据
        data = {
            "model": "deepseek-coder",
            "messages": self.conversation,
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            # 发送请求到AI
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            # 获取AI回复
            result = response.json()
            ai_reply = result["choices"][0]["message"]["content"]
            
            # 添加AI回复到对话
            self.conversation.append({"role": "assistant", "content": ai_reply})
            
            return ai_reply
            
        except Exception as e:
            return f"API调用失败：{str(e)}"
    
    def analyze_code(self, code):
        """分析代码"""
        question = "请分析这段Python代码，告诉我：1. 代码功能 2. 潜在问题 3. 改进建议"
        return self.ask_ai(question, code)
    
    def find_errors(self, code, error_message=""):
        """查找代码错误"""
        if error_message:
            question = f"这段代码运行时报错：{error_message}，请帮我找出问题并修复："
        else:
            question = "请检查这段代码是否有语法错误或潜在问题："
        
        return self.ask_ai(question, code)
    
    def explain_code(self, code):
        """解释代码"""
        question = "请详细解释这段代码的功能和工作原理："
        return self.ask_ai(question, code)
    
    def optimize_code(self, code):
        """优化代码"""
        question = "请优化这段代码，提高性能和可读性，并说明优化点："
        return self.ask_ai(question, code)
    
    def complete_code(self, partial_code):
        """代码补全"""
        question = "请帮我补全这段代码，保持代码风格一致："
        return self.ask_ai(question, partial_code)
    
    def chat(self, message, current_code=None):
        """普通聊天"""
        return self.ask_ai(message, current_code)

# 创建全局实例
ai_compiler = SimpleAICompiler()

# 简单易用的函数
def set_api_key(key):
    """设置API密钥"""
    ai_compiler.set_api_key(key)

def analyze(code):
    """分析代码"""
    return ai_compiler.analyze_code(code)

def find_errors(code, error_msg=""):
    """查找错误"""
    return ai_compiler.find_errors(code, error_msg)

def explain(code):
    """解释代码"""
    return ai_compiler.explain_code(code)

def optimize(code):
    """优化代码"""
    return ai_compiler.optimize_code(code)

def complete(partial_code):
    """代码补全"""
    return ai_compiler.complete_code(partial_code)

def chat(message, code=None):
    """与AI聊天"""
    return ai_compiler.chat(message, code)

# 测试
if __name__ == "__main__":
    # 设置你的API密钥（在实际使用中应该从环境变量或配置文件读取）
    set_api_key("你的Deepseek-API密钥")
    
    # 测试代码
    test_code = """
def calculate(numbers):
    sum = 0
    for i in numbers:
        sum = sum + i
    return sum
"""
    
    print("=== 代码分析 ===")
    print(analyze(test_code))
    
    print("\n=== 代码解释 ===")
    print(explain(test_code))
    
    print("\n=== 聊天测试 ===")
    print(chat("如何让这段代码更好？", test_code))