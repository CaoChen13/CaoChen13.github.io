#!/usr/bin/env python3
"""
Word to Anki 卡片生成器 - 简化启动版

使用方法:
1. 在 Word 中标注好文本（红色=生词，黄底=搭配）
2. 复制（Ctrl+C）
3. 在 VSCode 中打开此文件
4. 点击右上角运行按钮 ▶️
5. 等待完成
"""

import sys
from pathlib import Path

# 添加工具目录到路径
tools_dir = Path(__file__).parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

# 导入主程序
try:
    from word_to_anki import main

    print("=" * 60)
    print("Word 标注 → Anki 卡片生成器")
    print("=" * 60)
    print()
    print("准备开始...")
    print("请确保:")
    print("  ✓ 已在 Word 中复制标注好的文本")
    print("  ✓ Anki 正在运行")
    print("  ✓ config.json 已配置")
    print()

    input("按回车键开始处理... ")
    print()

    # 运行主程序
    main()

    print()
    input("按回车键关闭... ")

except FileNotFoundError as e:
    print("❌ 错误: 配置文件不存在")
    print()
    print("请先设置:")
    print(f"  1. 复制 {tools_dir}/config.example.json")
    print(f"  2. 重命名为 config.json")
    print("  3. 填入你的 Claude API Key 和 Anki 设置")
    print()
    input("按回车键关闭... ")
    sys.exit(1)

except ImportError as e:
    print("❌ 错误: 缺少依赖库")
    print()
    print("请先安装依赖:")
    print(f"  cd {tools_dir}")
    print("  pip install -r requirements.txt")
    print()
    print("需要安装的库:")
    print("  - anthropic (Claude API)")
    print("  - requests (AnkiConnect)")
    print("  - pyperclip (剪贴板)")
    print()
    input("按回车键关闭... ")
    sys.exit(1)

except Exception as e:
    print(f"❌ 错误: {e}")
    print()
    input("按回车键关闭... ")
    sys.exit(1)
