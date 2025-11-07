# hook-maink.py
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('maink')