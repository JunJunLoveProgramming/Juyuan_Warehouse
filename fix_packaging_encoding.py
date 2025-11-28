import os
import sys
import subprocess

def fix_encoding_environment():
    """修复打包环境的编码设置"""
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = 'utf-8'
    
    # 对于Windows系统，额外设置
    if sys.platform == 'win32':
        os.environ['PYTHONUTF8'] = '1'
    
    print("编码环境已设置完成")

def run_pyinstaller_safely(cmd_args):
    """安全运行PyInstaller命令"""
    fix_encoding_environment()
    
    try:
        # 使用UTF-8编码运行命令
        process = subprocess.Popen(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时输出
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        return process.returncode == 0
        
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_pyinstaller_safely(sys.argv[1:])