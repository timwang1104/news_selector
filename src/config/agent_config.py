"""
AI Agent配置管理
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class AgentAPIConfig:
    """Agent API配置"""
    # 基础配置
    name: str = "默认配置"
    description: str = ""
    
    # API设置
    api_key: str = ""
    base_url: str = ""
    model_name: str = "gpt-3.5-turbo"
    
    # 请求参数
    temperature: float = 0.3
    max_tokens: int = 1000
    timeout: int = 30
    retry_times: int = 3
    retry_delay: int = 1
    
    # 高级设置
    headers: Dict[str, str] = None
    proxy: str = ""
    verify_ssl: bool = True

    # 服务提供商标识
    provider: str = "openai"  # openai, siliconflow, anthropic, volcengine, moonshot, custom
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class AgentPromptConfig:
    """Agent提示词配置"""
    # 基础信息
    name: str = "默认提示词"
    description: str = ""
    version: str = "1.0"
    
    # 提示词内容
    system_prompt: str = ""
    evaluation_prompt: str = ""
    batch_evaluation_prompt: str = ""
    
    # 评估维度配置
    dimensions: List[Dict[str, str]] = None
    scoring_range: Dict[str, int] = None
    output_format: str = "json"
    
    # 示例和说明
    examples: List[Dict[str, str]] = None
    instructions: List[str] = None
    
    def __post_init__(self):
        if self.dimensions is None:
            self.dimensions = [
                {"name": "政策相关性", "description": "与科技政策的相关程度", "weight": 1.0},
                {"name": "创新影响", "description": "对科技创新的推动作用", "weight": 1.0},
                {"name": "实用性", "description": "可操作性和实施性", "weight": 1.0}
            ]
        if self.scoring_range is None:
            self.scoring_range = {"min": 0, "max": 10, "total_max": 30}
        if self.examples is None:
            self.examples = []
        if self.instructions is None:
            self.instructions = [
                "总分为各维度分数之和",
                "评估理由要具体明确",
                "置信度反映评估的确定程度"
            ]


@dataclass
class AgentConfig:
    """完整的Agent配置"""
    # 基础信息
    config_name: str = "默认Agent配置"
    created_at: str = ""
    updated_at: str = ""
    
    # 子配置
    api_config: AgentAPIConfig = None
    prompt_config: AgentPromptConfig = None
    
    # 使用设置
    is_active: bool = True
    is_default: bool = False
    
    def __post_init__(self):
        if self.api_config is None:
            self.api_config = AgentAPIConfig()
        if self.prompt_config is None:
            self.prompt_config = AgentPromptConfig()
        
        from datetime import datetime
        now = datetime.now().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class AgentConfigManager:
    """Agent配置管理器"""

    def __init__(self, config_dir: str = "config/agents"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.current_config_file = self.config_dir / "current_config.json"
        self.configs: Dict[str, AgentConfig] = {}
        self.current_config_name: Optional[str] = None
        self.load_all_configs()
    
    def load_all_configs(self):
        """加载所有配置"""
        # 加载保存的配置
        for config_file in self.config_dir.glob("*.json"):
            # 跳过当前配置文件
            if config_file.name == "current_config.json":
                continue

            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = self._dict_to_config(data)
                    self.configs[config.config_name] = config
            except Exception as e:
                print(f"加载配置文件 {config_file} 失败: {e}")

        # 如果没有配置，创建默认配置
        if not self.configs:
            self.create_default_config()

        # 加载当前配置名称
        self.load_current_config_name()

        # 设置当前配置
        if not self.current_config_name or self.current_config_name not in self.configs:
            # 优先使用标记为默认的配置
            default_configs = [name for name, config in self.configs.items() if config.is_default]
            if default_configs:
                self.current_config_name = default_configs[0]
            else:
                # 否则使用第一个配置
                self.current_config_name = list(self.configs.keys())[0]
            # 保存当前配置名称
            self.save_current_config_name()

        # 初始化时自动同步到FilterService
        self._sync_to_filter_service()
    
    def create_default_config(self):
        """创建默认配置"""
        # 从环境变量或现有配置加载默认值
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "")

        api_config = AgentAPIConfig(
            name="OpenAI GPT",
            description="OpenAI官方API配置",
            api_key=api_key,
            base_url=base_url,
            model_name="gpt-3.5-turbo"
        )

        # 使用简单的默认提示词，避免循环导入
        default_evaluation_prompt = """
你是上海市科委的专业顾问，请评估以下文章对上海科技发展的相关性和价值。

