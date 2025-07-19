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
    provider: str = "openai"  # openai, siliconflow, anthropic, custom
    
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
        self.configs: Dict[str, AgentConfig] = {}
        self.current_config_name: Optional[str] = None
        self.load_all_configs()
    
    def load_all_configs(self):
        """加载所有配置"""
        # 加载保存的配置
        for config_file in self.config_dir.glob("*.json"):
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
        
        # 设置当前配置
        if not self.current_config_name:
            # 优先使用标记为默认的配置
            default_configs = [name for name, config in self.configs.items() if config.is_default]
            if default_configs:
                self.current_config_name = default_configs[0]
            else:
                # 否则使用第一个配置
                self.current_config_name = list(self.configs.keys())[0]
    
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
        else:
            raise ValueError(f"配置 '{config_name}' 不存在")
    
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


# 全局配置管理器实例
agent_config_manager = AgentConfigManager()
