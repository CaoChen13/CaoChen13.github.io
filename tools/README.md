# Word 标注转 Anki 卡片工具

一键将 Word 中的阅读标注转换为 Anki 复习卡片。

## 功能特点

- **智能识别标记**: 自动识别 Word 中的红色文字（生词）和黄底文字（熟词僻义/搭配）
- **AI 生成解释**: 调用 Claude API 生成精简的中文解释
- **自动创建卡片**: 通过 AnkiConnect 自动添加到 Anki
- **容错处理**: 遇到错误自动跳过，不创建垃圾卡片
- **批量处理**: 按句子分组，一次处理整段文本

## 工作流程

```
Word 标注文本
    ↓ 复制
剪贴板
    ↓ 读取
脚本解析 (红色/黄底标记)
    ↓ 分组
按句子分组
    ↓ 调用
Claude API (生成解释)
    ↓ 创建
AnkiConnect (添加卡片)
    ↓
Anki 牌组
```

## 安装步骤

### 1. 安装 Python 依赖

```bash
cd tools
pip install -r requirements.txt
```

**Linux 系统额外步骤**（剪贴板支持）:

```bash
# Ubuntu/Debian
sudo apt-get install xclip

# Fedora/RHEL
sudo dnf install xclip

# Arch Linux
sudo pacman -S xclip
```

### 2. 安装 AnkiConnect

1. 打开 Anki
2. 进入 **工具 → 附加组件**
3. 点击 **获取插件**
4. 输入代码: `2055492159`
5. 重启 Anki

验证安装:
```bash
curl http://localhost:8765 -X POST -d '{"action":"version","version":6}'
# 应返回: {"result": 6, "error": null}
```

### 3. 配置脚本

复制配置模板:
```bash
cp config.example.json config.json
```

编辑 `config.json`:
```json
{
  "claude_api_key": "sk-ant-api03-YOUR_API_KEY",
  "claude_model": "claude-sonnet-4-5-20250929",
  "anki_connect_url": "http://localhost:8765",
  "anki_deck": "英语学习",
  "anki_model": "Basic",
  "base_tags": ["reading-auto"],
  "article_tag": "22T1"
}
```

**配置项说明**:
- `claude_api_key`: Claude API 密钥（从 https://console.anthropic.com 获取）
- `claude_model`: 使用的模型（推荐 claude-sonnet-4-5）
- `anki_connect_url`: AnkiConnect 地址（默认本地）
- `anki_deck`: Anki 牌组名称（需在 Anki 中预先创建）
- `anki_model`: 卡片模板（通常用 "Basic"）
- `base_tags`: 基础标签（所有卡片都会打上）
- `article_tag`: 文章标签（可选，用于区分不同文章）

### 4. 配置 Anki

1. 创建牌组（如 "英语学习"）
2. 确保有 "Basic" 模板（默认已有）
3. 模板包含 "Front" 和 "Back" 字段

## 使用方法

### 步骤 1: 在 Word 中标注

1. 打开 Word 文档
2. 阅读时标记:
   - **红色**: 完全不熟悉的生词/重点词
   - **黄底**: 熟词僻义、固定搭配、微妙语义

示例:
```
The company decided to <红色>leverage</红色> its existing
<黄底>infrastructure</黄底> to <黄底>roll out</黄底> the new service.
```

### 步骤 2: 复制文本

- 选中标注好的段落
- `Ctrl+C` (Windows) 或 `Cmd+C` (Mac)
- **重要**: 确保复制时保留了格式

### 步骤 3: 运行脚本

```bash
cd tools
python word_to_anki.py
```

或者（如果设置了可执行权限）:
```bash
./word_to_anki.py
```

### 步骤 4: 查看结果

脚本会输出处理进度:
```
检查 AnkiConnect 连接...
✓ AnkiConnect 连接成功

从剪贴板读取内容...
✓ 读取成功（1234 字符）

解析标记词...
✓ 找到 5 个包含标记的句子

开始处理 5 个句子...

[1/5] 处理句子:
  The company decided to leverage its existing infrastructure...
  → 调用 Claude API...
  → 添加到 Anki...
  ✓ 成功（卡片 ID: 1234567890123）

...

==================================================
完成！成功创建 5/5 张卡片
==================================================
```

### 步骤 5: 在 Anki 中复习

打开 Anki，进入对应牌组，开始复习！

卡片格式:
- **正面**: 原句（标记词用红色/黄底高亮）
- **背面**: Claude 生成的精简中文解释

## 高级用法

