# 关键词筛选器实现计划

## 模块概述

关键词筛选器是两步筛选系统的第一步，负责基于预定义关键词快速过滤相关文章。

### 核心职责
- 基于关键词匹配筛选文章
- 计算文章相关性评分
- 支持多维度关键词分类
- 提供筛选结果统计
- **完全过滤中国公司相关新闻**（新增功能）

## 接口设计

### 主要类定义

```python
# src/filters/keyword_filter.py

@dataclass
class KeywordMatch:
    keyword: str
    category: str
    position: int
    context: str

@dataclass
class KeywordFilterResult:
    article: Article
    matched_keywords: List[KeywordMatch]
    relevance_score: float
    category_scores: Dict[str, float]

class KeywordFilter:
    def __init__(self, config: KeywordConfig):
        self.config = config
        self.keyword_matcher = KeywordMatcher()
    
    def filter(self, articles: List[Article]) -> List[KeywordFilterResult]:
        """筛选文章并返回匹配结果"""
        pass
    
    def calculate_relevance_score(self, matches: List[KeywordMatch]) -> float:
        """计算文章相关性评分"""
        pass
```

### 配置类定义

```python
# src/config/keyword_config.py

@dataclass
class KeywordConfig:
    keywords: Dict[str, List[str]]  # 分类关键词
    weights: Dict[str, float]       # 分类权重
    threshold: float = 0.6          # 筛选阈值
    max_results: int = 100          # 最大结果数
    case_sensitive: bool = False    # 大小写敏感
    fuzzy_match: bool = True        # 模糊匹配
```

## 实现细节

### 1. 关键词匹配算法

```python
class KeywordMatcher:
    def __init__(self, fuzzy_threshold: float = 0.8):
        self.fuzzy_threshold = fuzzy_threshold
        # 初始化黑名单模式（新增）
        self.blacklist_pattern = self._compile_blacklist_pattern()
    
    def find_matches(self, text: str, keywords: List[str]) -> List[KeywordMatch]:
        """在文本中查找关键词匹配"""
        matches = []
        
        # 精确匹配
        for keyword in keywords:
            positions = self._find_exact_matches(text, keyword)
            for pos in positions:
                matches.append(KeywordMatch(
                    keyword=keyword,
                    position=pos,
                    context=self._extract_context(text, pos, keyword)
                ))
        
        # 模糊匹配（可选）
        if self.fuzzy_threshold > 0:
            fuzzy_matches = self._find_fuzzy_matches(text, keywords)
            matches.extend(fuzzy_matches)
        
        return matches
        
    def _compile_blacklist_pattern(self) -> re.Pattern:
        """预编译黑名单关键词正则表达式（新增）"""
        if not CHINA_BLACKLIST:
            return None
            
        # 构建正则表达式
        escaped_keywords = [re.escape(keyword) for keyword in CHINA_BLACKLIST]
        
        if self.config.word_boundary:
            # 使用单词边界
            pattern = r'\b(?:' + '|'.join(escaped_keywords) + r')\b'
        else:
            pattern = '|'.join(escaped_keywords)
        
        flags = re.IGNORECASE if not self.config.case_sensitive else 0
        return re.compile(pattern, flags)
    
    def check_blacklist(self, text: str) -> bool:
        """检查文本是否包含黑名单关键词（新增）"""
        if not text or not self.blacklist_pattern:
            return False
        
        return bool(self.blacklist_pattern.search(text))
```

### 2. 相关性评分算法

```python
def calculate_relevance_score(self, matches: List[KeywordMatch], 
                            article: Article) -> float:
    """计算文章相关性评分
    
    评分因子：
    - 关键词匹配数量
    - 关键词权重
    - 匹配位置（标题 > 摘要 > 正文）
    - 关键词密度
    """
    if not matches:
        return 0.0
    
    score = 0.0
    
    # 基础分数：匹配关键词数量
    base_score = len(matches) * 0.1
    
    # 位置权重
    position_weights = {
        'title': 3.0,
        'summary': 2.0,
        'content': 1.0
    }
    
    # 分类权重
    category_weights = self.config.weights
    
    for match in matches:
        # 位置加权
        position = self._get_match_position(match, article)
        position_weight = position_weights.get(position, 1.0)
        
        # 分类加权
        category_weight = category_weights.get(match.category, 1.0)
        
        # 累加分数
        score += position_weight * category_weight * 0.1
    
    # 归一化到 0-1 范围
    return min(score, 1.0)
```

