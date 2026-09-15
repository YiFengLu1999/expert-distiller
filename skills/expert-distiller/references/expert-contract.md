# 专家技能输出契约

```text
topic-expert/
  SKILL.md
  agents/openai.yaml
  scripts/corpus.py
  references/
    corpus.json
    knowledge.json
    reasoning.md
    coverage.md
    evaluations.md
```

`SKILL.md` 从 assets/expert-SKILL.md 改写。用领域专属名称与 description 触发专家；删除所有模板标记。在 reasoning.md 中写可执行的判断框架和规则 ID，在 knowledge.json 保存可核验的证据链，不把整本书塞进入口文件。

knowledge.json 使用以下结构；可追加字段，但保留这些字段：

```json
{
  "rules": [
    {
      "id": "R01",
      "kind": "source",
      "claim": "材料支持的明确命题",
      "when": "使用条件",
      "questions": ["应用前要了解什么"],
      "action": "有条件的行动建议",
      "limits": "失效条件或材料未给出的范围",
      "evidence": [{"chunk_id": "来自 corpus 的实际 ID", "quote": "该片段内逐字存在的短锚点"}]
    }
  ]
}
```

`inference` 规则还需非空 `rationale`，用简短说明表达证据到建议之间的逻辑，不输出隐含思维过程。`quote` 只取核验所需的短句，通常不超过 80 个字符；全文库用于本地检索，不能因有锚点就默认可公开整库。

`coverage.md` 应明确实际已读 chunk ID 与未覆盖范围；`evaluations.md` 放问题、预期行为、实际观察、通过/失败/未测与日期。发布“可用”前修复失效引用；不足以形成判断系统的材料应交付为有限范围草稿。

专家回答时先读 reasoning.md、coverage.md 和 knowledge.json，再按证据 ID 读取 corpus 中对应原文及邻近上下文。库大时用附带脚本 search 和 show。关键词检索仅为候选排序；无命中后尝试术语、同义词、目录和相邻片段，不能凭一次检索就断言书中不存在。

优先给简洁回答，按需附诊断问题或建议；在相关结论旁标注“材料依据”或“推导”及文件名、定位和 chunk ID。遇到冲突保留双方引用；材料不足时说明缺失的是哪项事实或判断依据。用户新增的情况只作为案例事实，不自动变成长期来源库。
