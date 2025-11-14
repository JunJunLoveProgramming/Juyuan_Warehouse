import re

class backEndprocessing:
    def __init__(self):
        self.KeyWordList = ["def","class","import","pass","True","False","for","in","continue","if","else","elif","while","return","and","or","not","None","as","with","from","try","except","finally","raise","lambda","is","global","nonlocal","yield","async","await","print","input"]

    def insertColorTag(self,text,parent):
        for p in  self.KeyWordList:
            self._insertColorTag(text,parent,p)

    def _insertColorTag(self,text,parent,pattern):
        lines = text.split("\n")
        for i, line in enumerate(lines):
            # 使用正则表达式查找所有匹配项
            matches = re.finditer(r'\b' + re.escape(pattern) + r'\b', line)
            for match in matches:
                start_index = f"{i+1}.{match.start()}"
                end_index = f"{i+1}.{match.end()}"
                parent.tag_add(self.Tag, start_index, end_index)

    def setTagKeyWord(self,tag_name):
        self.Tag = tag_name

    def __translateFormat(self,text):
        pass