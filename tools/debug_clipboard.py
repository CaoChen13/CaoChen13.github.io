#!/usr/bin/env python3
"""
剪贴板调试工具

查看剪贴板中的所有格式，帮助诊断问题
"""

import sys
from pathlib import Path

def check_clipboard():
    """检查剪贴板内容和格式"""
    try:
        import pyperclip

        # 获取纯文本
        text = pyperclip.paste()

        print("=" * 60)
        print("剪贴板诊断工具")
        print("=" * 60)
        print()

        print(f"📋 纯文本长度: {len(text)} 字符")
        print()
        print("📝 纯文本内容（前 200 字符）:")
        print("-" * 60)
        print(text[:200])
        if len(text) > 200:
            print("...")
        print("-" * 60)
        print()

        # 检查是否包含 HTML 标记
        has_html = '<html' in text.lower() or '<span' in text.lower() or '<p' in text.lower()
        has_rtf = '\\rtf' in text

        print("🔍 格式检测:")
        print(f"  HTML 格式: {'✓ 检测到' if has_html else '✗ 未检测到'}")
        print(f"  RTF 格式:  {'✓ 检测到' if has_rtf else '✗ 未检测到'}")
        print()

        if not has_html and not has_rtf:
            print("⚠️  问题: 剪贴板只有纯文本，没有格式信息！")
            print()
            print("可能原因:")
            print("  1. Word 中没有实际标注红色/黄底")
            print("  2. 复制时使用了 Ctrl+Shift+V (纯文本粘贴)")
            print("  3. 从其他应用（如浏览器/记事本）复制的")
            print("  4. Word 版本问题")
            print()
            print("解决方法:")
            print("  1. 在 Word 中选中文字")
            print("  2. 点击 '开始' → '字体颜色' → 选择红色")
            print("  3. 或点击 '文本突出显示颜色' → 选择黄色")
            print("  4. 使用 Ctrl+C 复制（不要用 Ctrl+Shift+V）")
            print("  5. 重新运行本工具检查")
        else:
            print("✓ 格式信息正常！可以运行主脚本了")

            if has_html:
                print()
                print("🔧 HTML 格式示例（前 500 字符）:")
                print("-" * 60)
                print(text[:500])
                if len(text) > 500:
                    print("...")
                print("-" * 60)

        print()

        # Windows 特定检查
        if sys.platform == 'win32':
            try:
                import win32clipboard
                import win32con

                print("🪟 Windows 剪贴板格式:")
                win32clipboard.OpenClipboard()

                formats = []
                fmt = 0
                while True:
                    fmt = win32clipboard.EnumClipboardFormats(fmt)
                    if fmt == 0:
                        break
                    try:
                        fmt_name = win32clipboard.GetClipboardFormatName(fmt)
                        formats.append(fmt_name)
                    except:
                        if fmt == win32con.CF_TEXT:
                            formats.append("CF_TEXT (纯文本)")
                        elif fmt == win32con.CF_UNICODETEXT:
                            formats.append("CF_UNICODETEXT (Unicode 文本)")
                        elif fmt == 49380:  # HTML Format
                            formats.append("HTML Format ✓")
                        elif fmt == 49471:  # Rich Text Format
                            formats.append("Rich Text Format ✓")

                win32clipboard.CloseClipboard()

                print()
                for fmt in formats:
                    print(f"  • {fmt}")

                has_rich_format = any('HTML' in f or 'Rich Text' in f for f in formats)
                if not has_rich_format:
                    print()
                    print("  ⚠️  剪贴板中没有富文本格式！")

            except ImportError:
                print("  提示: 安装 pywin32 可以查看更多格式信息")
                print("  pip install pywin32")

    except ImportError:
        print("❌ 错误: 未安装 pyperclip")
        print("请运行: pip install pyperclip")
        return

    except Exception as e:
        print(f"❌ 错误: {e}")
        return

    print()
    print("=" * 60)
    input("按回车键关闭...")


if __name__ == "__main__":
    check_clipboard()