### 3. 文章筛选实现

```python
def filter(self, articles: List[Article]) -> List[KeywordFilterResult]:
    """筛选文章列表"""
    results = []
    
    for article in articles:
        # 首先检查是否包含黑名单关键词（新增）
        text_content = self._prepare_text(article)
        if self.matcher.check_blacklist(text_content):
            # 如果包含黑名单关键词，直接跳过
            continue
            
        result = self.filter_single(article)
        if result and result.relevance_score >= self.config.threshold:
            results.append(result)
    
    # 按相关性分数排序
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    
    # 限制结果数量
    if len(results) > self.config.max_results:
        results = results[:self.config.max_results]
    
    return results

def filter_single(self, article: Article) -> Optional[KeywordFilterResult]:
    """筛选单篇文章"""
    # 准备文本内容
    text_content = self._prepare_text(article)
    
    # 检查是否包含黑名单关键词（新增）
    if self.matcher.check_blacklist(text_content):
        return None
    
    # 查找关键词匹配
    matches = self.matcher.find_matches(text_content)
    
    # 检查最少匹配数量
    if len(matches) < self.config.min_matches:
        return None
    
    # 计算相关性评分
    relevance_score = self.calculate_relevance_score(matches, article)
    
    # 创建筛选结果
    result = KeywordFilterResult(
        article=article,
        matched_keywords=matches,
        relevance_score=relevance_score
    )
    
    return result
```

## 中国黑名单配置

为了完全过滤中国相关新闻，我们在 `default_keywords.py` 中添加了中国黑名单配置：

```python
# 中国黑名单关键词（包含国家、地区、大学、政府机构和公司）
CHINA_BLACKLIST = [
    # 国家和地区
    "中国", "China", "Chinese", "PRC", "People's Republic of China",
    "中华人民共和国", "中华", "mainland China", "中国大陆",
    "北京", "Beijing", "上海", "Shanghai", "广州", "Guangzhou", "深圳", "Shenzhen",
    
    # 中国大学和研究机构
    "清华大学", "Tsinghua University", "北京大学", "Peking University", 
    "中国科学院", "Chinese Academy of Sciences", "CAS", "中科院",
    "复旦大学", "Fudan University", "浙江大学", "Zhejiang University",
    "上海交通大学", "Shanghai Jiao Tong University", "中国人民大学", "Renmin University",
    "南京大学", "Nanjing University", "武汉大学", "Wuhan University",
    "中国科学技术大学", "University of Science and Technology of China", "USTC",
    
    # 政府机构
    "中共", "CCP", "Chinese Communist Party", "中国共产党",
    "国务院", "State Council", "中央政府", "Central Government",
    "科技部", "Ministry of Science and Technology", "工信部", "MIIT",
    "教育部", "Ministry of Education", "外交部", "Ministry of Foreign Affairs",
    
    # 科技公司
    "华为", "Huawei", "中兴", "ZTE", "小米", "Xiaomi", "OPPO", "vivo", "联想", "Lenovo",
    "阿里巴巴", "Alibaba", "腾讯", "Tencent", "百度", "Baidu", "京东", "JD.com", "字节跳动", "ByteDance",
    "滴滴", "DiDi", "美团", "Meituan", "网易", "NetEase", "哔哩哔哩", "Bilibili", "快手", "Kuaishou",
    "商汤", "SenseTime", "旷视", "Megvii", "依图", "Yitu", "云从", "CloudWalk",
    
    # 半导体公司
    "中芯国际", "SMIC", "长江存储", "YMTC", "紫光", "Unisoc", "华虹", "Huahong",
    
    # 通信公司
    "中国移动", "China Mobile", "中国电信", "China Telecom", "中国联通", "China Unicom",
    
    # 能源公司
    "中石油", "PetroChina", "中石化", "Sinopec", "中海油", "CNOOC",
    
    # 金融公司
    "中国银行", "Bank of China", "工商银行", "ICBC", "建设银行", "CCB",
    "农业银行", "ABC", "中信", "CITIC", "平安", "Ping An",
    
    # 制造业公司
    "比亚迪", "BYD", "吉利", "Geely", "长城", "Great Wall Motors",
    "宁德时代", "CATL", "中国中车", "CRRC"
]
```

这些关键词将用于完全过滤包含中国相关内容的新闻，包括中国国家、地区、大学、政府机构和公司，而不是仅仅降低其评分。

