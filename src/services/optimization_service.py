"""
优化建议服务 - 基于偏好分析报告生成配置优化建议
"""
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..config.agent_config import agent_config_manager
from ..config.keyword_config import KeywordConfigManager
from ..config.filter_config import FilterConfigManager
from ..ai.factory import create_ai_client
from ..config.filter_config import AIFilterConfig

logger = logging.getLogger(__name__)


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    category: str  # 优化类别：keyword, prompt, config
    priority: str  # 优先级：high, medium, low
    title: str     # 建议标题
    description: str  # 详细描述
    current_value: str  # 当前值
    suggested_value: str  # 建议值
    reasoning: str  # 建议理由
    impact: str    # 预期影响


@dataclass
class OptimizationResult:
    """优化结果"""
    suggestions: List[OptimizationSuggestion]
    summary: str
    confidence: float
    generated_at: str


class OptimizationService:
    """优化建议服务"""
    
    def __init__(self):
        self.keyword_manager = KeywordConfigManager()
        self.filter_manager = FilterConfigManager()
        self.agent_config = agent_config_manager.get_current_config()
        
    def generate_optimization_suggestions(self, report_data: Dict[str, Any]) -> OptimizationResult:
        """
        基于偏好分析报告生成优化建议
        
        Args:
            report_data: 偏好分析报告数据
            
        Returns:
            优化建议结果
        """
        try:
            # 1. 准备当前配置信息
            current_config = self._get_current_config()
            
            # 2. 构建分析提示词
            analysis_prompt = self._build_analysis_prompt(report_data, current_config)
            
            # 3. 调用AI分析
            ai_response = self._call_ai_for_analysis(analysis_prompt)
            
            # 4. 解析AI响应并生成建议
            suggestions = self._parse_ai_response(ai_response)
            
            # 5. 生成摘要
            summary = self._generate_summary(suggestions, report_data)
            
            from datetime import datetime
            result = OptimizationResult(
                suggestions=suggestions,
                summary=summary,
                confidence=0.85,  # 基于AI分析的置信度
                generated_at=datetime.now().isoformat()
            )
            
            logger.info(f"生成了 {len(suggestions)} 条优化建议")
            return result
            
        except Exception as e:
            logger.error(f"生成优化建议失败: {e}")
            # 返回基础建议作为降级方案
            return self._generate_fallback_suggestions(report_data)
    
    def _get_current_config(self) -> Dict[str, Any]:
        """获取当前配置信息"""
        config = {
            "keywords": {},
            "prompt": {},
            "filter_settings": {}
        }
        
        try:
            # 获取关键词配置
            keywords_data = self.keyword_manager.get_keywords()
            config["keywords"] = {
                "categories": list(keywords_data.keys()),
                "total_keywords": sum(len(words) for words in keywords_data.values()),
                "sample_keywords": {
                    category: words[:5] for category, words in keywords_data.items()
                }
            }
            
            # 获取提示词配置
            if self.agent_config and self.agent_config.prompt_config:
                config["prompt"] = {
                    "name": self.agent_config.prompt_config.name,
                    "evaluation_dimensions": [
                        dim.get("name", "") for dim in self.agent_config.prompt_config.dimensions or []
                    ],
                    "scoring_range": self.agent_config.prompt_config.scoring_range or {},
                    "system_prompt_length": len(self.agent_config.prompt_config.system_prompt or ""),
                    "evaluation_prompt_length": len(self.agent_config.prompt_config.evaluation_prompt or "")
                }
            
            # 获取筛选配置
            try:
                filter_configs = self.filter_manager.configs
                if filter_configs:
                    keyword_config = filter_configs.get("keyword")
                    ai_config = filter_configs.get("ai")
                    chain_config = filter_configs.get("chain")

                    config["filter_settings"] = {
                        "keyword_threshold": getattr(keyword_config, "threshold", 0.6),
                        "ai_max_requests": getattr(ai_config, "max_requests", 50),
                        "final_score_threshold": getattr(chain_config, "final_score_threshold", 0.7),
                        "max_final_results": getattr(chain_config, "max_final_results", 30)
                    }
            except Exception as e:
                logger.warning(f"获取筛选配置失败: {e}")
                config["filter_settings"] = {
                    "keyword_threshold": 0.6,
                    "ai_max_requests": 50,
                    "final_score_threshold": 0.7,
                    "max_final_results": 30
                }
            
        except Exception as e:
            logger.warning(f"获取配置信息时出错: {e}")
        
        return config
    
    def _build_analysis_prompt(self, report_data: Dict[str, Any], current_config: Dict[str, Any]) -> str:
        """构建分析提示词"""
        
        # 提取报告关键信息
        summary = report_data.get("summary", {})
        insights = report_data.get("insights", [])
        keyword_analysis = report_data.get("keyword_analysis", {})
        
        prompt = f"""
你是一位专业的新闻筛选系统优化专家，请基于以下偏好分析报告和当前配置，提供具体的优化建议。

## 偏好分析报告摘要
- 关键词总数: {summary.get('total_keywords', 0)}
- 话题总数: {summary.get('total_topics', 0)}
- 话题多样性评分: {summary.get('diversity_score', 0):.2f}
- 话题集中度指数: {summary.get('concentration_index', 0):.3f}

## 主要洞察
{chr(10).join(f"- {insight}" for insight in insights)}

## 高权重关键词分析
{self._format_keyword_analysis(keyword_analysis)}

## 当前配置状态
### 关键词配置
- 分类数量: {len(current_config.get('keywords', {}).get('categories', []))}
- 总关键词数: {current_config.get('keywords', {}).get('total_keywords', 0)}
- 主要分类: {', '.join(current_config.get('keywords', {}).get('categories', [])[:5])}

### 提示词配置
- 当前提示词: {current_config.get('prompt', {}).get('name', '未知')}
- 评估维度: {', '.join(current_config.get('prompt', {}).get('evaluation_dimensions', []))}
- 评分范围: {current_config.get('prompt', {}).get('scoring_range', {})}

### 筛选配置
- 关键词阈值: {current_config.get('filter_settings', {}).get('keyword_threshold', 0.6)}
- AI最大请求数: {current_config.get('filter_settings', {}).get('ai_max_requests', 50)}
- 最终评分阈值: {current_config.get('filter_settings', {}).get('final_score_threshold', 0.7)}

## 请提供优化建议

请分析以上信息，从以下三个方面提供具体的优化建议：

1. **关键词优化** - 基于高权重关键词分析，建议添加、删除或调整关键词
2. **提示词优化** - 基于话题分布和多样性，建议改进AI评估提示词
3. **配置参数优化** - 基于筛选效果，建议调整阈值和参数

请严格按照以下JSON格式返回建议，不要包含任何其他文本：

{{
    "suggestions": [
        {{
            "category": "keyword",
            "priority": "high",
            "title": "添加高权重关键词",
            "description": "基于分析结果，建议添加权重较高的关键词以提升筛选精度",
            "current_value": "当前关键词配置",
            "suggested_value": "建议添加的关键词列表",
            "reasoning": "基于关键词分析数据的具体理由",
            "impact": "预期提升筛选准确率10-15%"
        }},
        {{
            "category": "prompt",
            "priority": "medium",
            "title": "优化AI评估提示词",
            "description": "基于话题分布分析，建议调整AI评估的关注重点",
            "current_value": "当前提示词配置",
            "suggested_value": "建议的新提示词内容",
            "reasoning": "基于话题多样性和集中度的分析",
            "impact": "预期改善话题覆盖均衡性"
        }},
        {{
            "category": "config",
            "priority": "low",
            "title": "调整筛选阈值",
            "description": "基于当前筛选效果，建议微调相关参数",
            "current_value": "当前阈值设置",
            "suggested_value": "建议的新阈值",
            "reasoning": "基于筛选结果统计的分析",
            "impact": "预期优化筛选效率"
        }}
    ]
}}

要求：
1. 必须返回有效的JSON格式
2. 至少提供3条不同类别的建议
3. 每个建议都要具体可操作
4. 优先级要基于对筛选效果的影响程度
5. 建议理由要基于分析报告的具体数据
6. 预期影响要尽量量化描述
"""
        
        return prompt
    
    def _format_keyword_analysis(self, keyword_analysis: Dict[str, float]) -> str:
        """格式化关键词分析"""
        if not keyword_analysis:
            return "无关键词分析数据"
        
        sorted_keywords = sorted(keyword_analysis.items(), key=lambda x: x[1], reverse=True)
        top_10 = sorted_keywords[:10]
        
        lines = ["Top 10 关键词:"]
        for i, (keyword, weight) in enumerate(top_10, 1):
            lines.append(f"{i}. {keyword}: {weight:.3f}")
        
        return "\n".join(lines)
    
    def _call_ai_for_analysis(self, prompt: str) -> str:
        """调用AI进行分析"""
        try:
            if not self.agent_config or not self.agent_config.api_config:
                raise Exception("未找到有效的Agent配置")
            
            # 创建AI配置
            ai_config = AIFilterConfig(
                api_key=self.agent_config.api_config.api_key,
                base_url=self.agent_config.api_config.base_url,
                model_name=self.agent_config.api_config.model_name,
                temperature=0.3,
                max_tokens=3000,
                timeout=60
            )
            
            # 创建AI客户端
            client = create_ai_client(ai_config)

            # 调用AI - 使用通用的调用方法
            try:
                # 尝试使用evaluate_article方法的底层API调用
                if hasattr(client, 'call_api'):
                    response = client.call_api([
                        {"role": "system", "content": "你是一位专业的新闻筛选系统优化专家。"},
                        {"role": "user", "content": prompt}
                    ])
                elif hasattr(client, '_make_request'):
                    response = client._make_request([
                        {"role": "system", "content": "你是一位专业的新闻筛选系统优化专家。"},
                        {"role": "user", "content": prompt}
                    ])
                else:
                    # 降级方案：创建一个虚拟文章来调用evaluate_article
                    from ..models.news import NewsArticle
                    from datetime import datetime

                    dummy_article = NewsArticle(
                        id="optimization_request",
                        title="优化建议请求",
                        summary=prompt[:500],  # 将提示词作为摘要
                        content=prompt,
                        url="",
                        published=datetime.now(),
                        updated=datetime.now()
                    )

                    # 使用evaluate_article方法，但提取原始响应
                    evaluation = client.evaluate_article(dummy_article)
                    response = evaluation.reasoning if hasattr(evaluation, 'reasoning') else str(evaluation)
            except Exception as e:
                logger.warning(f"AI调用失败，使用降级方案: {e}")
                raise
            
            return response
            
        except Exception as e:
            logger.error(f"调用AI分析失败: {e}")
            raise
    
    def _parse_ai_response(self, response: str) -> List[OptimizationSuggestion]:
        """解析AI响应"""
        suggestions = []
        
        try:
            # 尝试解析JSON响应
            data = json.loads(response)
            suggestions_data = data.get("suggestions", [])
            
            for item in suggestions_data:
                suggestion = OptimizationSuggestion(
                    category=item.get("category", "config"),
                    priority=item.get("priority", "medium"),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    current_value=item.get("current_value", ""),
                    suggested_value=item.get("suggested_value", ""),
                    reasoning=item.get("reasoning", ""),
                    impact=item.get("impact", "")
                )
                suggestions.append(suggestion)
                
        except json.JSONDecodeError as e:
            logger.warning(f"解析AI响应JSON失败: {e}")
            # 尝试从文本中提取建议
            suggestions = self._extract_suggestions_from_text(response)
        
        return suggestions
    
    def _extract_suggestions_from_text(self, text: str) -> List[OptimizationSuggestion]:
        """从文本中提取建议（降级方案）"""
        suggestions = []
        
        # 简单的文本解析逻辑
        lines = text.split('\n')
        current_suggestion = {}
        
        for line in lines:
            line = line.strip()
            if '建议' in line or '优化' in line:
                if current_suggestion:
                    suggestions.append(self._create_suggestion_from_dict(current_suggestion))
                    current_suggestion = {}
                current_suggestion['title'] = line
            elif line:
                if 'description' not in current_suggestion:
                    current_suggestion['description'] = line
                else:
                    current_suggestion['description'] += ' ' + line
        
        if current_suggestion:
            suggestions.append(self._create_suggestion_from_dict(current_suggestion))
        
        return suggestions
    
    def _create_suggestion_from_dict(self, data: Dict[str, str]) -> OptimizationSuggestion:
        """从字典创建建议对象"""
        return OptimizationSuggestion(
            category="config",
            priority="medium",
            title=data.get('title', '优化建议'),
            description=data.get('description', ''),
            current_value="",
            suggested_value="",
            reasoning="基于分析报告生成",
            impact="改善筛选效果"
        )
    
    def _generate_summary(self, suggestions: List[OptimizationSuggestion], report_data: Dict[str, Any]) -> str:
        """生成优化建议摘要"""
        if not suggestions:
            return "未生成具体优化建议，建议检查配置和数据。"
        
        high_priority = len([s for s in suggestions if s.priority == "high"])
        medium_priority = len([s for s in suggestions if s.priority == "medium"])
        low_priority = len([s for s in suggestions if s.priority == "low"])
        
        keyword_suggestions = len([s for s in suggestions if s.category == "keyword"])
        prompt_suggestions = len([s for s in suggestions if s.category == "prompt"])
        config_suggestions = len([s for s in suggestions if s.category == "config"])
        
        summary = f"""
基于偏好分析报告，共生成 {len(suggestions)} 条优化建议：

优先级分布：
- 高优先级：{high_priority} 条
- 中优先级：{medium_priority} 条  
- 低优先级：{low_priority} 条

类别分布：
- 关键词优化：{keyword_suggestions} 条
- 提示词优化：{prompt_suggestions} 条
- 配置参数优化：{config_suggestions} 条

建议重点关注高优先级建议，这些将对筛选效果产生最直接的改善。
"""
        
        return summary.strip()
    
    def _generate_fallback_suggestions(self, report_data: Dict[str, Any]) -> OptimizationResult:
        """生成降级建议（当AI分析失败时）"""
        suggestions = []
        summary = report_data.get("summary", {})
        
        # 基于数据特征生成基础建议
        if summary.get("diversity_score", 0) < 0.5:
            suggestions.append(OptimizationSuggestion(
                category="keyword",
                priority="high",
                title="扩展关键词覆盖面",
                description="当前话题多样性较低，建议增加更多领域的关键词",
                current_value=f"多样性评分: {summary.get('diversity_score', 0):.2f}",
                suggested_value="增加新兴技术领域关键词",
                reasoning="提高内容覆盖的多样性",
                impact="预期提升话题覆盖面20-30%"
            ))
        
        if summary.get("concentration_index", 0) > 0.7:
            suggestions.append(OptimizationSuggestion(
                category="config",
                priority="medium",
                title="调整筛选阈值",
                description="话题集中度较高，建议降低筛选阈值以获得更多样化的内容",
                current_value=f"集中度指数: {summary.get('concentration_index', 0):.3f}",
                suggested_value="降低关键词阈值0.1-0.15",
                reasoning="平衡各话题的关注度",
                impact="预期增加内容多样性15-25%"
            ))
        
        from datetime import datetime
        return OptimizationResult(
            suggestions=suggestions,
            summary="基于数据特征生成的基础优化建议",
            confidence=0.6,
            generated_at=datetime.now().isoformat()
        )