文章信息：
标题：{title}
摘要：{summary}
内容预览：{content_preview}

请从以下三个维度进行评估（每个维度0-10分）：

1. 政策相关性 (0-10分)
2. 创新影响 (0-10分)
3. 实用性 (0-10分)

请按以下JSON格式返回评估结果：
{{
    "relevance_score": <政策相关性分数>,
    "innovation_impact": <创新影响分数>,
    "practicality": <实用性分数>,
    "total_score": <总分>,
    "reasoning": "<详细评估理由>",
    "confidence": <置信度，0-1之间的小数>
}}
"""

        default_batch_prompt = """
你是上海市科委的专业顾问，请批量评估以下文章对上海科技发展的相关性和价值。

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。
"""

        prompt_config = AgentPromptConfig(
            name="科技政策评估",
            description="用于评估科技新闻对政策制定的价值",
            evaluation_prompt=default_evaluation_prompt,
            batch_evaluation_prompt=default_batch_prompt,
            system_prompt="你是上海市科委的专业顾问，专门负责评估科技新闻对政策制定的价值。"
        )

        default_config = AgentConfig(
            config_name="默认配置",
            api_config=api_config,
            prompt_config=prompt_config,
            is_default=True
        )

        self.configs["默认配置"] = default_config
        self.current_config_name = "默认配置"
        self.save_config("默认配置")

        # 创建硅基流动预设配置
        self.create_siliconflow_preset()

        # 创建火山引擎预设配置
        self.create_volcengine_preset()

        # 创建Moonshot预设配置
        self.create_moonshot_preset()

    def create_siliconflow_preset(self):
        """创建硅基流动预设配置"""
        # 检查是否已存在硅基流动配置
        if any("硅基流动" in name for name in self.configs.keys()):
            return

        # 从环境变量加载API Key
        siliconflow_api_key = os.getenv("SILICONFLOW_API_KEY", "")

        api_config = AgentAPIConfig(
            name="硅基流动平台",
            description="硅基流动平台多模型服务，支持Qwen、Kimi、DeepSeek等模型",
            api_key=siliconflow_api_key,
            base_url="https://api.siliconflow.cn/v1",
            model_name="Qwen/Qwen2.5-72B-Instruct",  # 默认使用Qwen
            temperature=0.3,
            max_tokens=2000,  # 增加以支持Kimi等长输出模型
            timeout=90,       # 增加以支持复杂模型
            provider="siliconflow"
        )

        # 针对硅基流动优化的提示词
        siliconflow_evaluation_prompt = """
你是上海市科委的专业顾问，请评估以下科技新闻文章对上海科技发展的相关性和价值。

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

请严格按照以下JSON格式返回评估结果，不要包含其他内容：
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
- 请确保返回的是有效的JSON格式
"""

        siliconflow_batch_prompt = """
你是上海市科委的专业顾问，请批量评估以下文章对上海科技发展的相关性和价值。

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。
评估维度和格式要求与单篇评估相同。

