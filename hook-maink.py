# hook-maink.py
from PyInstaller.utils.hooks import collect_all
import PyInstaller.__main__ as pm

datas, binaries, hiddenimports = collect_all('maink')

class pmPackage:
    def __init__(self):
        self.tagList = []#在列表里填入键值，自动生成全否定字典
        self.tagDic = {'--onefile':True,'--windowed':True}
        self.__icon = ''
        self.__fileName = None

    def runPachage(self):
        pm.run(self._getTrueList())


    def _getTrueList(self):
        result = []
        result.append(self.__fileName)


        for i in self.tagDic.keys():
            if self.tagDic[i]:
                result.append(i)

        result.append(self.__icon)
        return  result
    def setFileName(self,name):
        self.__fileName = name

    def setIcon(self,name):
        self.__icon = f'-i{name}'

if __name__ == "__main__":
    pmK = pmPackage()
    pmK.tagDic['--windowed'] = False
    pmK.setFileName("test.py")
    pmK.setIcon("neko.ico")
    pmK.runPachage()