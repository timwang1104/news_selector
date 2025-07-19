"""
AI评估提示词模板
"""

EVALUATION_PROMPT_TEMPLATE = """
你是上海市科委的专业顾问，请评估以下文章对上海科技发展的相关性和价值。

文章信息：
标题：{title}
摘要：{summary}
内容预览：{content_preview}

请从以下三个维度进行评估（每个维度0-10分）：

1. 政策相关性 (0-10分)
   - 与上海科技政策的相关程度
   - 对政策制定和执行的参考价值
   - 涉及的政策领域和重点方向

2. 创新影响 (0-10分)
   - 对科技创新的推动作用
   - 技术前沿性和突破性
   - 产业发展的促进效果

3. 实用性 (0-10分)
   - 可操作性和可实施性
   - 对实际工作的指导意义
   - 短期内的应用价值

请按以下JSON格式返回评估结果：
{{
    "relevance_score": <政策相关性分数>,
    "innovation_impact": <创新影响分数>,
    "practicality": <实用性分数>,
    "total_score": <总分>,
    "reasoning": "<详细评估理由，包含各维度的具体分析>",
    "confidence": <置信度，0-1之间的小数>
}}

注意：
- 总分为三个维度分数之和
- 评估理由要具体明确，说明评分依据
- 置信度反映评估的确定程度
"""

BATCH_EVALUATION_PROMPT = """
你是上海市科委的专业顾问，请批量评估以下文章对上海科技发展的相关性和价值。

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。
评估维度和格式要求与单篇评估相同。

返回格式：
[
    {{
        "article_index": 0,
        "relevance_score": <分数>,
        "innovation_impact": <分数>,
        "practicality": <分数>,
        "total_score": <总分>,
        "reasoning": "<评估理由>",
        "confidence": <置信度>
    }},
    ...
]
"""

FALLBACK_REASONING = "AI服务不可用，基于关键词匹配的降级评估"
