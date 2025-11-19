# hook-maink.py
from PyInstaller.utils.hooks import collect_all
import PyInstaller.__main__ as pm

datas, binaries, hiddenimports = collect_all('maink')

class pmPackage:
    def __init__(self):
        self.tagList = []#在列表里填入键值，自动生成全否定字典
        self.tagDic = {'--onefile':True,'--windowed':True}
        self.fileName = None

    def runPachage(self):
        pm.run(self._getTrueList())


    def _getTrueList(self):
        result = []
        result.append(self.fileName)

        for i in self.tagDic.keys():
            if self.tagDic[i]:
                result.append(i)
        return  result
    def setFileName(self,name):
        self.fileName = name

if __name__ == "__main__":
    pmK = pmPackage()
    pmK.tagDic['--windowed'] = False