def calculate_relevance_score(self, matches: List[KeywordMatch], 
                            article: Article) -> float:
    """计算文章相关性评分
    
    评分因子：
    - 关键词匹配数量
    - 关键词权重
    - 匹配位置（标题 > 摘要 > 正文）
    - 关键词密度
    """
    if not matches:
        return 0.0
    
    score = 0.0
    
    # 基础分数：匹配关键词数量
    base_score = len(matches) * 0.1
    
    # 位置权重
    position_weights = {
        'title': 3.0,
        'summary': 2.0,
        'content': 1.0
    }
    
    # 分类权重
    category_weights = self.config.weights
    
    for match in matches:
        # 位置加权
        position = self._get_match_position(match, article)
        position_weight = position_weights.get(position, 1.0)
        
        # 分类加权
        category_weight = category_weights.get(match.category, 1.0)
        
        # 累加分数
        score += position_weight * category_weight * 0.1
    
    # 归一化到 0-1 范围
    return min(score, 1.0)
```

### 3. 国际科技关键词配置

```python
# src/config/international_keywords.py

INTERNATIONAL_TECH_KEYWORDS = {
    "ai_technology": {
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "neural networks", "natural language processing", "computer vision",
            "generative AI", "large language model", "ChatGPT", "GPT",
            "AI research", "AI development", "AI applications", "AI ethics"
        ],
        "weight": 1.0
    },

    "quantum_technology": {
        "keywords": [
            "quantum computing", "quantum technology", "quantum research",
            "quantum supremacy", "quantum advantage", "quantum algorithm",
            "quantum cryptography", "quantum communication", "qubit",
            "quantum processor", "quantum internet", "quantum sensor"
        ],
        "weight": 0.9
    },

    "biotechnology": {
        "keywords": [
            "biotechnology", "bioengineering", "synthetic biology",
            "gene editing", "CRISPR", "genomics", "proteomics",
            "personalized medicine", "precision medicine", "cell therapy",
            "immunotherapy", "biomarker", "drug discovery", "clinical trial"
        ],
        "weight": 0.9
    },

    "semiconductor": {
        "keywords": [
            "semiconductor", "chip technology", "microprocessor",
            "integrated circuit", "silicon technology", "chip manufacturing",
            "foundry", "EUV lithography", "advanced packaging",
            "processor architecture", "memory technology", "TSMC", "ASML"
        ],
        "weight": 0.8
    },

    "tech_policy": {
        "keywords": [
            "technology policy", "innovation policy", "R&D policy",
            "science policy", "digital policy", "AI policy",
            "tech regulation", "innovation strategy", "national strategy",
            "research funding", "government grants", "public funding",
            "export control", "technology transfer", "intellectual property"
        ],
        "weight": 1.0
    },

    "industry_development": {
        "keywords": [
            "digital transformation", "industry 4.0", "smart manufacturing",
            "automation", "robotics", "IoT", "digital economy",
            "platform economy", "fintech", "blockchain", "cryptocurrency",
            "renewable energy", "electric vehicle", "space technology",
            "clean energy", "energy storage", "battery technology"
        ],
        "weight": 0.7
    },

    "international_cooperation": {
        "keywords": [
            "international collaboration", "research partnership",
            "joint research", "bilateral cooperation", "multilateral cooperation",
            "technology transfer", "trade war", "supply chain",
            "tech decoupling", "sanctions", "global governance",
            "scientific cooperation", "knowledge exchange"
        ],
        "weight": 0.8
    },

    "key_institutions": {
        "keywords": [
            "MIT", "Stanford", "Harvard", "Caltech", "Berkeley",
            "DARPA", "NSF", "NIH", "NASA", "European Commission",
            "Horizon Europe", "RIKEN", "Max Planck", "CERN",
            "Fraunhofer", "CNRS", "KAIST", "A*STAR"
        ],
        "weight": 0.6
    }
}
```

## 配置选项

### 国际科技新闻筛选配置

```python
# config/filter_settings.py

