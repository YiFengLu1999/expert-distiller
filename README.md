# Expert Distiller · 专家蒸馏

[简体中文](README.md) | [English](README.en.md)

**把你提供的书籍和材料，变成一个能依据材料判断、解释和与你对话的专家 Skill。**

```text
书籍 / 文章 / 讲义 / 笔记
           ↓
可定位的材料片段 + 覆盖范围
           ↓
概念 → 判断条件 → 诊断问题 → 行动 → 例外
           ↓
可安装的领域专家 SKILL.md + 证据库
           ↓
带出处的专家对话
```

这是由聊天模型执行的技能工作流，附带本地 Python 工具。不是模型权重训练，也不声称能复制真实专家。蒸馏和对话使用你运行 Skill 的模型，不需要本项目的独立 API Key；效果取决于模型、材料质量与评测。

## 两层技能

| 层 | 作用 |
|---|---|
| `expert-distiller` | 阅读指定材料，提炼知识和判断方法，生成新的专家技能 |
| 生成的 `<domain>-expert` | 安装后围绕该领域材料进行咨询、案例分析和问答 |

回答区分 **材料依据**、**基于材料推导**、**材料不足**。新问题可以推导，但不把推导冒充作者观点；多来源冲突保留各自条件。

## 快速开始

需要 Python 3.10+ 和能够读取本地文件、运行脚本的 Skill 宿主。TXT/Markdown 工具只用标准库；PDF 另需 `pypdf`。其他格式先转为带来源定位的 Markdown。脚本不联网；宿主模型如何处理你提供的文件取决于宿主服务设置。

### 1. 安装生成器

```bash
git clone https://github.com/YiFengLu1999/expert-distiller.git
cd expert-distiller
python3 scripts/install.py
```

安装器默认复制到 `$CODEX_HOME/skills`，未设置时为 `~/.codex/skills`，拒绝覆盖已有同名技能。可用 `--dest /your/host/skills` 指定其他宿主目录。以宿主实际技能发现目录为准；本项目当前按 Codex 目录验证，未逐一验证其他客户端。[OpenAI 官方技能文档](https://learn.chatgpt.com/docs/build-skills)介绍了 SKILL.md 格式。

在新的 Codex 对话中调用 `$expert-distiller`；若列表未刷新，重新打开对话或重启客户端。

### 2. 提供材料，生成专家

将材料放入本地 `materials/`，然后对 Codex 说：

```text
使用 $expert-distiller，把我提供的这三本书蒸馏成 research-methods-expert。
用途：帮助我设计研究问题、检查论证和分析案例。
只以这些材料为领域依据，允许基于材料推导，并明确标记。
输出到 generated/research-methods-expert。
请记录实际阅读范围，保留引用，验证后给我安装命令。
```

如果只给书名，生成器会请求正文或片段，不能从模型记忆假装读完整本书。长材料按章节分批处理，并记录未覆盖范围；建好索引不代表读完。

### 3. 安装并对话

```bash
python3 scripts/install.py generated/research-methods-expert
```

```text
使用 $research-methods-expert，帮我判断这个研究方案的问题。
先指出最关键的缺失信息，再结合材料给出建议和出处。
```

## 立即体验原创样例

```bash
python3 scripts/install.py examples/workshop-expert
```

然后问：

```text
使用 $workshop-expert，我要教新手使用一个工具。
学员课后满意度很高，能否说明他们学会了？我应该怎么验证？
```

材料支持的回答应指出：满意度不能单独证明技能掌握，需要观察无提示的个人操作。若问“最优时长是多少”，专家应说明此材料没有依据。原文见 [workshop-notes.md](examples/workshop-notes.md)。

## 工具与验证

```bash
# 建立可携带的证据库（不执行语义蒸馏；输出须为新文件）
python3 skills/expert-distiller/scripts/corpus.py ingest materials/book.md --out generated/my-expert/references/corpus.json

# 中英文关键词检索；分数仅用于排序，不是证据可信度
python3 skills/expert-distiller/scripts/corpus.py search examples/workshop-expert/references/corpus.json '满意度 技能'

# 校验专家包结构、证据 ID、片段哈希和逐字短锚点
python3 skills/expert-distiller/scripts/corpus.py validate examples/workshop-expert

# 运行本地工具回归测试
python3 -m unittest discover -s tests -v
```

PDF 可选依赖：`python3 -m pip install pypdf`。扫描件需要额外 OCR；PDF 阅读顺序、公式和表格仍需检查。关键词检索没有向量语义检索能力，应配合同义词与上下文阅读。专家知识库随技能安装，可离开原材料目录使用。

结构检查不证明语义正确，也不保证模型永远不幻觉。每个专家都应完成 [行为评测](skills/expert-distiller/references/evaluation.md)，实际未测试的项目应标为未运行。此版本包含原创样例和工具测试，尚未以真实长书完成端到端行为评测。

## 与 Fabric 的关系

灵感来自 [Daniel Miessler 的 Fabric](https://github.com/danielmiessler/Fabric)。其 [extract_book_ideas](https://github.com/danielmiessler/Fabric/blob/main/data/patterns/extract_book_ideas/system.md) 是书籍思想提取模式；当前文本包含从模型记忆提取书籍内容的指令。本项目针对“只基于实际提供材料”的需求，增加来源核验、判断规则、覆盖范围和可安装专家包。此处是对该模式的比较，不是对整个 Fabric 能力的穷尽描述。本项目独立编写，没有复制其提示词。

## 文件与隐私

- `skills/expert-distiller/`：完整生成器，可单独安装。
- `examples/`：原创短材料和可安装样例。
- `scripts/install.py`：本地复制安装，无覆盖升级。
- `tests/`：材料处理、损坏引用与安装行为测试。
- `materials/`、`generated/` 默认 Git 忽略。它们可能包含整本文本和私密材料；发布前仍需检查暂存文件，`.gitignore` 不是访问控制。

项目代码、技能指令与原创样例采用 MIT 许可；用户书籍和其他第三方材料的权利不因此改变。
