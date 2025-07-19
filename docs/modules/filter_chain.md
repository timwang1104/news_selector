# 筛选链管理实现计划

## 模块概述

筛选链管理器负责协调关键词筛选和AI筛选的执行流程，实现两步筛选策略的统一管理和结果整合。

### 核心职责
- 协调两步筛选流程的执行
- 管理筛选结果的传递和整合
- 提供筛选过程的监控和统计
- 处理筛选异常和错误恢复

## 接口设计

### 主要类定义

```python
# src/filters/filter_chain.py

@dataclass
class FilterChainConfig:
    # 筛选流程配置
    enable_keyword_filter: bool = True
    enable_ai_filter: bool = True
    keyword_threshold: float = 0.6
    ai_threshold: int = 20
    
    # 流程控制
    max_keyword_results: int = 100
    max_ai_requests: int = 50
    fail_fast: bool = False
    
    # 结果配置
    sort_by: str = "total_score"  # total_score, relevance, timestamp
    include_rejected: bool = False

@dataclass
class FilterChainResult:
    # 输入统计
    total_articles: int
    processing_start_time: datetime
    processing_end_time: datetime
    
    # 筛选统计
    keyword_filtered_count: int
    ai_filtered_count: int
    final_selected_count: int
    
    # 结果数据
    selected_articles: List[CombinedFilterResult]
    rejected_articles: List[CombinedFilterResult]
    
    # 性能统计
    keyword_filter_time: float
    ai_filter_time: float
    total_processing_time: float
    
    # 错误信息
    errors: List[str]
    warnings: List[str]

@dataclass
class CombinedFilterResult:
    article: Article
    keyword_result: Optional[KeywordFilterResult]
    ai_result: Optional[AIFilterResult]
    final_score: float
    selected: bool
    rejection_reason: Optional[str]

class FilterChain:
    def __init__(self, 
                 keyword_filter: KeywordFilter,
                 ai_filter: AIFilter,
                 config: FilterChainConfig):
        self.keyword_filter = keyword_filter
        self.ai_filter = ai_filter
        self.config = config
        self.metrics = FilterMetrics()
    
    def process(self, articles: List[Article]) -> FilterChainResult:
        """执行完整的筛选流程"""
        pass
    
    def process_with_callback(self, articles: List[Article], 
                            callback: Callable) -> FilterChainResult:
        """带进度回调的筛选流程"""
        pass
```

## 实现细节

### 1. 筛选流程控制