INTERNATIONAL_FILTER_CONFIG = {
    # 基础配置
    "threshold": 0.65,          # 相关性阈值（英文筛选稍高）
    "max_results": 150,         # 最大结果数（国际新闻量大）
    "min_matches": 2,           # 最少匹配关键词数
    "case_sensitive": False,    # 大小写不敏感

    # 英文文本处理配置
    "word_boundary": True,      # 启用单词边界检查
    "stem_matching": False,     # 暂不启用词干匹配（保持简单）
    "phrase_matching": True,    # 启用短语匹配
    "min_keyword_length": 2,    # 最小关键词长度

    # 评分配置
    "position_weights": {
        "title": 3.0,
        "summary": 2.0,
        "content": 1.0
    },

    # 分类权重（与关键词库保持一致）
    "category_weights": {
        "ai_technology": 1.0,
        "quantum_technology": 0.9,
        "biotechnology": 0.9,
        "semiconductor": 0.8,
        "tech_policy": 1.0,
        "industry_development": 0.7,
        "international_cooperation": 0.8,
        "key_institutions": 0.6
    },

    # 性能配置
    "batch_size": 50,           # 批处理大小
    "timeout": 30,              # 处理超时时间
    "max_content_length": 5000, # 最大内容长度
}

# 配置加载函数
def load_filter_config(target: str = "international") -> dict:
    """加载筛选配置"""
    if target == "international":
        config = INTERNATIONAL_FILTER_CONFIG.copy()
        config["keywords"] = INTERNATIONAL_TECH_KEYWORDS
        return config
    else:
        raise ValueError(f"Unknown target: {target}")
```

### 动态配置管理

```python
# src/config/config_manager.py

class FilterConfigManager:
    def __init__(self):
        self.configs = {}
        self.load_default_configs()

    def load_default_configs(self):
        """加载默认配置"""
        self.configs["international"] = load_filter_config("international")

    def get_config(self, target: str) -> dict:
        """获取配置"""
        if target not in self.configs:
            raise ValueError(f"Config for target '{target}' not found")
        return self.configs[target].copy()

    def update_config(self, target: str, **kwargs):
        """更新配置参数"""
        if target not in self.configs:
            raise ValueError(f"Config for target '{target}' not found")

        config = self.configs[target]
        for key, value in kwargs.items():
            if key in config:
                config[key] = value
            else:
                print(f"Warning: Unknown config key '{key}'")

    def adjust_for_source_type(self, target: str, source_type: str) -> dict:
        """根据新闻源类型调整配置"""
        config = self.get_config(target)

        # 根据不同新闻源调整阈值
        adjustments = {
            "academic": {"threshold": 0.7, "min_matches": 3},  # 学术源要求更高
            "news": {"threshold": 0.6, "min_matches": 2},      # 新闻源标准要求
            "policy": {"threshold": 0.8, "min_matches": 2},    # 政策源重点关注
            "industry": {"threshold": 0.65, "min_matches": 2}  # 产业源平衡要求
        }

        if source_type in adjustments:
            config.update(adjustments[source_type])

        return config
```

## 测试计划

### 单元测试

```python
# tests/test_keyword_filter.py

class TestKeywordMatcher:
    def test_exact_keyword_matching(self):
        """测试精确关键词匹配"""
        matcher = KeywordMatcher(test_config)
        text = "Artificial intelligence breakthrough in quantum computing"
        matches = matcher.find_matches(text)

        # 验证匹配结果
        assert len(matches) >= 2  # 应该匹配AI和量子计算
        keywords = [m.keyword for m in matches]
        assert "artificial intelligence" in keywords
        assert "quantum computing" in keywords

    def test_word_boundary_matching(self):
        """测试单词边界匹配"""
        matcher = KeywordMatcher(test_config)
        text = "The AI research team developed new algorithms"
        matches = matcher.find_matches(text)

        # "AI" 应该作为独立单词被匹配
        ai_matches = [m for m in matches if "AI" in m.keyword]
        assert len(ai_matches) > 0

    def test_case_insensitive_matching(self):
        """测试大小写不敏感匹配"""
        matcher = KeywordMatcher(test_config)
        text = "MACHINE LEARNING and Deep Learning applications"
        matches = matcher.find_matches(text)

        # 应该匹配不同大小写的关键词
        keywords = [m.keyword.lower() for m in matches]
        assert "machine learning" in keywords
        assert "deep learning" in keywords

    def test_phrase_matching(self):
        """测试短语匹配"""
        matcher = KeywordMatcher(test_config)
        text = "Natural language processing advances in AI"
        matches = matcher.find_matches(text)

        # 应该匹配完整短语而不是单个词
        assert any("natural language processing" in m.keyword.lower() for m in matches)

