# AI智能筛选器实现计划

## 模块概述

AI智能筛选器是两步筛选系统的第二步，负责对关键词筛选后的文章进行智能评估，提供更精准的相关性判断。

### 核心职责
- 智能评估文章与上海科委需求的相关性
- 提供多维度评分和详细理由
- 支持批量处理和结果缓存
- 处理AI服务异常和降级策略

## 接口设计

### 主要类定义

```python
# src/filters/ai_filter.py

@dataclass
class AIEvaluation:
    relevance_score: int        # 政策相关性 (0-10)
    innovation_impact: int      # 创新影响 (0-10)
    practicality: int          # 实用性 (0-10)
    total_score: int           # 总分 (0-30)
    reasoning: str             # 评估理由
    confidence: float          # 置信度 (0-1)

@dataclass
class AIFilterResult:
    article: Article
    evaluation: AIEvaluation
    processing_time: float
    ai_model: str

class AIFilter:
    def __init__(self, ai_client: AIClient, config: AIFilterConfig):
        self.ai_client = ai_client
        self.config = config
        self.cache = AIResultCache()
    
    def filter(self, articles: List[Article]) -> List[AIFilterResult]:
        """AI筛选文章并返回评估结果"""
        pass
    
    def evaluate_single(self, article: Article) -> AIFilterResult:
        """评估单篇文章"""
        pass
    
    def batch_evaluate(self, articles: List[Article]) -> List[AIFilterResult]:
        """批量评估文章"""
        pass
```

### 配置类定义

```python
# src/config/ai_filter_config.py

@dataclass
class AIFilterConfig:
    # AI服务配置
    model_name: str = "gpt-3.5-turbo"
    api_key: str = ""
    base_url: str = ""
    
    # 筛选配置
    threshold: int = 20         # 总分阈值 (满分30)
    max_requests: int = 50      # 最大请求数
    batch_size: int = 5         # 批处理大小
    
    # 性能配置
    timeout: int = 30           # 请求超时时间
    retry_times: int = 3        # 重试次数
    enable_cache: bool = True   # 启用缓存
    cache_ttl: int = 3600      # 缓存过期时间(秒)
    
    # 降级策略
    fallback_enabled: bool = True
    fallback_threshold: float = 0.7  # 关键词筛选分数作为降级
```

## 实现细节

### 1. AI客户端封装

```python
# src/ai/client.py

class AIClient:
    def __init__(self, config: AIFilterConfig):
        self.config = config
        self.client = self._init_client()
    
    def evaluate_article(self, article: Article) -> AIEvaluation:
        """评估单篇文章"""
        try:
            prompt = self._build_evaluation_prompt(article)
            response = self._call_ai_api(prompt)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return self._fallback_evaluation(article)
    
    def batch_evaluate(self, articles: List[Article]) -> List[AIEvaluation]:
        """批量评估文章"""
        results = []
        for batch in self._create_batches(articles):
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
        return results
    
    def _build_evaluation_prompt(self, article: Article) -> str:
        """构建评估提示词"""
        return EVALUATION_PROMPT_TEMPLATE.format(
            title=article.title,
            summary=article.summary or article.content[:500],
            content_preview=article.content[:1000] if article.content else ""
        )
```

### 2. 提示词模板

```python
# src/ai/prompts.py

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
{
    "relevance_score": <政策相关性分数>,
    "innovation_impact": <创新影响分数>,
    "practicality": <实用性分数>,
    "total_score": <总分>,
    "reasoning": "<详细评估理由，包含各维度的具体分析>",
    "confidence": <置信度，0-1之间的小数>
}

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
"""
```

### 3. 结果缓存机制