```python
class FilterChain:
    def process(self, articles: List[Article]) -> FilterChainResult:
        """执行完整的筛选流程"""
        start_time = datetime.now()
        result = FilterChainResult(
            total_articles=len(articles),
            processing_start_time=start_time,
            selected_articles=[],
            rejected_articles=[],
            errors=[],
            warnings=[]
        )
        
        try:
            # 第一步：关键词筛选
            keyword_results = self._execute_keyword_filter(articles, result)
            
            # 第二步：AI筛选
            if self.config.enable_ai_filter and keyword_results:
                ai_results = self._execute_ai_filter(keyword_results, result)
                final_results = self._combine_results(keyword_results, ai_results)
            else:
                final_results = self._convert_keyword_results(keyword_results)
            
            # 第三步：结果整理
            self._finalize_results(final_results, result)
            
        except Exception as e:
            result.errors.append(f"筛选流程异常: {str(e)}")
            logger.error(f"Filter chain error: {e}", exc_info=True)
        
        finally:
            result.processing_end_time = datetime.now()
            result.total_processing_time = (
                result.processing_end_time - start_time
            ).total_seconds()
        
        return result
    
    def _execute_keyword_filter(self, articles: List[Article], 
                              result: FilterChainResult) -> List[KeywordFilterResult]:
        """执行关键词筛选"""
        if not self.config.enable_keyword_filter:
            return []
        
        start_time = time.time()
        try:
            keyword_results = self.keyword_filter.filter(articles)
            
            # 应用阈值过滤
            filtered_results = [
                r for r in keyword_results 
                if r.relevance_score >= self.config.keyword_threshold
            ]
            
            # 限制结果数量
            if len(filtered_results) > self.config.max_keyword_results:
                filtered_results = sorted(
                    filtered_results, 
                    key=lambda x: x.relevance_score, 
                    reverse=True
                )[:self.config.max_keyword_results]
            
            result.keyword_filtered_count = len(filtered_results)
            result.keyword_filter_time = time.time() - start_time
            
            return filtered_results
            
        except Exception as e:
            result.errors.append(f"关键词筛选失败: {str(e)}")
            if self.config.fail_fast:
                raise
            return []
    
    def _execute_ai_filter(self, keyword_results: List[KeywordFilterResult],
                         result: FilterChainResult) -> List[AIFilterResult]:
        """执行AI筛选"""
        start_time = time.time()
        try:
            # 提取文章
            articles = [kr.article for kr in keyword_results]
            
            # 限制AI处理数量
            if len(articles) > self.config.max_ai_requests:
                # 按关键词分数排序，取前N个
                sorted_results = sorted(
                    keyword_results,
                    key=lambda x: x.relevance_score,
                    reverse=True
                )
                articles = [r.article for r in sorted_results[:self.config.max_ai_requests]]
                result.warnings.append(
                    f"AI筛选数量限制，仅处理前{self.config.max_ai_requests}篇文章"
                )
            
            ai_results = self.ai_filter.filter(articles)
            
            # 应用AI阈值过滤
            filtered_ai_results = [
                r for r in ai_results 
                if r.evaluation.total_score >= self.config.ai_threshold
            ]
            
            result.ai_filtered_count = len(filtered_ai_results)
            result.ai_filter_time = time.time() - start_time
            
            return filtered_ai_results
            
        except Exception as e:
            result.errors.append(f"AI筛选失败: {str(e)}")
            if self.config.fail_fast:
                raise
            return []
```

### 2. 结果整合逻辑

```python
def _combine_results(self, keyword_results: List[KeywordFilterResult],
                    ai_results: List[AIFilterResult]) -> List[CombinedFilterResult]:
    """整合关键词和AI筛选结果"""
    combined_results = []
    
    # 创建AI结果的快速查找字典
    ai_results_dict = {
        self._get_article_id(r.article): r for r in ai_results
    }
    
    for keyword_result in keyword_results:
        article_id = self._get_article_id(keyword_result.article)
        ai_result = ai_results_dict.get(article_id)
        
        # 计算最终分数
        final_score = self._calculate_final_score(keyword_result, ai_result)
        
        # 判断是否选中
        selected, rejection_reason = self._determine_selection(
            keyword_result, ai_result, final_score
        )
        
        combined_result = CombinedFilterResult(
            article=keyword_result.article,
            keyword_result=keyword_result,
            ai_result=ai_result,
            final_score=final_score,
            selected=selected,
            rejection_reason=rejection_reason
        )
        
        combined_results.append(combined_result)
    
    return combined_results

def _calculate_final_score(self, keyword_result: KeywordFilterResult,
                         ai_result: Optional[AIFilterResult]) -> float:
    """计算最终综合分数"""
    keyword_score = keyword_result.relevance_score
    
    if ai_result is None:
        # 仅有关键词分数
        return keyword_score
    
    # 综合评分：关键词分数 * 0.3 + AI分数 * 0.7
    ai_score = ai_result.evaluation.total_score / 30.0  # 归一化到0-1
    final_score = keyword_score * 0.3 + ai_score * 0.7
    
    return final_score

def _determine_selection(self, keyword_result: KeywordFilterResult,
                       ai_result: Optional[AIFilterResult],
                       final_score: float) -> Tuple[bool, Optional[str]]:
    """判断文章是否被选中"""
    # 关键词筛选未通过
    if keyword_result.relevance_score < self.config.keyword_threshold:
        return False, "关键词相关性不足"
    
    # AI筛选未通过
    if ai_result and ai_result.evaluation.total_score < self.config.ai_threshold:
        return False, "AI评估分数不足"
    
    # AI筛选失败但关键词分数较高
    if ai_result is None and keyword_result.relevance_score >= 0.8:
        return True, None
    
    # 综合分数判断
    if final_score >= 0.7:
        return True, None
    else:
        return False, "综合评分不足"
```