class TestRelevanceScorer:
    def test_basic_scoring(self):
        """测试基础评分功能"""
        scorer = RelevanceScorer(test_config)
        matches = [
            KeywordMatch("artificial intelligence", "ai_technology", 0, "context", "exact"),
            KeywordMatch("machine learning", "ai_technology", 50, "context", "exact")
        ]

        score = scorer.calculate_score(matches, test_article)
        assert 0 <= score <= 1
        assert score > 0.5  # 多个AI关键词应该得高分

    def test_position_weighting(self):
        """测试位置权重"""
        scorer = RelevanceScorer(test_config)
        article = create_test_article(
            title="AI breakthrough",
            summary="Machine learning advances",
            content="Deep learning applications in various fields"
        )

        # 标题中的匹配应该得分更高
        title_match = KeywordMatch("AI", "ai_technology", 0, "context", "exact")
        content_match = KeywordMatch("deep learning", "ai_technology", 100, "context", "exact")

        title_score = scorer._calculate_position_score([title_match], article)
        content_score = scorer._calculate_position_score([content_match], article)

        assert title_score > content_score

    def test_category_scoring(self):
        """测试分类评分"""
        scorer = RelevanceScorer(test_config)
        matches = [
            KeywordMatch("AI policy", "tech_policy", 0, "context", "exact"),
            KeywordMatch("quantum computing", "quantum_technology", 50, "context", "exact")
        ]

        category_scores = scorer.calculate_category_scores(matches)

        # 应该为每个分类计算分数
        assert "tech_policy" in category_scores
        assert "quantum_technology" in category_scores
        assert all(score > 0 for score in category_scores.values())

class TestKeywordFilter:
    def test_filter_single_article(self):
        """测试单篇文章筛选"""
        filter_instance = KeywordFilter(test_config)
        article = create_test_article(
            title="Breakthrough in artificial intelligence research",
            summary="Scientists develop new machine learning algorithms",
            content="The research focuses on deep learning applications..."
        )

        result = filter_instance.filter_single(article)

        assert result is not None
        assert result.relevance_score > 0.6
        assert len(result.matched_keywords) >= 2
        assert "ai_technology" in result.category_scores

    def test_threshold_filtering(self):
        """测试阈值过滤"""
        config = test_config.copy()
        config["threshold"] = 0.8  # 设置高阈值

        filter_instance = KeywordFilter(config)

        # 低相关性文章
        low_article = create_test_article("General technology news today")
        result_low = filter_instance.filter_single(low_article)

        # 高相关性文章
        high_article = create_test_article(
            "AI breakthrough in quantum computing research funding"
        )
        result_high = filter_instance.filter_single(high_article)

        # 低相关性应该被过滤，高相关性应该通过
        assert result_low is None or result_low.relevance_score < 0.8
        assert result_high is not None and result_high.relevance_score >= 0.8

    def test_batch_filtering(self):
        """测试批量筛选"""
        filter_instance = KeywordFilter(test_config)
        articles = [
            create_test_article("AI research breakthrough announced"),
            create_test_article("Quantum computing milestone achieved"),
            create_test_article("Weather forecast for tomorrow"),  # 不相关
            create_test_article("CRISPR gene editing advances"),
            create_test_article("Sports news update")  # 不相关
        ]

        results = filter_instance.filter(articles)

        # 应该筛选出3篇相关文章，过滤掉2篇不相关的
        assert len(results) == 3
        assert all(r.relevance_score >= test_config["threshold"] for r in results)

        # 验证结果按相关性排序
        scores = [r.relevance_score for r in results]
        assert scores == sorted(scores, reverse=True)

class TestConfigManager:
    def test_config_loading(self):
        """测试配置加载"""
        manager = FilterConfigManager()
        config = manager.get_config("international")

        assert "threshold" in config
        assert "keywords" in config
        assert "category_weights" in config

    def test_config_adjustment(self):
        """测试配置调整"""
        manager = FilterConfigManager()

        # 测试学术源配置调整
        academic_config = manager.adjust_for_source_type("international", "academic")
        assert academic_config["threshold"] == 0.7
        assert academic_config["min_matches"] == 3

        # 测试新闻源配置调整
        news_config = manager.adjust_for_source_type("international", "news")
        assert news_config["threshold"] == 0.6
        assert news_config["min_matches"] == 2
```

### 集成测试

```python
# tests/test_integration.py

