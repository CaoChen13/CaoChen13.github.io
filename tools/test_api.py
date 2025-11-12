#!/usr/bin/env python3
"""
API 调试工具 - 测试不同的调用方式
"""

import json
import requests
from pathlib import Path
from anthropic import Anthropic


def test_with_requests(api_key: str, base_url: str, model: str):
    """使用 requests 直接调用（模拟其他软件）"""
    print("=" * 60)
    print("方法 1: 使用 requests 库直接调用")
    print("=" * 60)

    url = base_url
    if not url.endswith('/messages'):
        url = url + '/messages'

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01'
    }

    data = {
        'model': model,
        'max_tokens': 100,
        'messages': [
            {
                'role': 'user',
                'content': 'Say "Hello" in Chinese.'
            }
        ]
    }

    print(f"\n请求 URL: {url}")
    print(f"请求头: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    print(f"请求体: {json.dumps(data, indent=2, ensure_ascii=False)}")
    print("\n发送请求...")

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ 成功！响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return True
        else:
            print(f"\n✗ 失败！响应内容:")
            print(response.text)
            return False

    except Exception as e:
        print(f"\n✗ 请求失败: {e}")
        return False


def test_with_sdk(api_key: str, base_url: str, model: str):
    """使用 Anthropic SDK 调用（当前脚本使用的方式）"""
    print("\n" + "=" * 60)
    print("方法 2: 使用 Anthropic SDK")
    print("=" * 60)

    # 去掉 /messages 后缀（如果有）
    clean_base_url = base_url
    if clean_base_url.endswith('/messages'):
        clean_base_url = clean_base_url[:-9]

    print(f"\n传给 SDK 的 base_url: {clean_base_url}")
    print(f"SDK 会自动添加 /messages，实际请求: {clean_base_url}/messages")
    print("\n发送请求...")

    try:
        client = Anthropic(api_key=api_key, base_url=clean_base_url)

        response = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[
                {
                    'role': 'user',
                    'content': 'Say "Hello" in Chinese.'
                }
            ]
        )

        print(f"\n✓ 成功！响应内容:")
        print(f"ID: {response.id}")
        print(f"内容: {response.content[0].text}")
        return True

    except Exception as e:
        print(f"\n✗ 失败: {e}")
        print(f"\n错误详情:")
        print(f"  错误类型: {type(e).__name__}")
        print(f"  错误信息: {str(e)}")
        return False


def main():
    # 读取配置
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        print("错误: 找不到 config.json")
        return

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    api_key = config.get('claude_api_key')
    base_url = config.get('claude_api_base_url', 'https://api.anthropic.com/v1')
    model = config.get('claude_model', 'claude-sonnet-4-5-20250929')

    print("读取配置:")
    print(f"  API Key: {api_key[:15]}...")
    print(f"  Base URL: {base_url}")
    print(f"  Model: {model}")
    print()

    # 测试方法 1: requests
    result1 = test_with_requests(api_key, base_url, model)

    # 测试方法 2: SDK
    result2 = test_with_sdk(api_key, base_url, model)

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"requests 直接调用: {'✓ 成功' if result1 else '✗ 失败'}")
    print(f"Anthropic SDK 调用: {'✓ 成功' if result2 else '✗ 失败'}")
    print()

    if result1 and not result2:
        print("诊断结果:")
        print("  - requests 能成功说明 API 配置正确")
        print("  - SDK 失败说明代理站点可能不完全兼容 Anthropic SDK")
        print()
        print("解决方案:")
        print("  需要修改脚本，使用 requests 代替 Anthropic SDK")
    elif not result1 and not result2:
        print("诊断结果:")
        print("  - 两种方式都失败，说明 API 配置可能有问题")
        print()
        print("请检查:")
        print("  1. API Key 是否正确")
        print("  2. Base URL 是否正确")
        print("  3. 模型名是否正确")
        print("  4. 账户余额是否充足")
    elif result1 and result2:
        print("诊断结果:")
        print("  ✓ 两种方式都成功！API 配置正确")

    print()
    input("按回车键关闭...")


if __name__ == "__main__":
    main()