### 3. 进度监控和回调

```python
class FilterProgressCallback:
    def on_start(self, total_articles: int):
        """筛选开始"""
        pass
    
    def on_keyword_progress(self, processed: int, total: int):
        """关键词筛选进度"""
        pass
    
    def on_keyword_complete(self, results_count: int):
        """关键词筛选完成"""
        pass
    
    def on_ai_progress(self, processed: int, total: int):
        """AI筛选进度"""
        pass
    
    def on_ai_complete(self, results_count: int):
        """AI筛选完成"""
        pass
    
    def on_complete(self, final_count: int):
        """筛选完成"""
        pass
    
    def on_error(self, error: str):
        """筛选错误"""
        pass

def process_with_callback(self, articles: List[Article], 
                        callback: FilterProgressCallback) -> FilterChainResult:
    """带进度回调的筛选流程"""
    callback.on_start(len(articles))
    
    try:
        # 关键词筛选
        keyword_results = []
        if self.config.enable_keyword_filter:
            for i, batch in enumerate(self._create_batches(articles, 10)):
                batch_results = self.keyword_filter.filter(batch)
                keyword_results.extend(batch_results)
                callback.on_keyword_progress(
                    min((i + 1) * 10, len(articles)), 
                    len(articles)
                )
            callback.on_keyword_complete(len(keyword_results))
        
        # AI筛选
        ai_results = []
        if self.config.enable_ai_filter and keyword_results:
            ai_articles = [r.article for r in keyword_results]
            for i, batch in enumerate(self._create_batches(ai_articles, 5)):
                batch_results = self.ai_filter.filter(batch)
                ai_results.extend(batch_results)
                callback.on_ai_progress(
                    min((i + 1) * 5, len(ai_articles)), 
                    len(ai_articles)
                )
            callback.on_ai_complete(len(ai_results))
        
        # 整合结果
        final_results = self._combine_results(keyword_results, ai_results)
        selected_count = sum(1 for r in final_results if r.selected)
        
        callback.on_complete(selected_count)
        
        return self._build_result(final_results)
        
    except Exception as e:
        callback.on_error(str(e))
        raise
```

## 配置选项

```python
# config/filter_chain_settings.py

FILTER_CHAIN_CONFIG = {
    # 筛选开关
    "enable_keyword_filter": True,
    "enable_ai_filter": True,
    
    # 阈值配置
    "keyword_threshold": 0.6,
    "ai_threshold": 20,
    "final_score_threshold": 0.7,
    
    # 数量限制
    "max_keyword_results": 100,
    "max_ai_requests": 50,
    "max_final_results": 30,
    
    # 流程控制
    "fail_fast": False,
    "enable_parallel": True,
    "batch_size": 10,
    
    # 结果配置
    "sort_by": "final_score",
    "include_rejected": False,
    "include_metrics": True
}
```

## 测试计划

```python
# tests/test_filter_chain.py

class TestFilterChain:
    def test_complete_flow(self):
        """测试完整筛选流程"""
        pass
    
    def test_keyword_only_flow(self):
        """测试仅关键词筛选流程"""
        pass
    
    def test_error_handling(self):
        """测试错误处理"""
        pass
    
    def test_progress_callback(self):
        """测试进度回调"""
        pass
    
    def test_result_combination(self):
        """测试结果整合"""
        pass
    
    def test_threshold_filtering(self):
        """测试阈值过滤"""
        pass
```

## 性能考虑

### 优化策略
1. **并行处理** - 关键词和AI筛选的并行化
2. **批量处理** - 减少函数调用开销
3. **内存管理** - 及时释放中间结果
4. **缓存利用** - 复用AI筛选结果

### 性能指标
- 端到端处理时间：< 5分钟（100篇文章）
- 内存使用：< 200MB
- 错误率：< 5%

## 扩展性

### 未来扩展方向
1. **多级筛选** - 支持更多筛选步骤
2. **动态配置** - 运行时调整筛选参数
3. **结果反馈** - 基于用户反馈优化筛选
4. **分布式处理** - 支持大规模文章处理
