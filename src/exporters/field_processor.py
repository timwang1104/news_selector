"""
文章字段处理器 - 将筛选结果转换为表格所需的字段格式
"""
import re
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from urllib.parse import urlparse
from ..models.news import NewsArticle
from ..filters.base import CombinedFilterResult, AIFilterResult

logger = logging.getLogger(__name__)


class ArticleFieldProcessor:
    """文章字段处理器"""
    
    def __init__(self, enable_translation: bool = True, enable_ai_enhancement: bool = False):
        """
        初始化字段处理器
        
        Args:
            enable_translation: 是否启用翻译功能
            enable_ai_enhancement: 是否启用AI增强功能
        """
        self.enable_translation = enable_translation
        self.enable_ai_enhancement = enable_ai_enhancement
        
        # 发布单位映射表
        self.publisher_mapping = {
            'arxiv.org': 'arXiv',
            'nature.com': 'Nature',
            'science.org': 'Science',
            'ieee.org': 'IEEE',
            'acm.org': 'ACM',
            'mit.edu': 'MIT',
            'stanford.edu': 'Stanford University',
            'gov.cn': '中国政府网',
            'xinhuanet.com': '新华网',
            'people.com.cn': '人民网'
        }
        
        # 报告类型关键词映射
        self.report_type_keywords = {
            '研究报告': ['research', 'study', 'analysis', 'investigation', '研究', '分析', '调研'],
            '政策文件': ['policy', 'regulation', 'guideline', 'framework', '政策', '规定', '指导'],
            '技术白皮书': ['whitepaper', 'technical', 'specification', '白皮书', '技术规范'],
            '新闻报道': ['news', 'report', 'announcement', '新闻', '报道', '公告'],
            '学术论文': ['paper', 'journal', 'conference', 'proceedings', '论文', '期刊'],
            '产业报告': ['industry', 'market', 'commercial', '产业', '市场', '商业']
        }
    
    def process_article(self, result: CombinedFilterResult) -> Dict[str, Any]:
        """
        处理单篇文章，提取所需字段
        
        Args:
            result: 筛选结果
            
        Returns:
            处理后的字段字典
        """
        article = result.article
        
        processed_fields = {
            'chinese_title': self._get_chinese_title(article.title),
            'english_title': self._get_english_title(article.title),
            'chinese_summary': self._get_chinese_summary(article.summary),
            'publisher': self._extract_publisher(article),
            'publish_time': self._format_publish_time(article.published),
            'content': self._clean_content(article.content),
            'report_type': self._determine_report_type(article, result),
            'url': article.url,
            
            # 额外的元数据
            'final_score': result.final_score,
            'tags': self._format_tags(result.tags) if result.tags else '',
            'relevance_score': result.keyword_result.relevance_score if result.keyword_result else 0
        }
        
        return processed_fields
    
    def _get_chinese_title(self, title: str) -> str:
        """获取中文标题"""
        if self._is_chinese(title):
            return title
        elif self.enable_translation:
            return self._translate_to_chinese(title)
        else:
            return f"[英文] {title}"
    
    def _get_english_title(self, title: str) -> str:
        """获取英文标题"""
        if self._is_english(title):
            return title
        elif self.enable_translation:
            return self._translate_to_english(title)
        else:
            return f"[Chinese] {title}"
    
    def _get_chinese_summary(self, summary: str) -> str:
        """获取中文摘要"""
        if not summary:
            return "无摘要"
        
        if self._is_chinese(summary):
            return summary
        elif self.enable_translation:
            return self._translate_to_chinese(summary)
        else:
            return f"[英文摘要] {summary[:200]}..."
    
    def _extract_publisher(self, article: NewsArticle) -> str:
        """提取发布单位"""
        # 优先使用feed_title
        if article.feed_title:
            return article.feed_title
        
        # 从URL域名推断
        if article.url:
            domain = urlparse(article.url).netloc.lower()
            for key, publisher in self.publisher_mapping.items():
                if key in domain:
                    return publisher
        
        # 从作者信息推断
        if article.author and hasattr(article.author, 'name'):
            return article.author.name
        
        # 从内容中提取（简单规则）
        publisher = self._extract_publisher_from_content(article.content)
        if publisher:
            return publisher
        
        return "未知来源"
    
    def _extract_publisher_from_content(self, content: str) -> Optional[str]:
        """从内容中提取发布单位"""
        if not content:
            return None
        
        # 查找常见的发布单位模式
        patterns = [
            r'发布[单位机构][:：]\s*([^\n\r]{2,50})',
            r'来源[:：]\s*([^\n\r]{2,50})',
            r'出版[社方][:：]\s*([^\n\r]{2,50})',
            r'Published by[:：]\s*([^\n\r]{2,50})',
            r'Source[:：]\s*([^\n\r]{2,50})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content[:1000])  # 只搜索前1000字符
            if match:
                publisher = match.group(1).strip()
                if len(publisher) > 2 and len(publisher) < 50:
                    return publisher
        
        return None
    
    def _determine_report_type(self, article: NewsArticle, result: CombinedFilterResult) -> str:
        """判断报告类型"""
        # 基于标签判断
        if result.tags:
            primary_tag = max(result.tags, key=lambda t: t.score)
            if 'policy' in primary_tag.name or 'regulation' in primary_tag.name:
                return '政策文件'
            elif 'research' in primary_tag.name or 'academic' in primary_tag.name:
                return '研究报告'
        
        # 基于URL判断
        if article.url:
            url_lower = article.url.lower()
            if 'arxiv.org' in url_lower or 'paper' in url_lower:
                return '学术论文'
            elif 'gov.' in url_lower or 'policy' in url_lower:
                return '政策文件'
            elif 'news' in url_lower or 'report' in url_lower:
                return '新闻报道'
        
        # 基于标题和内容关键词判断
        text_to_analyze = f"{article.title} {article.summary}".lower()
        
        for report_type, keywords in self.report_type_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_to_analyze:
                    return report_type
        
        # AI增强判断（如果启用）
        if self.enable_ai_enhancement and result.ai_result:
            ai_type = self._get_ai_suggested_type(result.ai_result)
            if ai_type:
                return ai_type
        
        return '其他'
    
    def _get_ai_suggested_type(self, ai_result: AIFilterResult) -> Optional[str]:
        """从AI结果中获取建议的报告类型"""
        # 如果AI结果中包含类型信息
        if hasattr(ai_result.evaluation, 'detailed_analysis'):
            analysis = ai_result.evaluation.detailed_analysis
            if 'document_type' in analysis:
                return analysis['document_type']
        
        # 基于AI标签推断
        if hasattr(ai_result.evaluation, 'tags') and ai_result.evaluation.tags:
            for tag in ai_result.evaluation.tags:
                if 'policy' in tag.lower():
                    return '政策文件'
                elif 'research' in tag.lower():
                    return '研究报告'
                elif 'technical' in tag.lower():
                    return '技术白皮书'
        
        return None
    
    def _format_publish_time(self, published: datetime) -> str:
        """格式化发布时间"""
        if not published:
            return "未知时间"
        
        return published.strftime("%Y-%m-%d %H:%M:%S")
    
    def _clean_content(self, content: str) -> str:
        """清理文章内容"""
        if not content:
            return "无内容"
        
        # 移除多余的空白字符
        content = re.sub(r'\s+', ' ', content)
        
        # 移除HTML标签（如果有）
        content = re.sub(r'<[^>]+>', '', content)
        
        # 限制长度（可配置）
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length] + "..."
        
        return content.strip()
    
    def _format_tags(self, tags) -> str:
        """格式化标签"""
        if not tags:
            return ""
        
        tag_names = [tag.name for tag in tags]
        return ", ".join(tag_names)
    
    def _is_chinese(self, text: str) -> bool:
        """判断文本是否主要是中文"""
        if not text:
            return False
        
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text.replace(' ', ''))
        
        return chinese_chars / max(total_chars, 1) > 0.3
    
    def _is_english(self, text: str) -> bool:
        """判断文本是否主要是英文"""
        if not text:
            return False
        
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        total_chars = len(text.replace(' ', ''))
        
        return english_chars / max(total_chars, 1) > 0.5
    
    def _translate_to_chinese(self, text: str) -> str:
        """翻译为中文（占位符，需要集成翻译服务）"""
        # TODO: 集成翻译API
        logger.info(f"需要翻译为中文: {text[:50]}...")
        return f"[待翻译] {text}"
    
    def _translate_to_english(self, text: str) -> str:
        """翻译为英文（占位符，需要集成翻译服务）"""
        # TODO: 集成翻译API
        logger.info(f"需要翻译为英文: {text[:50]}...")
        return f"[To be translated] {text}"


class TranslationService:
    """翻译服务接口"""
    
    def __init__(self, service_type: str = "baidu"):
        """
        初始化翻译服务
        
        Args:
            service_type: 翻译服务类型 (baidu, tencent, google)
        """
        self.service_type = service_type
        # TODO: 初始化具体的翻译服务
    
    def translate_to_chinese(self, text: str) -> str:
        """翻译为中文"""
        # TODO: 实现具体的翻译逻辑
        return text
    
    def translate_to_english(self, text: str) -> str:
        """翻译为英文"""
        # TODO: 实现具体的翻译逻辑
        return text