### 修改文章标签

每篇文章使用不同标签:
```bash
# 编辑 config.json
{
  ...
  "article_tag": "economist_2024_01"
}
```

运行后，所有卡片会打上 `reading-auto` 和 `economist_2024_01` 标签。

### 使用不同模型

如果需要更快速度或更低成本:
```json
{
  "claude_model": "claude-3-5-haiku-20241022"
}
```

### 自定义卡片模板

如果想用自定义模板:
1. 在 Anki 中创建新模板（如 "Reading Card"）
2. 确保包含 "Front" 和 "Back" 字段
3. 修改 config.json:
```json
{
  "anki_model": "Reading Card"
}
```

## 故障排除

### 问题: 无法连接 AnkiConnect

**解决**:
1. 确认 Anki 正在运行
2. 确认 AnkiConnect 插件已安装
3. 检查 AnkiConnect 配置:
   - 进入 **工具 → 附加组件 → AnkiConnect → 配置**
   - 确认 `webBindAddress` 为 `127.0.0.1`，`webBindPort` 为 `8765`

### 问题: 未找到标记词

**原因**: Word 复制时丢失了格式信息

**解决**:
1. 确认在 Word 中文字确实是红色/黄底
2. 尝试以下复制方式:
   - **方法 1**: 右键 → 复制（保留格式）
   - **方法 2**: 复制后检查剪贴板是否包含格式信息
3. 如果是 Mac，确保使用原生 Word（而非 Pages）

### 问题: Claude API 调用失败

**解决**:
1. 检查 API 密钥是否正确
2. 检查网络连接
3. 确认账户余额充足
4. 查看具体错误信息

### 问题: 剪贴板读取失败（Linux）

**解决**:
```bash
# 安装剪贴板工具
sudo apt-get install xclip xsel

# 或使用 pyclip（更好的兼容性）
pip install pyclip
```

### 问题: 生成的解释不够精简

**解决**: 修改脚本中的提示词

编辑 `word_to_anki.py` 的 `ClaudeExplainer.explain()` 方法:
```python
prompt = f"""句子：{sentence}

标记词：
{chr(10).join(marks_desc)}

要求：用不超过 20 字解释每个标记词的核心含义。"""
```

## 工作原理

### 1. 格式解析

Word 复制到剪贴板时会提供多种格式:
- **HTML**: 包含 `<span style="color:red">` 等标记
- **RTF**: 包含 `\cf2` (颜色)、`\highlight5` (背景) 等控制字

脚本优先解析 HTML，因为更容易处理。

### 2. 句子分组

按标点符号（`.` `!` `?` 等）分割句子，每个包含标记词的句子生成一张卡片。

### 3. Claude 提示词

脚本会将句子和标记词发送给 Claude:
```
句子：The company decided to leverage its existing infrastructure.

标记词：
红色标记（生词/重点词）: leverage
黄底标记（熟词僻义/搭配/微妙语义）: infrastructure

请用极简的中文（1-2 行）解释这些标记词在此句中的：
- 红色词：核心含义 + 词性
- 黄色词：在此语境下的特殊用法、搭配或语义要点
```

Claude 返回:
```
leverage (v.): 利用、发挥；infrastructure: 此处指"现有基础设施"，强调已有资源
```

### 4. 卡片生成

- **正面**: HTML 格式的原句，标记词用 `<span>` 标签高亮
- **背面**: Claude 生成的解释

通过 AnkiConnect API 添加到 Anki。

## 最佳实践

### 标注建议

1. **红色**: 真正不认识的词，或需要重点记忆的核心词
2. **黄底**: 熟词生义、固定搭配、微妙语义差异
3. **适度标注**: 每句不超过 3-5 个标记（太多影响复习效率）

### 复习建议

1. **新卡片限制**: Anki 设置每天新卡片上限（如 20 张）
2. **标签管理**: 用文章标签区分来源，方便筛选复习
3. **定期整理**: 对太简单的卡片点击 "暂停" 或删除

### 效率提升

1. **批量处理**: 一次复制多段文本（确保每段都有句子结构）
2. **统一风格**: 保持标注风格一致（什么该标红、什么该标黄）
3. **配合原文**: 在 Anki 卡片背面添加文章链接或出处

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 致谢

- [Anthropic Claude](https://www.anthropic.com/) - AI 解释生成
- [AnkiConnect](https://github.com/FooSoft/anki-connect) - Anki 接口
- [Anki](https://apps.ankiweb.net/) - 间隔重复学习
