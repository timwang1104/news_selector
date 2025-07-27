"""
预设RSS订阅源数据
"""

# 预设的RSS订阅源列表
PRESET_RSS_FEEDS = [
    # 科技新闻
    {
        "name": "TechCrunch",
        "url": "https://techcrunch.com/feed/",
        "category": "科技新闻",
        "description": "全球领先的科技创业和创新新闻"
    },
    {
        "name": "Ars Technica",
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "category": "科技新闻", 
        "description": "深度科技新闻和分析"
    },
    {
        "name": "The Verge",
        "url": "https://www.theverge.com/rss/index.xml",
        "category": "科技新闻",
        "description": "科技、科学、艺术和文化交叉领域新闻"
    },
    {
        "name": "Wired",
        "url": "https://www.wired.com/feed/rss",
        "category": "科技新闻",
        "description": "科技如何改变文化、经济和政治"
    },
    {
        "name": "Engadget",
        "url": "https://www.engadget.com/rss.xml",
        "category": "科技新闻",
        "description": "消费电子和科技产品新闻"
    },
    {
        "name": "CNET",
        "url": "https://www.cnet.com/rss/news/",
        "category": "科技新闻",
        "description": "科技新闻、评测和购买指南"
    },
    {
        "name": "ZDNet",
        "url": "https://www.zdnet.com/news/rss.xml",
        "category": "科技新闻",
        "description": "企业技术和IT新闻"
    },
    {
        "name": "BBC Technology",
        "url": "http://feeds.bbci.co.uk/news/technology/rss.xml",
        "category": "科技新闻",
        "description": "BBC科技新闻"
    },
    {
        "name": "Reuters Technology",
        "url": "https://feeds.reuters.com/reuters/technologyNews",
        "category": "科技新闻",
        "description": "路透社科技新闻"
    },
    {
        "name": "VentureBeat",
        "url": "https://venturebeat.com/feed/",
        "category": "科技新闻",
        "description": "科技创业和创新新闻"
    },
    {
        "name": "Mashable Tech",
        "url": "https://mashable.com/feeds/rss/tech",
        "category": "科技新闻",
        "description": "数字文化和科技新闻"
    },
    
    # 中文科技新闻
    {
        "name": "36氪",
        "url": "https://36kr.com/feed",
        "category": "中文科技",
        "description": "中国领先的科技创投媒体"
    },
    {
        "name": "虎嗅网",
        "url": "https://www.huxiu.com/rss/0.xml",
        "category": "中文科技",
        "description": "个性化商业资讯与观点交流平台"
    },
    {
        "name": "少数派",
        "url": "https://sspai.com/feed",
        "category": "中文科技",
        "description": "高质量数字生活指南"
    },
    {
        "name": "爱范儿",
        "url": "https://www.ifanr.com/feed",
        "category": "中文科技",
        "description": "让未来触手可及"
    },
    
    # 人工智能
    {
        "name": "AI News",
        "url": "https://artificialintelligence-news.com/feed/",
        "category": "人工智能",
        "description": "人工智能行业新闻和趋势"
    },
    {
        "name": "MIT Technology Review AI",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
        "category": "人工智能",
        "description": "MIT科技评论AI专栏"
    },
    {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/feed/",
        "category": "科技新闻",
        "description": "MIT科技评论主站"
    },
    {
        "name": "AI Research",
        "url": "https://airesearch.com/feed/",
        "category": "人工智能",
        "description": "AI研究和发展动态"
    },
    {
        "name": "OpenAI Blog",
        "url": "https://openai.com/blog/rss.xml",
        "category": "人工智能",
        "description": "OpenAI官方博客"
    },
    {
        "name": "机器之心",
        "url": "https://www.jiqizhixin.com/rss",
        "category": "人工智能",
        "description": "专业的人工智能媒体和产业服务平台"
    },
    
    # 区块链与加密货币
    {
        "name": "CoinDesk",
        "url": "https://feeds.feedburner.com/CoinDesk",
        "category": "区块链",
        "description": "数字货币和区块链新闻领导者"
    },
    {
        "name": "Cointelegraph",
        "url": "https://cointelegraph.com/rss",
        "category": "区块链",
        "description": "区块链新闻、价格、分析"
    },
    {
        "name": "链闻",
        "url": "https://www.chainnews.com/feed.xml",
        "category": "区块链",
        "description": "区块链新闻快讯与深度分析"
    },
    
    # 开发者与编程
    {
        "name": "GitHub Blog",
        "url": "https://github.blog/feed/",
        "category": "开发者",
        "description": "GitHub官方博客"
    },
    {
        "name": "Stack Overflow Blog",
        "url": "https://stackoverflow.blog/feed/",
        "category": "开发者",
        "description": "Stack Overflow官方博客"
    },
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "开发者",
        "description": "黑客新闻前页"
    },
    {
        "name": "Dev.to",
        "url": "https://dev.to/feed",
        "category": "开发者",
        "description": "开发者社区"
    },
    {
        "name": "阮一峰的网络日志",
        "url": "http://www.ruanyifeng.com/blog/atom.xml",
        "category": "开发者",
        "description": "技术博客和周刊"
    },
    {
        "name": "InfoWorld",
        "url": "https://www.infoworld.com/index.rss",
        "category": "开发者",
        "description": "企业技术和软件开发新闻"
    },
    {
        "name": "TechRepublic",
        "url": "https://www.techrepublic.com/rssfeeds/articles/",
        "category": "开发者",
        "description": "IT专业人士资源和新闻"
    },
    
    # 产业与商业
    {
        "name": "Harvard Business Review",
        "url": "https://feeds.hbr.org/harvardbusiness",
        "category": "商业",
        "description": "哈佛商业评论"
    },
    {
        "name": "Fast Company",
        "url": "https://www.fastcompany.com/rss.xml",
        "category": "商业",
        "description": "创新商业思想和设计"
    },
    {
        "name": "Forbes Technology",
        "url": "https://www.forbes.com/technology/feed/",
        "category": "商业",
        "description": "福布斯科技频道"
    },
    {
        "name": "经济学人",
        "url": "https://www.economist.com/rss.xml",
        "category": "商业",
        "description": "全球经济和政治分析"
    },
    
    # 设计与创意
    {
        "name": "Smashing Magazine",
        "url": "https://www.smashingmagazine.com/feed/",
        "category": "设计",
        "description": "网页设计和开发"
    },
    {
        "name": "A List Apart",
        "url": "https://alistapart.com/main/feed/",
        "category": "设计",
        "description": "网页设计、开发和内容"
    },
    {
        "name": "Designer News",
        "url": "https://www.designernews.co/rss",
        "category": "设计",
        "description": "设计师社区新闻"
    },
    
    # 科学与研究
    {
        "name": "Nature News",
        "url": "https://www.nature.com/nature.rss",
        "category": "科学",
        "description": "自然科学研究新闻"
    },
    {
        "name": "Science News",
        "url": "https://www.sciencenews.org/feed",
        "category": "科学",
        "description": "科学新闻和发现"
    },
    {
        "name": "IEEE Spectrum",
        "url": "https://spectrum.ieee.org/rss/fulltext",
        "category": "科学",
        "description": "工程技术新闻"
    },
    {
        "name": "New Scientist",
        "url": "https://www.newscientist.com/feed/home/",
        "category": "科学",
        "description": "科学发现和技术创新"
    },
    {
        "name": "Scientific American",
        "url": "http://rss.sciam.com/ScientificAmerican-Global",
        "category": "科学",
        "description": "科学美国人杂志"
    },
    
    # 游戏与娱乐
    {
        "name": "GameSpot",
        "url": "https://www.gamespot.com/feeds/mashup/",
        "category": "游戏",
        "description": "游戏新闻和评测"
    },
    {
        "name": "IGN",
        "url": "https://feeds.ign.com/ign/all",
        "category": "游戏",
        "description": "游戏、电影、电视新闻"
    },
    {
        "name": "机核网",
        "url": "https://www.gcores.com/rss",
        "category": "游戏",
        "description": "游戏文化媒体"
    },
    
    # 政府科技决策
    {
        "name": "美国白宫新闻",
        "url": "https://www.whitehouse.gov/feed/",
        "category": "政府科技",
        "description": "美国白宫官方新闻发布"
    },
    {
        "name": "美国国家标准技术研究院",
        "url": "https://www.nist.gov/news/rss.xml",
        "category": "政府科技",
        "description": "NIST技术标准和研究新闻"
    },
    {
        "name": "英国政府新闻",
        "url": "https://www.gov.uk/search/news-and-communications.atom",
        "category": "政府科技",
        "description": "英国政府官方新闻发布"
    },
    {
        "name": "德国健康研究部",
        "url": "https://www.gesundheitsforschung-bmbf.de/rss-feed-5806.php",
        "category": "政府科技",
        "description": "德国联邦教育研究部健康研究新闻"
    },
    {
        "name": "加拿大政府新闻",
        "url": "https://www.canada.ca/en/news/web-feeds.html",
        "category": "政府科技",
        "description": "加拿大政府官方新闻发布"
    },
    {
        "name": "澳大利亚工业科学部",
        "url": "https://www.industry.gov.au/contact-us/rss-feeds",
        "category": "政府科技",
        "description": "澳大利亚工业科学与资源部新闻"
    }
]