class TestFilterIntegration:
    def test_end_to_end_filtering(self):
        """测试端到端筛选流程"""
        # 使用真实配置和模拟文章数据
        config = load_filter_config("international")
        filter_instance = KeywordFilter(config)

        # 模拟从RSS源获取的文章
        articles = load_test_articles("international_tech_news.json")

        results = filter_instance.filter(articles)

        # 验证筛选结果
        assert len(results) > 0
        assert all(r.relevance_score >= config["threshold"] for r in results)

        # 验证分类分布
        categories = set()
        for result in results:
            categories.update(result.category_scores.keys())

        # 应该覆盖多个技术分类
        assert len(categories) >= 3

    def test_performance_benchmark(self):
        """测试性能基准"""
        config = load_filter_config("international")
        filter_instance = KeywordFilter(config)

        # 生成1000篇测试文章
        articles = generate_test_articles(1000)

        start_time = time.time()
        results = filter_instance.filter(articles)
        end_time = time.time()

        processing_time = end_time - start_time
        articles_per_second = len(articles) / processing_time

        # 性能要求：> 50篇/秒
        assert articles_per_second > 50

        # 内存使用检查
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        assert memory_mb < 200  # < 200MB

    def test_real_world_accuracy(self):
        """测试真实世界准确性"""
        # 使用人工标注的测试数据集
        labeled_articles = load_labeled_test_data()

        config = load_filter_config("international")
        filter_instance = KeywordFilter(config)

        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        for article, expected_relevant in labeled_articles:
            result = filter_instance.filter_single(article)
            predicted_relevant = result is not None and result.relevance_score >= config["threshold"]

            if expected_relevant and predicted_relevant:
                true_positives += 1
            elif not expected_relevant and not predicted_relevant:
                true_negatives += 1
            elif not expected_relevant and predicted_relevant:
                false_positives += 1
            else:  # expected_relevant and not predicted_relevant
                false_negatives += 1

        # 计算指标
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        accuracy = (true_positives + true_negatives) / len(labeled_articles)

        # 性能要求
        assert precision > 0.8  # 精确率 > 80%
        assert recall > 0.75    # 召回率 > 75%
        assert accuracy > 0.8   # 准确率 > 80%
```

## 性能考虑

### 优化策略

#### 1. 文本处理优化
```python
class OptimizedTextProcessor:
    def __init__(self):
        # 预编译常用正则表达式
        self.html_pattern = re.compile(r'<[^>]+>')
        self.whitespace_pattern = re.compile(r'\s+')
        self.word_pattern = re.compile(r'\b\w+\b')

    def fast_clean_text(self, text: str) -> str:
        """快速文本清理"""
        # 使用预编译的正则表达式
        text = self.html_pattern.sub('', text)
        text = self.whitespace_pattern.sub(' ', text)
        return text.strip()
```

#### 2. 关键词匹配优化
```python
class OptimizedKeywordMatcher:
    def __init__(self, keywords: Dict[str, List[str]]):
        # 构建高效的关键词查找结构
        self.keyword_trie = self._build_trie(keywords)
        self.keyword_patterns = self._compile_patterns(keywords)

    def _build_trie(self, keywords: Dict[str, List[str]]):
        """构建Trie树用于快速匹配"""
        # 实现Trie树结构
        pass

    def _compile_patterns(self, keywords: Dict[str, List[str]]):
        """预编译关键词正则表达式"""
        patterns = {}
        for category, words in keywords.items():
            # 将关键词组合成单个正则表达式
            pattern = r'\b(?:' + '|'.join(re.escape(word) for word in words) + r')\b'
            patterns[category] = re.compile(pattern, re.IGNORECASE)
        return patterns
```

#### 3. 批量处理优化
- **内存管理**：及时释放处理完的文章数据
- **流式处理**：避免一次性加载所有文章到内存
- **并行处理**：使用多进程处理大批量文章

#### 4. 缓存策略
- **结果缓存**：缓存已处理文章的筛选结果
- **配置缓存**：缓存加载的关键词配置
- **文本预处理缓存**：缓存清理后的文本内容

### 性能指标

#### 目标性能
- **处理速度**：> 50篇文章/秒（单线程）
- **内存使用**：< 200MB（处理1000篇文章）
- **准确率**：> 85%（与人工标注对比）
- **召回率**：> 80%（相关文章覆盖率）
- **响应时间**：< 100ms（单篇文章处理）

#### 性能监控
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'processing_times': [],
            'memory_usage': [],
            'accuracy_scores': [],
            'throughput': []
        }

    def record_processing_time(self, time_ms: float):
        self.metrics['processing_times'].append(time_ms)

    def get_performance_summary(self) -> Dict:
        return {
            'avg_processing_time': np.mean(self.metrics['processing_times']),
            'p95_processing_time': np.percentile(self.metrics['processing_times'], 95),
            'throughput_per_second': 1000 / np.mean(self.metrics['processing_times'])
        }
```

