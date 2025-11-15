#!/usr/bin/env python3
"""
Word 标注转 Anki 卡片工具

从剪贴板读取 Word 复制的内容，提取红色/黄底标记，
调用 Claude API 生成解释，通过 AnkiConnect 创建卡片。
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import requests


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
                self.full_text = ''  # 完整文本
                self.all_marks = []  # 所有标记
                self.current_tag_stack = []
                self.current_style = {}
                self.ignore_content = False  # 是否忽略内容（style/script标签内）

            def handle_starttag(self, tag, attrs):
                self.current_tag_stack.append(tag)

                # 忽略 style、script、head 等标签内的内容
                if tag.lower() in ('style', 'script', 'head'):
                    self.ignore_content = True
                    return

                # 检查样式
                attrs_dict = dict(attrs)
                style = attrs_dict.get('style', '')
                if 'color' in style or 'background' in style:
                    self.current_style = {'style': style}

            def handle_endtag(self, tag):
                # 恢复内容处理
                if tag.lower() in ('style', 'script', 'head'):
                    self.ignore_content = False

                if self.current_tag_stack and self.current_tag_stack[-1] == tag:
                    self.current_tag_stack.pop()
                self.current_style = {}

            def handle_data(self, data):
                # 忽略特定标签内的内容
                if self.ignore_content:
                    return

                text = data.strip()
                if not text:
                    return

                start_pos = len(self.full_text)
                self.full_text += text + ' '
                end_pos = len(self.full_text)

                # 检查是否有样式标记
                mark_type = None
                if self.current_style.get('style'):
                    style = self.current_style['style']
                    style_lower = style.lower()

                    # 检测红色：color 样式，但排除黑色
                    # Word 可能生成：color:red, color:#FF0000, color:#C00000, color:rgb(255,0,0)
                    if 'color' in style_lower and 'background' not in style_lower:
                        # 排除黑色文字
                        if not ('black' in style_lower or '#000000' in style_lower or 'rgb(0,0,0)' in style_lower.replace(' ', '')):
                            mark_type = 'red'

                    # 检测黄色背景
                    elif 'background' in style_lower and ('yellow' in style_lower or '#ffff' in style_lower):
                        mark_type = 'yellow'

                if mark_type:
                    self.all_marks.append({
                        'text': text,
                        'type': mark_type,
                        'position': (start_pos, end_pos)
                    })

        parser = WordHTMLParser()
        try:
            parser.feed(self.html_content)
        except Exception as e:
            print(f"HTML 解析失败: {e}")
            return []

        # 第二步：按句子切分，找到包含标记的句子
        sentences = self._split_into_sentences(parser.full_text, parser.all_marks)

        # 合并每个句子中相邻的相同类型标记（修复单词被拆分的问题）
        for sent_data in sentences:
            sent_data['marks'] = self._merge_adjacent_marks(
                sent_data['marks'],
                sent_data['sentence']
            )

        return sentences

    def _split_into_sentences(self, full_text: str, all_marks: List[Dict]) -> List[Dict]:
        """
        将完整文本按句子切分，为每个句子分配标记

        Args:
            full_text: 完整文本
            all_marks: 所有标记列表

        Returns:
            句子列表，每个句子包含其标记
        """
        import re

        # 用正则按句子切分（保留分隔符）
        # 匹配句号、问号、感叹号、分号，后面跟空格或结尾
        sentence_pattern = r'([^.!?;。！？；]+[.!?;。！？；]+)'
        raw_sentences = re.findall(sentence_pattern, full_text)

        # 如果有剩余文本（最后没有句号的部分）
        last_pos = sum(len(s) for s in raw_sentences)
        if last_pos < len(full_text):
            remaining = full_text[last_pos:].strip()
            if remaining:
                raw_sentences.append(remaining)

        # 为每个句子分配标记
        sentences = []
        current_pos = 0

        for raw_sent in raw_sentences:
            sent_text = raw_sent.strip()
            if not sent_text:
                current_pos += len(raw_sent)
                continue

            # 找到这个句子在 full_text 中的位置
            sent_start = full_text.find(sent_text, current_pos)
            if sent_start == -1:
                # 找不到，跳过
                current_pos += len(raw_sent)
                continue

            sent_end = sent_start + len(sent_text)
            current_pos = sent_end

            # 找到在这个句子范围内的所有标记
            sent_marks = []
            for mark in all_marks:
                mark_start, mark_end = mark['position']
                # 标记在句子范围内
                if mark_start >= sent_start and mark_end <= sent_end + 5:  # +5 容错
                    # 调整标记位置（相对于句子开头）
                    adjusted_mark = mark.copy()
                    adjusted_mark['position'] = (mark_start - sent_start, mark_end - sent_start)
                    sent_marks.append(adjusted_mark)

            # 只保留有标记的句子
            if sent_marks:
                sentences.append({
                    'sentence': sent_text,
                    'marks': sent_marks
                })

        return sentences

    def _merge_adjacent_marks(self, marks: List[Dict], sentence: str) -> List[Dict]:
        """
        合并相邻的相同类型标记

        Args:
            marks: 标记列表
            sentence: 原句

        Returns:
            合并后的标记列表
        """
        if not marks:
            return marks

        # 按位置排序
        marks = sorted(marks, key=lambda m: m['position'][0])

        merged = []
        current = marks[0].copy()

        for next_mark in marks[1:]:
            # 检查是否相邻且类型相同
            current_end = current['position'][1]
            next_start = next_mark['position'][0]

            # 检查中间的内容
            between = sentence[current_end:next_start]

            # 相邻判断：
            # 1. 位置差小于 10 个字符
            # 2. 中间只有空格、标点或为空
            # 3. 类型相同
            distance = next_start - current_end
            # 允许的间隔字符：空格、撇号、引号、连字符
            is_likely_same_word = distance < 10 and all(c in " '\"-" for c in between)
            same_type = current['type'] == next_mark['type']

            if is_likely_same_word and same_type:
                # 合并：扩展位置，拼接文本
                current['position'] = (current['position'][0], next_mark['position'][1])
                # 从原句中提取实际文本
                start, end = current['position']
                raw_text = sentence[start:end]

                # 判断是否应该去掉空格：
                # 1. 如果中间只有空格，检查是否是单词拆分
                # 2. 简单规则：如果next是短片段（<=3字符），很可能是拆分，去掉空格
                # 3. 否则保留空格（如 "present and personal"）
                if all(c == ' ' for c in between):
                    # 中间只有空格
                    next_is_short = len(next_mark['text']) <= 3
                    if next_is_short:
                        # next是短片段，很可能是拆分，去掉空格
                        current['text'] = ''.join(raw_text.split())
                    else:
                        # next是正常单词，保留空格
                        current['text'] = ' '.join(raw_text.split())
                else:
                    # 中间有标点等，保留原样
                    current['text'] = ' '.join(raw_text.split())
            else:
                # 不合并，保存当前标记并开始新的
                merged.append(current)
                current = next_mark.copy()

        # 添加最后一个
        merged.append(current)

        return merged


class ClaudeExplainer:
    """使用 Claude API 生成解释（使用 requests 直接调用）"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", base_url: Optional[str] = None):
        """
        初始化 Claude API 客户端

        Args:
            api_key: API 密钥
            model: 模型名称
            base_url: API 基础 URL（代理站点）
        """
        self.api_key = api_key
        self.model = model

        # 设置 API URL
        if base_url:
            # 确保有 /messages 后缀
            if base_url.endswith('/messages'):
                self.api_url = base_url
            else:
                self.api_url = base_url + '/messages'
        else:
            self.api_url = "https://api.anthropic.com/v1/messages"

    def explain(self, sentence: str, marks: List[Dict]) -> Tuple[Optional[str], Optional[str]]:
        """
        为标记词生成解释（带重试机制）

        Args:
            sentence: 原句
            marks: 标记列表 [{'text': '词', 'type': 'red/yellow'}, ...]

        Returns:
            (中文解释字符串, 错误原因)，成功时错误原因为 None
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

解释要求（考研背诵，必须简洁）：
1. 核心释义：最常见的意思，简短
2. 句中含义：仅当和核心释义不同时才说明
3. 熟词生义（重点）：如有熟词生义/引申义，必须标注
4. 固定搭配：如是搭配，说明搭配意思
5. 复杂结构：仅当有倒装/后置/前置时说明

输出格式：
- 每个词单独一行（用空行分隔）
- 格式：单词: 核心释义 [→ 句中意思] (熟词生义)
- 不要词性标注，不要多余说明
- 直接给答案

示例：
stock: 库存 → 股票 (熟词生义)

run into: 偶遇 → 遇到(问题)

倒装: Not until...did he...（否定词前置）

现在请解释："""

        # 构建请求
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01'
        }

        data = {
            'model': self.model,
            'max_tokens': 300,
            'messages': [
                {
                    'role': 'user',
                    'content': prompt
                }
            ]
        }

        # 重试配置
        max_retries = 3
        base_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                # 使用 requests 直接调用
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=data,
                    timeout=60
                )

                # 检查响应
                if response.status_code == 200:
                    result = response.json()
                    explanation = result['content'][0]['text'].strip()
                    return explanation, None
                elif response.status_code == 429:
                    # HTTP 429 - 请求过于频繁，可以重试
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
                        continue
                    else:
                        return None, "HTTP 429 - 请求过于频繁（已重试3次），代理站点限流严格"
                else:
                    # 其他 HTTP 错误不重试（配置错误或服务器问题）
                    error_msgs = {
                        401: "HTTP 401 - API Key无效，请检查config.json中的claude_api_key",
                        403: "HTTP 403 - 访问被拒绝，请检查API Key权限",
                        500: "HTTP 500 - 服务器内部错误，代理站点出现问题",
                        502: "HTTP 502 - 网关错误，代理站点连接Claude失败",
                        503: "HTTP 503 - 服务暂时不可用，代理站点维护中"
                    }
                    error_msg = error_msgs.get(response.status_code, f"HTTP {response.status_code} - API调用失败")
                    return None, error_msg

            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return None, "请求超时（已重试3次），网络较慢或代理站点响应慢"

            except requests.exceptions.SSLError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return None, "SSL连接错误（已重试3次），代理站点网络不稳定"

            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
                    continue
                else:
                    return None, "网络连接失败（已重试3次），请检查网络或代理设置"

            except requests.exceptions.RequestException as e:
                # 其他 requests 错误，不重试（配置错误）
                return None, f"API请求错误: {str(e)[:50]}"

            except Exception as e:
                # 未知错误，不重试
                return None, f"未知错误: {str(e)[:50]}"

        # 不应该到这里
        return None, "重试失败（已尝试3次）"


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
        # 按位置倒序排序，从后往前替换，避免位置偏移
        sorted_marks = sorted(marks, key=lambda m: m['position'][0], reverse=True)

        result = sentence

        for mark in sorted_marks:
            start, end = mark['position']
            text = mark['text']  # 合并后的文本（干净的，可能去掉了空格）
            mark_type = mark['type']

            # 获取原始片段（可能包含尾部空格）
            original_segment = result[start:end]

            # 计算尾部空格数量
            trailing_spaces = len(original_segment) - len(original_segment.rstrip())

            # 构建样式
            if mark_type == 'red':
                styled = f'<span style="color: red; font-weight: bold;">{text}</span>'
            else:  # yellow
                styled = f'<span style="background-color: yellow;">{text}</span>'

            # 按位置替换（从后往前，避免位置变化）
            # 替换时保留原始的尾部空格，避免单词连在一起
            result = result[:start] + styled + (' ' * trailing_spaces) + result[end:]

        return result

    def _format_back(self, explanation: str, marks: List[Dict]) -> str:
        """
        格式化卡片背面

        Args:
            explanation: Claude 生成的解释
            marks: 标记列表

        Returns:
            格式化后的 HTML 文本
        """
        # 换行符转 HTML
        result = explanation.replace('\n', '<br>')

        # 给标记的单词加颜色（红色或黄色）
        for mark in marks:
            word = mark['text']
            mark_type = mark['type']

            # 选择样式（和正面一致）
            if mark_type == 'red':
                style = 'color: red; font-weight: bold;'
            else:  # yellow
                style = 'background-color: yellow;'

            # 尝试匹配：精确匹配
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, result, re.IGNORECASE):
                # 精确匹配到了
                match = re.search(pattern, result, re.IGNORECASE)
                original_text = match.group()
                result = result.replace(original_text, f'<span style="{style}">{original_text}</span>', 1)

        return result

    def convert(self, sentences: List[Dict]) -> Tuple[int, List[Dict]]:
        """
        转换句子列表为 Anki 卡片

        Returns:
            (成功数量, 失败列表)
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
        failed_items = []  # 记录失败的句子

        print(f"\n开始处理 {len(sentences)} 个句子...")

        for i, sent_data in enumerate(sentences, 1):
            sentence = sent_data['sentence']
            marks = sent_data['marks']
            mark_words = [m['text'] for m in marks]

            print(f"[{i}/{len(sentences)}] {', '.join(mark_words)}", end=" ... ")

            # 如果不是第一个请求，等待一下（避免触发速率限制）
            if i > 1:
                time.sleep(1.5)  # 每个请求间隔 1.5 秒

            # 调用 Claude 生成解释
            explanation, error = self.claude.explain(sentence, marks)

            if not explanation:
                print("✗")
                print(f"  → 失败原因: {error}")
                failed_items.append({
                    'index': i,
                    'marks': mark_words,
                    'reason': error
                })
                continue

            # 格式化卡片
            front = self._format_front(sentence, marks)
            back = self._format_back(explanation, marks)

            # 添加到 Anki
            note_id = self.anki.add_note(deck_name, model_name, front, back, tags,
                                         front_field, back_field)

            if note_id:
                print("✓")
                success_count += 1
            else:
                print("✗")
                print(f"  → 失败原因: Anki添加失败，请检查模板名称、字段名称或卡片是否重复")
                failed_items.append({
                    'index': i,
                    'marks': mark_words,
                    'reason': 'Anki添加失败（检查模板/字段名称）'
                })

        return success_count, failed_items


def read_from_clipboard() -> Optional[str]:
    """从剪贴板读取内容（优先读取富文本格式）"""
    import sys

    # Windows: 尝试读取 HTML 格式
    if sys.platform == 'win32':
        try:
            import win32clipboard

            win32clipboard.OpenClipboard()
            try:
                # 尝试读取 HTML Format (CF_HTML)
                # HTML Format 的格式 ID 通常是 49380，但也可以通过名称获取
                html_format = win32clipboard.RegisterClipboardFormat("HTML Format")
                if win32clipboard.IsClipboardFormatAvailable(html_format):
                    html_data = win32clipboard.GetClipboardData(html_format)
                    win32clipboard.CloseClipboard()

                    # HTML Format 包含头部信息，需要提取实际的 HTML
                    # 格式: Version:0.9\nStartHTML:...\nEndHTML:...\n<html>...</html>
                    if isinstance(html_data, bytes):
                        html_data = html_data.decode('utf-8', errors='ignore')

                    # 提取 HTML 内容
                    html_start = html_data.find('<html')
                    if html_start == -1:
                        html_start = html_data.find('<HTML')
                    if html_start != -1:
                        return html_data[html_start:]

            except Exception as e:
                print(f"读取 HTML 格式失败: {e}")
            finally:
                try:
                    win32clipboard.CloseClipboard()
                except:
                    pass

        except ImportError:
            print("提示: 安装 pywin32 可以读取 Word 格式")
            print("  pip install pywin32")

    # 回退到纯文本
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

    # 检查连接
    print("✓ 检查 AnkiConnect...")
    anki = AnkiConnector(config.get('anki_connect_url', 'http://localhost:8765'))
    if not anki.check_connection():
        print("  ✗ 无法连接 Anki（请确保 Anki 正在运行）")
        sys.exit(1)

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
    success_count, failed_items = converter.convert(sentences)

    # 总结
    print(f"\n完成：{success_count}/{len(sentences)} 成功")

    # 如果有失败的，显示失败总结
    if failed_items:
        print(f"\n失败: ", end="")
        failed_indices = [f"第{item['index']}句({item['reason']})" for item in failed_items]
        print(", ".join(failed_indices))


if __name__ == "__main__":
    main()
