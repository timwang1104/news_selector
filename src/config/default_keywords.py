"""
默认关键词配置
"""

# 国际科技政策关键词库
INTERNATIONAL_TECH_KEYWORDS = {
    "artificial_intelligence": {
        "keywords": [
            "artificial intelligence", "AI", "machine learning", "deep learning",
            "neural networks", "natural language processing", "computer vision",
            "robotics", "automation", "intelligent systems", "cognitive computing",
            "expert systems", "knowledge graphs", "reinforcement learning",
            "generative AI", "large language models", "ChatGPT", "GPT",
            "人工智能", "机器学习", "深度学习", "神经网络", "自然语言处理",
            "计算机视觉", "机器人", "自动化", "智能系统", "认知计算"
        ],
        "weight": 1.0
    },
    "quantum_computing": {
        "keywords": [
            "quantum computing", "quantum computer", "quantum algorithm",
            "quantum supremacy", "quantum entanglement", "quantum cryptography",
            "quantum communication", "quantum sensing", "quantum simulation",
            "qubit", "quantum gate", "quantum error correction",
            "量子计算", "量子计算机", "量子算法", "量子霸权", "量子纠缠",
            "量子密码", "量子通信", "量子传感", "量子模拟", "量子比特"
        ],
        "weight": 0.9
    },
    "biotechnology": {
        "keywords": [
            "biotechnology", "genetic engineering", "gene editing", "CRISPR",
            "synthetic biology", "bioengineering", "genomics", "proteomics",
            "bioinformatics", "personalized medicine", "gene therapy",
            "stem cells", "regenerative medicine", "biomarkers",
            "生物技术", "基因工程", "基因编辑", "合成生物学", "生物工程",
            "基因组学", "蛋白质组学", "生物信息学", "个性化医疗", "基因治疗"
        ],
        "weight": 0.9
    },
    "blockchain_crypto": {
        "keywords": [
            "blockchain", "cryptocurrency", "bitcoin", "ethereum", "smart contracts",
            "distributed ledger", "decentralized", "DeFi", "NFT", "Web3",
            "digital currency", "crypto", "mining", "consensus mechanism",
            "区块链", "加密货币", "比特币", "以太坊", "智能合约",
            "分布式账本", "去中心化", "数字货币", "挖矿", "共识机制"
        ],
        "weight": 0.8
    },
    "renewable_energy": {
        "keywords": [
            "renewable energy", "solar energy", "wind energy", "hydroelectric",
            "geothermal", "biomass", "energy storage", "battery technology",
            "electric vehicles", "smart grid", "energy efficiency",
            "carbon neutral", "clean energy", "green technology",
            "可再生能源", "太阳能", "风能", "水电", "地热能", "生物质能",
            "储能", "电池技术", "电动汽车", "智能电网", "能源效率", "碳中和"
        ],
        "weight": 0.8
    },
    "space_technology": {
        "keywords": [
            "space technology", "satellite", "rocket", "space exploration",
            "Mars mission", "lunar mission", "space station", "SpaceX",
            "NASA", "ESA", "commercial space", "space tourism",
            "space debris", "asteroid mining", "space colonization",
            "航天技术", "卫星", "火箭", "太空探索", "火星任务", "月球任务",
            "空间站", "商业航天", "太空旅游", "太空垃圾", "小行星采矿"
        ],
        "weight": 0.8
    },
    "cybersecurity": {
        "keywords": [
            "cybersecurity", "information security", "data protection",
            "privacy", "encryption", "cyber attack", "malware", "ransomware",
            "phishing", "vulnerability", "penetration testing", "firewall",
            "zero trust", "threat intelligence", "incident response",
            "网络安全", "信息安全", "数据保护", "隐私保护", "加密",
            "网络攻击", "恶意软件", "勒索软件", "钓鱼攻击", "漏洞", "防火墙"
        ],
        "weight": 0.9
    },
    "semiconductor": {
        "keywords": [
            "semiconductor", "chip", "microprocessor", "integrated circuit",
            "silicon", "wafer", "fabrication", "lithography", "EUV",
            "Moore's law", "nanotechnology", "quantum dots", "graphene",
            "TSMC", "Intel", "AMD", "NVIDIA", "chip shortage",
            "半导体", "芯片", "微处理器", "集成电路", "硅", "晶圆",
            "制造", "光刻", "纳米技术", "量子点", "石墨烯", "芯片短缺"
        ],
        "weight": 0.9
    },
    "5g_6g_networks": {
        "keywords": [
            "5G", "6G", "wireless communication", "mobile networks",
            "telecommunications", "network infrastructure", "edge computing",
            "IoT", "Internet of Things", "connected devices", "smart cities",
            "autonomous vehicles", "telemedicine", "augmented reality", "VR",
            "无线通信", "移动网络", "电信", "网络基础设施", "边缘计算",
            "物联网", "智能城市", "自动驾驶", "远程医疗", "增强现实", "虚拟现实"
        ],
        "weight": 0.8
    },
    "climate_technology": {
        "keywords": [
            "climate technology", "carbon capture", "carbon storage",
            "climate change", "greenhouse gas", "emission reduction",
            "sustainable development", "green innovation", "clean technology",
            "environmental protection", "circular economy", "waste management",
            "气候技术", "碳捕获", "碳储存", "气候变化", "温室气体", "减排",
            "可持续发展", "绿色创新", "清洁技术", "环境保护", "循环经济"
        ],
        "weight": 0.8
    },
    "advanced_materials": {
        "keywords": [
            "advanced materials", "nanomaterials", "metamaterials",
            "superconductors", "smart materials", "composite materials",
            "2D materials", "carbon nanotubes", "perovskites",
            "biomaterials", "self-healing materials", "shape memory alloys",
            "先进材料", "纳米材料", "超材料", "超导体", "智能材料",
            "复合材料", "二维材料", "碳纳米管", "生物材料", "自修复材料"
        ],
        "weight": 0.7
    },
    "digital_transformation": {
        "keywords": [
            "digital transformation", "digitalization", "Industry 4.0",
            "smart manufacturing", "digital twin", "cloud computing",
            "big data", "data analytics", "business intelligence",
            "automation", "process optimization", "digital economy",
            "数字化转型", "数字化", "工业4.0", "智能制造", "数字孪生",
            "云计算", "大数据", "数据分析", "商业智能", "流程优化", "数字经济"
        ],
        "weight": 0.8
    },
    "international_cooperation": {
        "keywords": [
            "international collaboration", "research partnership",
            "joint research", "bilateral cooperation", "multilateral cooperation",
            "technology transfer", "trade war", "supply chain",
            "tech decoupling", "sanctions", "global governance",
            "scientific cooperation", "knowledge exchange",
            "国际合作", "研究伙伴关系", "联合研究", "双边合作", "多边合作",
            "技术转移", "贸易战", "供应链", "技术脱钩", "制裁", "全球治理"
        ],
        "weight": 0.8
    },
    "key_institutions": {
        "keywords": [
            "MIT", "Stanford", "Harvard", "Caltech", "Berkeley",
            "DARPA", "NSF", "NIH", "NASA", "European Commission",
            "Horizon Europe", "RIKEN", "Max Planck", "CERN",
            "Fraunhofer", "CNRS", "KAIST", "A*STAR",
            "中科院", "清华大学", "北京大学", "科技部", "工信部"
        ],
        "weight": 0.6
    }
}