请严格按照以下JSON数组格式返回结果，不要包含其他内容：
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

        prompt_config = AgentPromptConfig(
            name="硅基流动科技政策评估",
            description="适用于硅基流动平台多种模型的科技政策评估提示词",
            version="1.0",
            system_prompt="你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。",
            evaluation_prompt=siliconflow_evaluation_prompt,
            batch_evaluation_prompt=siliconflow_batch_prompt
        )

        siliconflow_config = AgentConfig(
            config_name="硅基流动",
            api_config=api_config,
            prompt_config=prompt_config,
            is_default=False
        )

        self.configs["硅基流动"] = siliconflow_config
        self.save_config("硅基流动")

    def create_volcengine_preset(self):
        """创建火山引擎预设配置"""
        # 检查是否已存在火山引擎配置
        if any("火山引擎" in name for name in self.configs.keys()):
            return

        # 从环境变量加载API Key
        volcengine_api_key = os.getenv("VOLCENGINE_API_KEY", "")

        api_config = AgentAPIConfig(
            name="火山引擎平台",
            description="火山引擎豆包大模型服务，支持Doubao等模型",
            api_key=volcengine_api_key,
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            model_name="ep-20241219105016-8xqzm",  # 使用endpoint ID格式
            temperature=0.3,
            max_tokens=2000,
            timeout=90,
            provider="volcengine",
            headers={
                "Content-Type": "application/json"
            }
        )

        # 针对火山引擎优化的提示词
        volcengine_evaluation_prompt = """
你是上海市科委的专业顾问，请评估以下科技新闻文章对上海科技发展的相关性和价值。

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

请严格按照以下JSON格式返回评估结果，不要包含其他内容：
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
- 请确保返回的是有效的JSON格式
"""

        volcengine_batch_evaluation_prompt = """
你是上海市科委的专业顾问，请批量评估以下文章对上海科技发展的相关性和价值。

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。
评估维度和格式要求与单篇评估相同。

请严格按照以下JSON数组格式返回结果，不要包含其他内容：
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

注意：请确保返回的是有效的JSON数组格式，不要包含markdown代码块标记。
"""

        prompt_config = AgentPromptConfig(
            name="火山引擎科技政策评估",
            description="适用于火山引擎豆包模型的科技政策评估提示词",
            version="1.0",
            system_prompt="你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。",
            evaluation_prompt=volcengine_evaluation_prompt,
            batch_evaluation_prompt=volcengine_batch_evaluation_prompt,
            dimensions=[
                {"name": "政策相关性", "description": "与科技政策的相关程度", "weight": 1.0},
                {"name": "创新影响", "description": "对科技创新的推动作用", "weight": 1.0},
                {"name": "实用性", "description": "可操作性和实施性", "weight": 1.0}
            ],
            scoring_range={"min": 0, "max": 10, "total_max": 30},
            output_format="json",
            examples=[],
            instructions=[
                "总分为各维度分数之和",
                "评估理由要具体明确",
                "置信度反映评估的确定程度"
            ]
        )

        volcengine_config = AgentConfig(
            config_name="火山引擎",
            api_config=api_config,
            prompt_config=prompt_config,
            is_default=False
        )

        self.configs["火山引擎"] = volcengine_config
        self.save_config("火山引擎")

    def create_moonshot_preset(self):
        """创建Moonshot预设配置"""
        # 检查是否已存在Moonshot配置
        if any("Moonshot" in name or "moonshot" in name.lower() for name in self.configs.keys()):
            return

        # 从环境变量加载API Key
        moonshot_api_key = os.getenv("MOONSHOT_API_KEY", "")

        api_config = AgentAPIConfig(
            name="Moonshot平台",
            description="Moonshot AI平台，提供Kimi大模型服务，支持超长上下文",
            api_key=moonshot_api_key,
            base_url="https://api.moonshot.cn/v1",
            model_name="moonshot-v1-8k",  # 默认使用8k上下文模型
            temperature=0.3,
            max_tokens=2000,
            timeout=90,
            provider="moonshot",
            headers={
                "Content-Type": "application/json"
            }
        )

        # 针对Moonshot优化的提示词
        moonshot_evaluation_prompt = """
你是上海市科委的专业顾问，请评估以下科技新闻文章对上海科技发展的相关性和价值。

文章信息：
标题：{title}
摘要：{summary}
内容预览：{content_preview}

请从以下三个维度进行评估（每个维度0-10分）：

1. 政策相关性 (0-10分)：评估文章内容与上海科技政策、产业发展规划的相关程度
2. 创新影响 (0-10分)：评估文章所述技术或事件对科技创新的推动作用
3. 实用性 (0-10分)：评估文章内容的可操作性和对实际工作的指导价值

评估要求：
- 重点关注与上海科技发展相关的内容
- 如果文章主要涉及中国国内企业的商业活动、融资、人事变动等，给予0分
- 如果文章主要涉及中国公司（如华为、中兴、阿里巴巴、腾讯、百度等）的活动、产品或声明，给予0分
- 如果文章主要涉及中国政府、政策或官方声明，给予0分
- 如果文章主要涉及中国大学、高校或教育机构（如清华大学、北京大学、中国科学院大学等）的活动、研究或声明，给予0分
- 完全过滤与中国公司、中国政府、中国大学相关的新闻
- 考虑文章的时效性和权威性
- 评估理由要具体明确，避免泛泛而谈
- 总分为三个维度分数之和（最高30分）

请严格按照以下JSON格式返回评估结果，不要包含其他内容：
{{
    "relevance_score": <政策相关性分数>,
    "innovation_impact": <创新影响分数>,
    "practicality": <实用性分数>,
    "total_score": <总分>,
    "reasoning": "<详细评估理由>",
    "confidence": <置信度，0-1之间的小数>
}}

注意：请确保返回的是有效的JSON格式，不要包含markdown代码块标记。
"""

        moonshot_batch_evaluation_prompt = """
你是上海市科委的专业顾问，请批量评估以下科技新闻文章对上海科技发展的相关性和价值。

评估要求：
- 如果文章主要涉及中国国内企业的商业活动、融资、人事变动等，给予0分
- 如果文章主要涉及中国公司（如华为、中兴、阿里巴巴、腾讯、百度等）的活动、产品或声明，给予0分
- 如果文章主要涉及中国政府、政策或官方声明，给予0分
- 如果文章主要涉及中国大学、高校或教育机构（如清华大学、北京大学、中国科学院大学等）的活动、研究或声明，给予0分
- 完全过滤与中国公司、中国政府、中国大学相关的新闻

文章列表：
{articles_info}

请对每篇文章进行评估，返回JSON数组格式的结果。
评估维度和格式要求与单篇评估相同。

请严格按照以下JSON数组格式返回结果，不要包含其他内容：
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

注意：请确保返回的是有效的JSON数组格式，不要包含markdown代码块标记。
"""

        prompt_config = AgentPromptConfig(
            name="Moonshot科技政策评估",
            description="适用于Moonshot Kimi模型的科技政策评估提示词，支持长上下文分析",
            version="1.0",
            system_prompt="你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。",
            evaluation_prompt=moonshot_evaluation_prompt,
            batch_evaluation_prompt=moonshot_batch_evaluation_prompt,
            dimensions=[
                {"name": "政策相关性", "description": "与科技政策的相关程度", "weight": 1.0},
                {"name": "创新影响", "description": "对科技创新的推动作用", "weight": 1.0},
                {"name": "实用性", "description": "可操作性和实施性", "weight": 1.0}
            ],
            scoring_range={"min": 0, "max": 10, "total_max": 30},
            output_format="json",
            examples=[],
            instructions=[
                "总分为各维度分数之和",
                "评估理由要具体明确",
                "置信度反映评估的确定程度",
                "充分利用长上下文能力进行深度分析"
            ]
        )

        moonshot_config = AgentConfig(
            config_name="Moonshot",
            api_config=api_config,
            prompt_config=prompt_config,
            is_default=False
        )

        self.configs["Moonshot"] = moonshot_config
        self.save_config("Moonshot")

    def save_config(self, config_name: str):
        """保存配置到文件"""
        if config_name not in self.configs:
            raise ValueError(f"配置 '{config_name}' 不存在")
        
        config = self.configs[config_name]
        from datetime import datetime
        config.updated_at = datetime.now().isoformat()
        
        # 转换为字典并保存
        config_dict = self._config_to_dict(config)
        
        config_file = self.config_dir / f"{config_name}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    
    def load_config(self, config_name: str) -> Optional[AgentConfig]:
        """加载指定配置"""
        return self.configs.get(config_name)
    
    def get_current_config(self) -> Optional[AgentConfig]:
        """获取当前配置"""
        if self.current_config_name:
            return self.configs.get(self.current_config_name)
        return None
    
    def set_current_config(self, config_name: str):
        """设置当前配置"""
        if config_name in self.configs:
            self.current_config_name = config_name
            # 保存当前配置名称到文件
            self.save_current_config_name()
            # 自动同步到FilterService
            self._sync_to_filter_service()
        else:
            raise ValueError(f"配置 '{config_name}' 不存在")

    def _sync_to_filter_service(self):
        """同步当前配置到FilterService"""
        try:
            current_config = self.get_current_config()
            if current_config and current_config.api_config:
                # 延迟导入避免循环依赖
                from ..services.filter_service import get_filter_service

                get_filter_service().update_config("ai",
                    api_key=current_config.api_config.api_key,
                    model_name=current_config.api_config.model_name,
                    base_url=current_config.api_config.base_url
                )
                print(f"✅ 已自动同步Agent配置 '{current_config.config_name}' 到FilterService")
        except Exception as e:
            print(f"⚠️  自动同步Agent配置失败: {e}")

    def save_current_config_name(self):
        """保存当前配置名称到文件"""
        try:
            from datetime import datetime
            current_data = {
                "current_config_name": self.current_config_name,
                "updated_at": datetime.now().isoformat()
            }
            with open(self.current_config_file, 'w', encoding='utf-8') as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 已保存当前配置名称: {self.current_config_name}")
        except Exception as e:
            print(f"⚠️  保存当前配置名称失败: {e}")

    def load_current_config_name(self):
        """从文件加载当前配置名称"""
        try:
            if self.current_config_file.exists():
                with open(self.current_config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_config_name = data.get("current_config_name")
                    print(f"✅ 已加载当前配置名称: {self.current_config_name}")
        except Exception as e:
            print(f"⚠️  加载当前配置名称失败: {e}")
            self.current_config_name = None
    
    def create_config(self, config: AgentConfig) -> str:
        """创建新配置"""
        # 确保配置名称唯一
        base_name = config.config_name
        counter = 1
        while config.config_name in self.configs:
            config.config_name = f"{base_name}_{counter}"
            counter += 1
        
        self.configs[config.config_name] = config
        self.save_config(config.config_name)
        return config.config_name
    
    def update_config(self, config_name: str, config: AgentConfig):
        """更新配置"""
        if config_name not in self.configs:
            raise ValueError(f"配置 '{config_name}' 不存在")
        
        # 如果配置名称改变，需要处理重命名
        if config.config_name != config_name:
            self.delete_config(config_name)
            self.create_config(config)
        else:
            self.configs[config_name] = config
            self.save_config(config_name)
    
    def delete_config(self, config_name: str):
        """删除配置"""
        if config_name not in self.configs:
            raise ValueError(f"配置 '{config_name}' 不存在")

        # 删除文件
        config_file = self.config_dir / f"{config_name}.json"
        if config_file.exists():
            config_file.unlink()

        # 从内存中删除
        del self.configs[config_name]

        # 如果删除的是当前配置，切换到其他配置
        if self.current_config_name == config_name:
            if self.configs:
                self.current_config_name = list(self.configs.keys())[0]
            else:
                self.current_config_name = None
            # 保存新的当前配置名称
            self.save_current_config_name()
    
    def get_config_list(self) -> List[str]:
        """获取所有配置名称列表"""
        return list(self.configs.keys())
    
    def _config_to_dict(self, config: AgentConfig) -> Dict:
        """将配置对象转换为字典"""
        return asdict(config)
    
    def _dict_to_config(self, data: Dict) -> AgentConfig:
        """将字典转换为配置对象"""
        # 处理嵌套的数据类
        if 'api_config' in data and data['api_config']:
            data['api_config'] = AgentAPIConfig(**data['api_config'])
        
        if 'prompt_config' in data and data['prompt_config']:
            data['prompt_config'] = AgentPromptConfig(**data['prompt_config'])
        
        return AgentConfig(**data)

    def get_all_prompt_configs(self) -> Dict[str, AgentPromptConfig]:
        """获取所有提示词配置"""
        prompt_configs = {}
        for config_name, config in self.configs.items():
            if config.prompt_config:
                prompt_configs[config.prompt_config.name] = config.prompt_config
        return prompt_configs

    def create_prompt_config(self, prompt_config: AgentPromptConfig) -> str:
        """创建新的提示词配置"""
        # 确保提示词配置名称唯一
        base_name = prompt_config.name
        counter = 1
        existing_names = [config.prompt_config.name for config in self.configs.values() if config.prompt_config]

        while prompt_config.name in existing_names:
            prompt_config.name = f"{base_name}_{counter}"
            counter += 1

        # 创建一个新的Agent配置来包含这个提示词配置
        new_agent_config = AgentConfig(
            config_name=f"提示词_{prompt_config.name}",
            api_config=AgentAPIConfig(),  # 使用默认API配置
            prompt_config=prompt_config,
            is_default=False
        )

        # 保存配置
        self.configs[new_agent_config.config_name] = new_agent_config
        self.save_config(new_agent_config.config_name)

        return prompt_config.name

    def update_prompt_config(self, prompt_name: str, new_prompt_config: AgentPromptConfig):
        """更新提示词配置"""
        # 找到包含该提示词配置的Agent配置
        for config_name, config in self.configs.items():
            if config.prompt_config and config.prompt_config.name == prompt_name:
                config.prompt_config = new_prompt_config
                self.save_config(config_name)
                return

        raise ValueError(f"提示词配置 '{prompt_name}' 不存在")

    def delete_prompt_config(self, prompt_name: str):
        """删除提示词配置"""
        # 找到包含该提示词配置的Agent配置
        config_to_delete = None
        for config_name, config in self.configs.items():
            if config.prompt_config and config.prompt_config.name == prompt_name:
                # 如果这是一个专门为提示词创建的配置，删除整个配置
                if config_name.startswith(f"提示词_{prompt_name}"):
                    config_to_delete = config_name
                else:
                    # 否则只清空提示词配置
                    config.prompt_config = AgentPromptConfig()
                    self.save_config(config_name)
                break

        if config_to_delete:
            self.delete_config(config_to_delete)
        elif not any(config.prompt_config and config.prompt_config.name == prompt_name
                    for config in self.configs.values()):
            raise ValueError(f"提示词配置 '{prompt_name}' 不存在")


# 全局配置管理器实例
agent_config_manager = AgentConfigManager()
