import re

class backEndprocessing:
    def __init__(self):
        self.KeyWordList = ["def","class","import","pass","True","False","for","in","continue","if","else","elif","while","return","and","or","not","None","as","with","from","try","except","finally","raise","lambda","is","global","nonlocal","yield","async","await","print","input"]
        self.Tag = "keyword"  # 设置默认标签

    def insertColorTag(self, text, parent):
        """插入颜色标签 - 修复版本"""
        try:
            if not text or not parent:
                return
                
            for p in self.KeyWordList:
                self._insertColorTag(text, parent, p)
        except Exception as e:
            print(f"插入颜色标签失败: {e}")

    def _insertColorTag(self, text, parent, pattern):
        """插入单个颜色标签 - 修复版本"""
        try:
            lines = text.split("\n")
            for i, line in enumerate(lines):
                # 使用正则表达式查找所有匹配项
                matches = re.finditer(r'\b' + re.escape(pattern) + r'\b', line)
                for match in matches:
                    start_index = f"{i+1}.{match.start()}"
                    end_index = f"{i+1}.{match.end()}"
                    parent.tag_add(self.Tag, start_index, end_index)
        except Exception as e:
            print(f"插入单个颜色标签失败: {e}")

    def setTagKeyWord(self, tag_name):
        """设置标签关键字"""
        self.Tag = tag_name

    def __translateFormat(self, text):
        """格式化转换（预留方法）"""
        pass