## 扩展性设计

### 模块化架构
```python
# 可插拔的筛选器架构
class FilterPipeline:
    def __init__(self):
        self.filters = []

    def add_filter(self, filter_instance):
        """添加筛选器到管道"""
        self.filters.append(filter_instance)

    def process(self, articles: List[Article]) -> List[FilterResult]:
        """执行筛选管道"""
        results = articles
        for filter_instance in self.filters:
            results = filter_instance.filter(results)
        return results
```

### 未来扩展方向

#### 1. 智能关键词扩展
```python
class IntelligentKeywordExpander:
    def __init__(self, embedding_model):
        self.embedding_model = embedding_model

    def expand_keywords(self, base_keywords: List[str]) -> List[str]:
        """基于语义相似性扩展关键词"""
        # 使用词向量模型找到相似词汇
        expanded = []
        for keyword in base_keywords:
            similar_words = self.embedding_model.most_similar(keyword, topn=5)
            expanded.extend([word for word, score in similar_words if score > 0.7])
        return expanded
```

#### 2. 动态权重调整
```python
class AdaptiveWeightManager:
    def __init__(self):
        self.feedback_data = []

    def update_weights(self, feedback: List[Tuple[str, bool]]):
        """根据用户反馈调整关键词权重"""
        # 分析用户反馈，调整分类权重
        pass

    def get_adjusted_weights(self) -> Dict[str, float]:
        """获取调整后的权重"""
        pass
```

#### 3. 实时关键词更新
```python
class DynamicKeywordManager:
    def __init__(self, update_interval: int = 3600):
        self.update_interval = update_interval
        self.last_update = 0

    def check_for_updates(self):
        """检查关键词库更新"""
        if time.time() - self.last_update > self.update_interval:
            self.update_keywords()

    def update_keywords(self):
        """从外部源更新关键词库"""
        # 从配置文件、API或数据库更新关键词
        pass
```

#### 4. 多源融合筛选
```python
class MultiSourceFilter:
    def __init__(self):
        self.source_configs = {}

    def add_source_config(self, source_name: str, config: dict):
        """为不同新闻源添加专门配置"""
        self.source_configs[source_name] = config

    def filter_by_source(self, articles: List[Article], source: str):
        """根据新闻源使用不同筛选策略"""
        config = self.source_configs.get(source, self.default_config)
        return self.filter_with_config(articles, config)
```

### 插件接口设计

#### 自定义筛选器接口
```python
from abc import ABC, abstractmethod

class FilterPlugin(ABC):
    @abstractmethod
    def filter(self, articles: List[Article]) -> List[FilterResult]:
        """筛选文章的抽象方法"""
        pass

    @abstractmethod
    def get_config_schema(self) -> Dict:
        """返回配置模式"""
        pass

class CustomTechFilter(FilterPlugin):
    def filter(self, articles: List[Article]) -> List[FilterResult]:
        """自定义技术筛选逻辑"""
        # 实现特定的筛选算法
        pass

    def get_config_schema(self) -> Dict:
        return {
            "threshold": {"type": "float", "default": 0.6},
            "categories": {"type": "list", "default": []}
        }
```

#### 评分器插件接口
```python
class ScoringPlugin(ABC):
    @abstractmethod
    def calculate_score(self, matches: List[KeywordMatch],
                       article: Article) -> float:
        """计算自定义评分"""
        pass

class MLBasedScorer(ScoringPlugin):
    def __init__(self, model_path: str):
        self.model = self.load_model(model_path)

    def calculate_score(self, matches: List[KeywordMatch],
                       article: Article) -> float:
        """使用机器学习模型计算评分"""
        features = self.extract_features(matches, article)
        return self.model.predict_proba(features)[0][1]
```

这个扩展性设计确保了系统能够：
1. **适应变化**：支持新的筛选需求和算法
2. **性能优化**：持续改进处理速度和准确性
3. **功能扩展**：轻松添加新的筛选维度和评分方法
4. **配置灵活**：支持不同场景的配置需求
