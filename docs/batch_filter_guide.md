# 批量筛选功能使用指南

## 功能概述

批量筛选功能允许您自动切换不同的订阅源，进行批量筛选，并将所有筛选结果统一列出。这个功能特别适合处理大量订阅源，快速找到高质量的文章。

## 核心特性

### 1. 自动订阅源切换
- 自动遍历所有订阅源或指定的订阅源
- 支持按关键词过滤订阅源
- 支持限制处理的订阅源数量

### 2. 批量文章筛选
- 支持关键词筛选、AI筛选和完整筛选链
- 并行处理提高效率
- 可配置每个订阅源的文章获取数量

### 3. 统一结果展示
- 按分数排序显示所有筛选结果
- 支持按订阅源分组显示
- 提供详细的统计信息

### 4. 结果导出
- 支持JSON格式导出（包含详细信息）
- 支持CSV格式导出（便于Excel处理）
- 自动生成带时间戳的文件名

## 使用方法

### 1. 编程接口使用

```python
from src.services.batch_filter_service import BatchFilterConfig, BatchFilterManager, CLIBatchProgressCallback
from src.utils.result_formatter import ResultFormatter, ResultExporter

# 创建批量筛选管理器
manager = BatchFilterManager()

# 创建配置
config = BatchFilterConfig()
config.max_subscriptions = 10  # 最多处理10个订阅源
config.subscription_keywords = ["AI", "tech", "科技"]  # 筛选包含这些关键词的订阅源
config.articles_per_subscription = 20  # 每个订阅源获取20篇文章
config.filter_type = "keyword"  # 使用关键词筛选
config.enable_parallel = True  # 启用并行处理
config.min_score_threshold = 0.7  # 最小分数阈值

# 创建进度回调
callback = CLIBatchProgressCallback(show_progress=True)

# 执行批量筛选
result = manager.filter_subscriptions_batch(config, callback)

# 显示结果
summary = ResultFormatter.format_batch_summary(result)
print(summary)

# 导出结果
json_content = ResultFormatter.export_to_json(result)
ResultExporter.save_to_file(json_content, "batch_result.json")
```

### 2. 测试脚本使用

我们提供了几个测试脚本来演示功能：

```bash
# 基本功能测试
python test_batch_filter.py

# 演示脚本（包含多种使用场景）
python demo_batch_filter.py

# 简单导入测试
python minimal_test.py
```

## 配置选项

### BatchFilterConfig 配置类

```python
class BatchFilterConfig:
    # 订阅源筛选配置
    max_subscriptions: Optional[int] = None  # 最大处理订阅源数量
    subscription_keywords: List[str] = []    # 订阅源标题关键词过滤
    
    # 文章获取配置
    articles_per_subscription: int = 50      # 每个订阅源获取的文章数量
    exclude_read: bool = True                # 是否排除已读文章
    hours_back: Optional[int] = 24           # 获取多少小时内的文章
    
    # 筛选配置
    filter_type: str = "chain"               # 筛选类型: keyword, ai, chain
    enable_parallel: bool = True             # 是否启用并行处理
    max_workers: int = 3                     # 最大并行工作线程数
    
    # 结果配置
    max_results_per_subscription: Optional[int] = None  # 每个订阅源最大结果数
    min_score_threshold: Optional[float] = None         # 最小分数阈值
    sort_by: str = "final_score"             # 排序方式
    group_by_subscription: bool = True       # 是否按订阅源分组显示
```

## 使用场景示例

### 场景1：快速获取科技新闻
```python
config = BatchFilterConfig()
config.subscription_keywords = ["tech", "Technology", "科技", "AI"]
config.filter_type = "keyword"
config.max_subscriptions = 5
config.articles_per_subscription = 15
```

### 场景2：高质量文章深度筛选
```python
config = BatchFilterConfig()
config.filter_type = "ai"  # 使用AI筛选
config.min_score_threshold = 0.8
config.max_results_per_subscription = 3
config.enable_parallel = True
```

### 场景3：大规模并行处理
```python
config = BatchFilterConfig()
config.enable_parallel = True
config.max_workers = 5
config.max_subscriptions = 20
config.filter_type = "chain"
```

## 结果格式

### 批量筛选结果结构
```python
@dataclass
class BatchFilterResult:
    total_subscriptions: int          # 总订阅源数
    processed_subscriptions: int      # 成功处理的订阅源数
    total_articles_fetched: int       # 总获取文章数
    total_articles_selected: int      # 总选中文章数
    subscription_results: List[SubscriptionFilterResult]  # 各订阅源结果
    processing_time: float            # 总处理时间
```

### 单个订阅源结果
```python
@dataclass
class SubscriptionFilterResult:
    subscription_id: str              # 订阅源ID
    subscription_title: str           # 订阅源标题
    articles_fetched: int             # 获取的文章数
    selected_count: int               # 选中的文章数
    filter_result: FilterChainResult  # 详细筛选结果
```

## 性能优化建议

### 1. 并行处理
- 对于大量订阅源，启用并行处理可显著提高效率
- 建议并行工作线程数设置为2-5个

### 2. 筛选类型选择
- **keyword**: 速度最快，适合快速筛选
- **ai**: 质量最高，但速度较慢
- **chain**: 平衡质量和速度

### 3. 数量控制
- 合理设置`max_subscriptions`避免处理时间过长
- 使用`min_score_threshold`过滤低质量文章

## 错误处理

系统具有完善的错误处理机制：

1. **订阅源获取失败**: 跳过该订阅源，继续处理其他订阅源
2. **文章获取失败**: 记录错误信息，不影响其他订阅源
3. **筛选失败**: 使用降级策略，确保有结果返回
4. **网络超时**: 自动重试机制

## 注意事项

1. **API限制**: 注意Inoreader API的调用频率限制
2. **内存使用**: 大量文章处理时注意内存使用情况
3. **认证状态**: 确保已登录Inoreader账户
4. **AI配置**: 使用AI筛选时需要配置API密钥

## 故障排除

### 常见问题

1. **未登录错误**
   ```bash
   python main.py login
   ```

2. **导入错误**
   - 检查Python路径设置
   - 确保所有依赖已安装

3. **筛选结果为空**
   - 降低`min_score_threshold`
   - 检查关键词配置
   - 增加`articles_per_subscription`

4. **处理速度慢**
   - 启用并行处理
   - 减少订阅源数量
   - 使用关键词筛选而非AI筛选

## 扩展功能

系统设计具有良好的扩展性，可以轻松添加：

1. **自定义筛选器**: 实现BaseFilter接口
2. **新的导出格式**: 扩展ResultFormatter类
3. **自定义进度回调**: 实现BatchFilterProgressCallback接口
4. **订阅源过滤器**: 自定义subscription_filter函数

## 总结

批量筛选功能为新闻订阅工具提供了强大的自动化处理能力，能够：

- ✅ 自动处理多个订阅源
- ✅ 智能筛选高质量文章
- ✅ 统一展示和导出结果
- ✅ 支持并行处理提高效率
- ✅ 提供丰富的配置选项
- ✅ 具有完善的错误处理机制

这个功能特别适合需要处理大量信息源的用户，能够显著提高信息获取和筛选的效率。