```python
# src/ai/cache.py

class AIResultCache:
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
    
    def get(self, article_hash: str) -> Optional[AIEvaluation]:
        """获取缓存结果"""
        if article_hash in self.cache:
            result, timestamp = self.cache[article_hash]
            if time.time() - timestamp < self.ttl:
                return result
            else:
                del self.cache[article_hash]
        return None
    
    def set(self, article_hash: str, evaluation: AIEvaluation):
        """设置缓存结果"""
        self.cache[article_hash] = (evaluation, time.time())
    
    def _hash_article(self, article: Article) -> str:
        """生成文章哈希值"""
        content = f"{article.title}{article.summary}"
        return hashlib.md5(content.encode()).hexdigest()
```

### 4. 降级策略

```python
class FallbackStrategy:
    def __init__(self, keyword_filter: KeywordFilter):
        self.keyword_filter = keyword_filter
    
    def fallback_evaluation(self, article: Article, 
                          keyword_score: float) -> AIEvaluation:
        """基于关键词分数的降级评估"""
        # 将关键词分数转换为AI评估格式
        base_score = int(keyword_score * 30)  # 转换为30分制
        
        return AIEvaluation(
            relevance_score=int(base_score * 0.4),
            innovation_impact=int(base_score * 0.3),
            practicality=int(base_score * 0.3),
            total_score=base_score,
            reasoning="AI服务不可用，基于关键词匹配的降级评估",
            confidence=0.6
        )
```

## 配置选项

### AI服务配置

```python
# config/ai_settings.py

AI_FILTER_CONFIG = {
    # 模型配置
    "model_name": "gpt-3.5-turbo",
    "temperature": 0.3,
    "max_tokens": 1000,
    
    # 请求配置
    "timeout": 30,
    "retry_times": 3,
    "retry_delay": 1,
    
    # 批处理配置
    "batch_size": 5,
    "max_concurrent": 3,
    "rate_limit": 60,  # 每分钟请求数
    
    # 缓存配置
    "enable_cache": True,
    "cache_ttl": 3600,
    "cache_size": 1000,
    
    # 质量控制
    "min_confidence": 0.5,
    "threshold": 20,
    "enable_fallback": True
}
```

## 测试计划

### 单元测试

```python
# tests/test_ai_filter.py

class TestAIFilter:
    def test_single_evaluation(self):
        """测试单篇文章评估"""
        pass
    
    def test_batch_evaluation(self):
        """测试批量评估"""
        pass
    
    def test_cache_mechanism(self):
        """测试缓存机制"""
        pass
    
    def test_fallback_strategy(self):
        """测试降级策略"""
        pass
    
    def test_error_handling(self):
        """测试错误处理"""
        pass
    
    def test_response_parsing(self):
        """测试响应解析"""
        pass

class TestAIClient:
    def test_api_call(self):
        """测试API调用"""
        pass
    
    def test_prompt_building(self):
        """测试提示词构建"""
        pass
    
    def test_retry_mechanism(self):
        """测试重试机制"""
        pass
```

### 集成测试

```python
class TestAIFilterIntegration:
    def test_end_to_end_filtering(self):
        """测试端到端筛选"""
        pass
    
    def test_performance_benchmark(self):
        """测试性能基准"""
        pass
    
    def test_accuracy_evaluation(self):
        """测试准确性评估"""
        pass
```

## 性能考虑

### 优化策略
1. **批量处理** - 减少API调用次数
2. **异步处理** - 并发处理多个请求
3. **智能缓存** - 避免重复评估
4. **请求限流** - 控制API调用频率
5. **结果预处理** - 优化提示词长度

### 性能指标
- 处理速度：5-10篇文章/分钟
- 准确率：> 85%
- 缓存命中率：> 60%
- API成功率：> 95%

## 扩展性

### 未来扩展方向
1. **多模型支持** - 支持不同AI模型
2. **自定义评估维度** - 可配置评估标准
3. **学习优化** - 基于反馈优化评估
4. **多语言支持** - 支持英文文章评估

### 插件接口
```python
class CustomEvaluator:
    def evaluate(self, article: Article, context: dict) -> AIEvaluation:
        """自定义评估逻辑"""
        pass

class ModelAdapter:
    def adapt_prompt(self, prompt: str, model: str) -> str:
        """适配不同模型的提示词"""
        pass
```
