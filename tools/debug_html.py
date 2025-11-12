#!/usr/bin/env python3
"""
HTML 调试工具 - 查看 Word 复制的实际 HTML 结构
"""

import sys
from pathlib import Path


def debug_html():
    """查看剪贴板中的 HTML 结构"""
    # 读取剪贴板
    if sys.platform == 'win32':
        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            try:
                html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
                if win32clipboard.IsClipboardFormatAvailable(html_format):
                    html_data = win32clipboard.GetClipboardData(html_format)
                    win32clipboard.CloseClipboard()

                    if isinstance(html_data, bytes):
                        html_data = html_data.decode('utf-8', errors='ignore')

                    # 提取 HTML 内容
                    html_start = html_data.find('<html')
                    if html_start == -1:
                        html_start = html_data.find('<HTML')
                    if html_start != -1:
                        html_content = html_data[html_start:]

                        # 保存到文件
                        output_file = Path(__file__).parent / "clipboard_debug.html"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(html_content)

                        print(f"HTML 内容已保存到: {output_file}")
                        print("\n前 2000 字符:")
                        print("=" * 60)
                        print(html_content[:2000])
                        print("=" * 60)
                        print(f"\n完整内容长度: {len(html_content)} 字符")
                        print(f"请用浏览器或编辑器打开 {output_file.name} 查看完整结构")
                        return

            except Exception as e:
                print(f"读取失败: {e}")
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass

        except ImportError:
            print("需要安装 pywin32: pip install pywin32")
            return

    print("没有检测到 HTML 格式")


if __name__ == "__main__":
    debug_html()
    input("\n按回车键关闭...")
