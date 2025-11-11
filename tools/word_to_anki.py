#!/usr/bin/env python3
"""
Word 标注转 Anki 卡片工具

从剪贴板读取 Word 复制的内容，提取红色/黄底标记，
调用 Claude API 生成解释，通过 AnkiConnect 创建卡片。
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import requests
from anthropic import Anthropic


class RTFParser:
    """解析 RTF 格式，提取文本和格式信息"""

    def __init__(self, rtf_content: str):
        self.rtf_content = rtf_content
        self.color_table = []
        self._parse_color_table()

    def _parse_color_table(self):
        """解析 RTF 颜色表"""
        # 查找 {\colortbl;...} 部分
        match = re.search(r'\\colortbl;([^}]+)', self.rtf_content)
        if match:
            color_data = match.group(1)
            # 提取每个颜色 \red255\green0\blue0;
            colors = re.findall(r'\\red(\d+)\\green(\d+)\\blue(\d+);', color_data)
            self.color_table = [(int(r), int(g), int(b)) for r, g, b in colors]

    def _is_red_color(self, color_index: int) -> bool:
        """判断是否为红色（或接近红色）"""
        if color_index >= len(self.color_table):
            return False
        r, g, b = self.color_table[color_index]
        # 红色：R 高，G B 低
        return r > 200 and g < 100 and b < 100

    def _is_yellow_color(self, color_index: int) -> bool:
        """判断是否为黄色（或接近黄色）"""
        if color_index >= len(self.color_table):
            return False
        r, g, b = self.color_table[color_index]
        # 黄色：R G 高，B 低
        return r > 200 and g > 200 and b < 100

    def parse(self) -> List[Dict]:
        """
        解析 RTF 返回句子列表，每个句子包含标记词

        返回格式:
        [
            {
                'sentence': '原句文本',
                'marks': [
                    {'text': '标记词', 'type': 'red', 'position': (start, end)},
                    ...
                ]
            },
            ...
        ]
        """
        # 简化的 RTF 解析逻辑
        # 移除 RTF 控制字，保留纯文本和格式标记

        text_parts = []
        current_text = ''
        current_format = {'color': None, 'highlight': None}

        # 简化解析：提取文本和格式
        # 实际使用中可能需要更复杂的 RTF 解析

        # 使用正则提取所有文本段落和格式标记
        # \cf<n> = 前景色, \cb<n> 或 \highlight<n> = 背景色

        tokens = re.findall(
            r'\\cf(\d+)|\\cb(\d+)|\\highlight(\d+)|\\cf0|\\cb0|\\highlight0|[^\\{}]+|[\\{}]',
            self.rtf_content
        )

        segments = []
        current_fg_color = None
        current_bg_color = None

        for token in tokens:
            if isinstance(token, tuple):
                # 格式标记
                if token[0]:  # \cf<n>
                    current_fg_color = int(token[0]) - 1  # RTF 颜色索引从 1 开始
                elif token[1]:  # \cb<n>
                    current_bg_color = int(token[1]) - 1
                elif token[2]:  # \highlight<n>
                    current_bg_color = int(token[2]) - 1
            elif isinstance(token, str):
                if token.startswith('\\'):
                    if token == '\\cf0':
                        current_fg_color = None
                    elif token in ('\\cb0', '\\highlight0'):
                        current_bg_color = None
                    # 忽略其他控制字
                elif token not in ('{', '}'):
                    # 纯文本
                    clean_text = token.strip()
                    if clean_text:
                        mark_type = None
                        if current_fg_color is not None and self._is_red_color(current_fg_color):
                            mark_type = 'red'
                        elif current_bg_color is not None and self._is_yellow_color(current_bg_color):
                            mark_type = 'yellow'

                        segments.append({
                            'text': clean_text,
                            'mark_type': mark_type
                        })

        # 重组为句子
        sentences = self._group_into_sentences(segments)
        return sentences

    def _group_into_sentences(self, segments: List[Dict]) -> List[Dict]:
        """将文本段落按句子分组"""
        sentences = []
        current_sentence_text = ''
        current_marks = []

        for seg in segments:
            text = seg['text']
            mark_type = seg['mark_type']

            # 添加到当前句子
            start_pos = len(current_sentence_text)
            current_sentence_text += text
            end_pos = len(current_sentence_text)

            if mark_type:
                current_marks.append({
                    'text': text,
                    'type': mark_type,
                    'position': (start_pos, end_pos)
                })

            # 判断句子结束（简化：以 .!? 结尾）
            if text.rstrip().endswith(('.', '!', '?', '。', '！', '？')):
                if current_marks:  # 只保留有标记的句子
                    sentences.append({
                        'sentence': current_sentence_text.strip(),
                        'marks': current_marks
                    })
                current_sentence_text = ''
                current_marks = []

        # 处理最后一个句子
        if current_marks and current_sentence_text.strip():
            sentences.append({
                'sentence': current_sentence_text.strip(),
                'marks': current_marks
            })

        return sentences


class SimpleRTFParser:
    """简化版 RTF 解析器 - 使用 pyperclip 读取纯文本"""

    def __init__(self, html_content: str):
        """
        从剪贴板 HTML 格式解析
        Word 复制时会在剪贴板放置多种格式，HTML 格式更容易解析
        """
        self.html_content = html_content

    def parse(self) -> List[Dict]:
        """从 HTML 解析句子和标记"""
        from html.parser import HTMLParser

        class WordHTMLParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.sentences = []
                self.current_sentence = ''
                self.current_marks = []
                self.current_tag_stack = []
                self.current_style = {}

            def handle_starttag(self, tag, attrs):
                self.current_tag_stack.append(tag)
                # 检查样式
                style = dict(attrs).get('style', '')
                if 'color' in style or 'background' in style:
                    self.current_style = {'style': style}

            def handle_endtag(self, tag):
                if self.current_tag_stack and self.current_tag_stack[-1] == tag:
                    self.current_tag_stack.pop()
                self.current_style = {}

            def handle_data(self, data):
                text = data.strip()
                if not text:
                    return

                start_pos = len(self.current_sentence)
                self.current_sentence += text + ' '
                end_pos = len(self.current_sentence)

                # 检查是否有样式标记
                mark_type = None
                if self.current_style.get('style'):
                    style = self.current_style['style']
                    if 'color' in style and 'red' in style.lower():
                        mark_type = 'red'
                    elif 'background' in style and 'yellow' in style.lower():
                        mark_type = 'yellow'

                if mark_type:
                    self.current_marks.append({
                        'text': text,
                        'type': mark_type,
                        'position': (start_pos, end_pos)
                    })

                # 句子结束判断
                if text.rstrip().endswith(('.', '!', '?', '。', '！', '？')):
                    if self.current_marks:
                        self.sentences.append({
                            'sentence': self.current_sentence.strip(),
                            'marks': self.current_marks
                        })
                    self.current_sentence = ''
                    self.current_marks = []

        parser = WordHTMLParser()
        try:
            parser.feed(self.html_content)
        except Exception as e:
            print(f"HTML 解析失败: {e}")
            return []

        # 处理最后一个句子
        if parser.current_marks and parser.current_sentence.strip():
            parser.sentences.append({
                'sentence': parser.current_sentence.strip(),
                'marks': parser.current_marks
            })

        return parser.sentences


class ClaudeExplainer:
    """使用 Claude API 生成解释"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", base_url: Optional[str] = None):
        # 支持自定义 base_url（代理站点）
        if base_url:
            # 移除 /messages 后缀（如果有）
            if base_url.endswith('/messages'):
                base_url = base_url[:-9]
            self.client = Anthropic(api_key=api_key, base_url=base_url)
        else:
            self.client = Anthropic(api_key=api_key)
        self.model = model

    def explain(self, sentence: str, marks: List[Dict]) -> Optional[str]:
        """
        为标记词生成解释

        Args:
            sentence: 原句
            marks: 标记列表 [{'text': '词', 'type': 'red/yellow'}, ...]

        Returns:
            中文解释字符串，失败返回 None
        """
        # 构建提示词
        red_marks = [m['text'] for m in marks if m['type'] == 'red']
        yellow_marks = [m['text'] for m in marks if m['type'] == 'yellow']

        marks_desc = []
        if red_marks:
            marks_desc.append(f"红色标记（生词/重点词）: {', '.join(red_marks)}")
        if yellow_marks:
            marks_desc.append(f"黄底标记（熟词僻义/搭配/微妙语义）: {', '.join(yellow_marks)}")

        prompt = f"""句子：{sentence}

标记词：
{chr(10).join(marks_desc)}

请用极简的中文（1-2 行）解释这些标记词在此句中的：
- 红色词：核心含义 + 词性
- 黄色词：在此语境下的特殊用法、搭配或语义要点

要求：直击要点，适合考研复习，不要啰嗦。"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            explanation = message.content[0].text.strip()
            return explanation

        except Exception as e:
            print(f"Claude API 调用失败: {e}")
            return None


class AnkiConnector:
    """AnkiConnect 接口"""

    def __init__(self, url: str = "http://localhost:8765"):
        self.url = url

    def _invoke(self, action: str, **params) -> Dict:
        """调用 AnkiConnect API"""
        payload = {
            "action": action,
            "version": 6,
            "params": params
        }

        try:
            response = requests.post(self.url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("error"):
                raise Exception(f"AnkiConnect 错误: {result['error']}")

            return result.get("result")

        except requests.exceptions.RequestException as e:
            raise Exception(f"无法连接 AnkiConnect: {e}")

    def add_note(self, deck_name: str, model_name: str,
                 front: str, back: str, tags: List[str],
                 front_field: str = "Front", back_field: str = "Back") -> Optional[int]:
        """
        添加卡片

        Args:
            front_field: 正面字段名（默认 "Front"，中文模板可能是 "正面"）
            back_field: 背面字段名（默认 "Back"，中文模板可能是 "背面"）

        Returns:
            卡片 ID，失败返回 None
        """
        try:
            note_id = self._invoke(
                "addNote",
                note={
                    "deckName": deck_name,
                    "modelName": model_name,
                    "fields": {
                        front_field: front,
                        back_field: back
                    },
                    "tags": tags
                }
            )
            return note_id
        except Exception as e:
            print(f"添加卡片失败: {e}")
            return None

    def check_connection(self) -> bool:
        """检查 AnkiConnect 连接"""
        try:
            self._invoke("version")
            return True
        except:
            return False


class WordToAnkiConverter:
    """主转换器"""

    def __init__(self, config: Dict):
        self.config = config
        self.claude = ClaudeExplainer(
            config['claude_api_key'],
            config.get('claude_model', 'claude-sonnet-4-5-20250929'),
            config.get('claude_api_base_url')  # 支持代理站点
        )
        self.anki = AnkiConnector(config.get('anki_connect_url', 'http://localhost:8765'))

    def _format_front(self, sentence: str, marks: List[Dict]) -> str:
        """格式化卡片正面（带 HTML 高亮）"""
        # 为标记词添加 HTML 样式
        result = sentence

        # 按位置倒序排序，避免替换时位置偏移
        sorted_marks = sorted(marks, key=lambda m: m['position'][0], reverse=True)

        for mark in sorted_marks:
            start, end = mark['position']
            text = mark['text']
            mark_type = mark['type']

            if mark_type == 'red':
                styled = f'<span style="color: red; font-weight: bold;">{text}</span>'
            else:  # yellow
                styled = f'<span style="background-color: yellow;">{text}</span>'

            result = result[:start] + styled + result[end:]

        return result

    def convert(self, sentences: List[Dict]) -> int:
        """
        转换句子列表为 Anki 卡片

        Returns:
            成功创建的卡片数量
        """
        deck_name = self.config['anki_deck']
        model_name = self.config['anki_model']
        front_field = self.config.get('anki_front_field', 'Front')
        back_field = self.config.get('anki_back_field', 'Back')
        base_tags = self.config.get('base_tags', ['reading-auto'])
        article_tag = self.config.get('article_tag', '')

        if article_tag:
            tags = base_tags + [article_tag]
        else:
            tags = base_tags

        success_count = 0

        print(f"\n开始处理 {len(sentences)} 个句子...")

        for i, sent_data in enumerate(sentences, 1):
            sentence = sent_data['sentence']
            marks = sent_data['marks']

            print(f"\n[{i}/{len(sentences)}] 处理句子:")
            print(f"  {sentence[:60]}..." if len(sentence) > 60 else f"  {sentence}")

            # 调用 Claude 生成解释
            print("  → 调用 Claude API...")
            explanation = self.claude.explain(sentence, marks)

            if not explanation:
                print("  ✗ 跳过（解释生成失败）")
                continue

            # 格式化卡片
            front = self._format_front(sentence, marks)
            back = explanation

            # 添加到 Anki
            print("  → 添加到 Anki...")
            note_id = self.anki.add_note(deck_name, model_name, front, back, tags,
                                         front_field, back_field)

            if note_id:
                print(f"  ✓ 成功（卡片 ID: {note_id}）")
                success_count += 1
            else:
                print("  ✗ 跳过（Anki 添加失败）")

        return success_count


def read_from_clipboard() -> Optional[str]:
    """从剪贴板读取内容"""
    try:
        import pyperclip
        content = pyperclip.paste()
        return content
    except Exception as e:
        print(f"读取剪贴板失败: {e}")
        print("提示: 请确保安装了 pyperclip 和必要的系统依赖")
        return None


def main():
    """主函数"""
    # 读取配置
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        print("错误: 配置文件不存在")
        print(f"请创建 {config_path} 并参考 config.example.json")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 检查 AnkiConnect 连接
    print("检查 AnkiConnect 连接...")
    anki = AnkiConnector(config.get('anki_connect_url', 'http://localhost:8765'))
    if not anki.check_connection():
        print("错误: 无法连接到 AnkiConnect")
        print("请确保:")
        print("  1. Anki 正在运行")
        print("  2. AnkiConnect 插件已安装")
        print("  3. AnkiConnect 配置正确（默认 http://localhost:8765）")
        sys.exit(1)
    print("✓ AnkiConnect 连接成功")

    # 从剪贴板读取
    print("\n从剪贴板读取内容...")
    clipboard_content = read_from_clipboard()

    if not clipboard_content:
        print("错误: 剪贴板为空或读取失败")
        sys.exit(1)

    print(f"✓ 读取成功（{len(clipboard_content)} 字符）")

    # 解析内容
    print("\n解析标记词...")

    # 尝试多种解析方式
    sentences = []

    # 方式 1: 假设是 HTML 格式（Word 复制通常包含 HTML）
    if '<html' in clipboard_content.lower() or '<span' in clipboard_content.lower():
        print("  检测到 HTML 格式")
        parser = SimpleRTFParser(clipboard_content)
        sentences = parser.parse()

    # 方式 2: RTF 格式
    elif '\\rtf' in clipboard_content:
        print("  检测到 RTF 格式")
        parser = RTFParser(clipboard_content)
        sentences = parser.parse()

    # 方式 3: 纯文本（无法识别标记）
    else:
        print("  ⚠ 无法识别格式（可能是纯文本，丢失了格式信息）")
        print("  提示: 请确保从 Word 中复制时保留了格式")
        sys.exit(1)

    if not sentences:
        print("✗ 未找到任何标记词")
        print("请检查:")
        print("  1. 是否正确标记了红色/黄底文字")
        print("  2. 复制时是否保留了格式")
        sys.exit(1)

    print(f"✓ 找到 {len(sentences)} 个包含标记的句子")

    # 转换并添加到 Anki
    converter = WordToAnkiConverter(config)
    success_count = converter.convert(sentences)

    # 总结
    print("\n" + "=" * 50)
    print(f"完成！成功创建 {success_count}/{len(sentences)} 张卡片")
    print("=" * 50)


if __name__ == "__main__":
    main()