# 按分类组织的RSS源
RSS_CATEGORIES = {
    "科技新闻": ["TechCrunch", "Ars Technica", "The Verge", "Wired", "Engadget", "CNET", "ZDNet", "BBC Technology", "Reuters Technology", "VentureBeat", "Mashable Tech", "MIT Technology Review"],
    "中文科技": ["36氪", "虎嗅网", "少数派", "爱范儿"],
    "人工智能": ["AI News", "MIT Technology Review AI", "AI Research", "OpenAI Blog", "机器之心"],
    "区块链": ["CoinDesk", "Cointelegraph", "链闻"],
    "开发者": ["GitHub Blog", "Stack Overflow Blog", "Hacker News", "Dev.to", "阮一峰的网络日志", "InfoWorld", "TechRepublic"],
    "商业": ["Harvard Business Review", "Fast Company", "Forbes Technology", "经济学人"],
    "设计": ["Smashing Magazine", "A List Apart", "Designer News"],
    "科学": ["Nature News", "Science News", "IEEE Spectrum", "New Scientist", "Scientific American"],
    "游戏": ["GameSpot", "IGN", "机核网"],
    "政府科技": ["美国白宫新闻", "美国国家标准技术研究院", "英国政府新闻", "德国健康研究部", "加拿大政府新闻", "澳大利亚工业科学部"]
}

def get_feeds_by_category(category: str = None):
    """根据分类获取RSS源"""
    if category is None:
        return PRESET_RSS_FEEDS
    
    return [feed for feed in PRESET_RSS_FEEDS if feed["category"] == category]

def get_all_categories():
    """获取所有分类"""
    return list(RSS_CATEGORIES.keys())

def get_feed_by_name(name: str):
    """根据名称获取RSS源"""
    for feed in PRESET_RSS_FEEDS:
        if feed["name"] == name:
            return feed
    return None
