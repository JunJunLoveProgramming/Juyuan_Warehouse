import sys
import os
import io
import codecs

def fix_all_encoding():
    """全面修复编码问题"""
    
    # 修复标准流编码
    def fix_stream(stream):
        try:
            if stream.encoding != 'utf-8':
                if hasattr(stream, 'buffer'):
                    return io.TextIOWrapper(stream.buffer, encoding='utf-8', errors='replace')
                else:
                    return codecs.getwriter('utf-8')(stream.buffer)
        except:
            return stream
        return stream
    
    sys.stdout = fix_stream(sys.stdout)
    sys.stderr = fix_stream(sys.stderr)
    
    # Windows控制台设置
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleOutputCP(65001)  # UTF-8
            kernel32.SetConsoleCP(65001)        # UTF-8
        except:
            pass
    
    # 设置默认编码
    try:
        if hasattr(sys, 'setdefaultencoding'):
            sys.setdefaultencoding('utf-8')
    except:
        pass
    
    print("编码设置已修复 - UTF-8")

# 自动执行修复
fix_all_encoding()