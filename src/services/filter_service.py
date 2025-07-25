"""
筛选服务 - 提供新闻筛选的高级接口
"""
import logging
from typing import List, Optional, Dict, Any
from ..models.news import NewsArticle
from ..config.filter_config import filter_config_manager
from ..filters.keyword_filter import KeywordFilter
from ..filters.ai_filter import AIFilter
from ..filters.filter_chain import FilterChain, FilterProgressCallback
from ..filters.base import FilterChainResult, CombinedFilterResult

logger = logging.getLogger(__name__)


class FilterService:
    """筛选服务"""
    
    def __init__(self):
        self.config_manager = filter_config_manager
        self._keyword_filter = None
        self._ai_filter = None
        self._filter_chain = None
    
    @property
    def keyword_filter(self) -> KeywordFilter:
        """获取关键词筛选器"""
        if self._keyword_filter is None:
            config = self.config_manager.get_keyword_config()
            self._keyword_filter = KeywordFilter(config)
        return self._keyword_filter
    
    @property
    def ai_filter(self) -> AIFilter:
        """获取AI筛选器"""
        if self._ai_filter is None:
            try:
                config = self.config_manager.get_ai_config()
                print(f"🔧 初始化AI筛选器: model={config.model_name}, api_key={'***' if config.api_key else 'None'}")
                self._ai_filter = AIFilter(config)
                print(f"✅ AI筛选器初始化成功")
            except Exception as e:
                print(f"❌ AI筛选器初始化失败: {e}")
                # 创建一个空的AI筛选器以避免崩溃
                from ..config.filter_config import AIFilterConfig
                fallback_config = AIFilterConfig()
                self._ai_filter = AIFilter(fallback_config)
        return self._ai_filter

    def reset_ai_filter(self):
        """重置AI筛选器缓存"""
        print(f"🔄 重置AI筛选器缓存")
        self._ai_filter = None
        self._filter_chain = None
    
    @property
    def filter_chain(self) -> FilterChain:
        """获取筛选链"""
        if self._filter_chain is None:
            config = self.config_manager.get_chain_config()
            self._filter_chain = FilterChain(
                self.keyword_filter,
                self.ai_filter,
                config
            )
        return self._filter_chain
    
    def filter_articles(self, articles: List[NewsArticle], 
                       filter_type: str = "chain",
                       callback: Optional[FilterProgressCallback] = None) -> FilterChainResult:
        """
        筛选文章
        
        Args:
            articles: 待筛选的文章列表
            filter_type: 筛选类型 ("keyword", "ai", "chain")
            callback: 进度回调函数
        
        Returns:
            筛选结果
        """
        if not articles:
            logger.warning("No articles to filter")
            return FilterChainResult(total_articles=0, processing_start_time=None)
        
        logger.info(f"Starting {filter_type} filtering for {len(articles)} articles")
        print(f"🎯 FilterService.filter_articles: filter_type='{filter_type}', articles={len(articles)}")

        try:
            if filter_type == "keyword":
                print(f"📝 执行关键词筛选")
                return self._keyword_only_filter(articles, callback)
            elif filter_type == "ai":
                print(f"🤖 执行AI筛选")
                return self._ai_only_filter(articles, callback)
            elif filter_type == "chain":
                print(f"🔗 执行综合筛选 (关键词+AI)")
                if callback:
                    return self.filter_chain.process_with_callback(articles, callback)
                else:
                    return self.filter_chain.process(articles)
            else:
                raise ValueError(f"Unknown filter type: {filter_type}")
                
        except Exception as e:
            logger.error(f"Filtering failed: {e}")
            raise
    
    def _keyword_only_filter(self, articles: List[NewsArticle],
                           callback: Optional[FilterProgressCallback] = None) -> FilterChainResult:
        """仅关键词筛选"""
        from datetime import datetime

        start_time = datetime.now()
        result = FilterChainResult(
            total_articles=len(articles),
            processing_start_time=start_time
        )

        # 通知开始筛选
        if callback:
            callback.on_start(len(articles))

        try:
            # 使用批处理方式进行关键词筛选以支持进度回调
            keyword_results = []
            batch_size = 10  # 每批处理10篇文章

            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                batch_results = []

                for article in batch:
                    single_result = self.keyword_filter.filter_single(article)
                    if single_result and single_result.relevance_score >= self.keyword_filter.config.threshold:
                        batch_results.append(single_result)

                keyword_results.extend(batch_results)

                # 更新进度
                if callback:
                    processed = min(i + batch_size, len(articles))
                    callback.on_keyword_progress(processed, len(articles))

            # 通知关键词筛选完成
            if callback:
                callback.on_keyword_complete(len(keyword_results))

            # 转换为综合结果格式
            combined_results = []
            for kr in keyword_results:
                combined_result = CombinedFilterResult(
                    article=kr.article,
                    keyword_result=kr,
                    ai_result=None,
                    final_score=kr.relevance_score,
                    selected=True,
                    rejection_reason=None
                )
                combined_results.append(combined_result)

            result.selected_articles = combined_results
            result.keyword_filtered_count = len(keyword_results)
            result.final_selected_count = len(combined_results)

            # 通知筛选完成
            if callback:
                callback.on_complete(len(combined_results))
            
        except Exception as e:
            result.errors.append(f"关键词筛选失败: {str(e)}")
        
        finally:
            result.processing_end_time = datetime.now()
            result.total_processing_time = (
                result.processing_end_time - start_time
            ).total_seconds()
        
        return result
    
    def _ai_only_filter(self, articles: List[NewsArticle],
                      callback: Optional[FilterProgressCallback] = None) -> FilterChainResult:
        """仅AI筛选"""
        from datetime import datetime

        start_time = datetime.now()
        result = FilterChainResult(
            total_articles=len(articles),
            processing_start_time=start_time
        )

        # 通知开始筛选
        if callback:
            callback.on_start(len(articles))

        try:
            # 通知AI筛选开始
            if callback and hasattr(callback, 'on_ai_start'):
                callback.on_ai_start(len(articles))

            # 使用批处理方式进行AI筛选以支持进度回调
            all_results = []
            batch_size = 5  # AI筛选每批处理5篇文章（较慢）
            total_batches = (len(articles) + batch_size - 1) // batch_size

            for batch_num, i in enumerate(range(0, len(articles), batch_size), 1):
                batch = articles[i:i + batch_size]

                # 通知批处理开始
                if callback and hasattr(callback, 'on_ai_batch_start'):
                    callback.on_ai_batch_start(len(batch), batch_num, total_batches)

                batch_results = []
                batch_scores = []

                for j, article in enumerate(batch):
                    article_index = i + j + 1

                    # 通知开始评估单篇文章
                    if callback and hasattr(callback, 'on_ai_article_start'):
                        callback.on_ai_article_start(article.title, article_index, len(articles))

                    try:
                        single_result = self.ai_filter.filter_single(article)
                        if single_result:
                            batch_results.append(single_result)
                            batch_scores.append(single_result.evaluation.total_score)

                            # 通知文章评估完成
                            if callback and hasattr(callback, 'on_ai_article_complete'):
                                callback.on_ai_article_complete(
                                    article.title,
                                    single_result.evaluation.total_score,
                                    single_result.processing_time
                                )
                        else:
                            # 评估失败
                            if callback and hasattr(callback, 'on_ai_error'):
                                callback.on_ai_error(article.title, "评估返回空结果")

                    except Exception as e:
                        # 评估异常
                        if callback and hasattr(callback, 'on_ai_error'):
                            callback.on_ai_error(article.title, str(e))

                all_results.extend(batch_results)

                # 通知批处理完成
                if callback and hasattr(callback, 'on_ai_batch_complete'):
                    avg_score = sum(batch_scores) / len(batch_scores) if batch_scores else 0
                    callback.on_ai_batch_complete(len(batch), batch_num, total_batches, avg_score)

                # 更新进度
                if callback:
                    processed = min(i + batch_size, len(articles))
                    callback.on_ai_progress(processed, len(articles))

            # 通知开始排序
            if callback and hasattr(callback, 'on_ai_ranking_start'):
                callback.on_ai_ranking_start(len(all_results))

            # 按评分排序并取前N条
            all_results.sort(key=lambda x: x.evaluation.total_score, reverse=True)
            max_selected = getattr(self.ai_filter.config, 'max_selected', 3)
            ai_results = all_results[:max_selected]

            # 通知排序完成
            if callback and hasattr(callback, 'on_ai_ranking_complete'):
                callback.on_ai_ranking_complete(len(ai_results), len(all_results))

            # 通知所有AI评估结果（用于更新界面显示）
            if callback and hasattr(callback, 'on_all_ai_results'):
                callback.on_all_ai_results(all_results)

            # 通知AI筛选完成
            if callback:
                callback.on_ai_complete(len(ai_results))

            # 转换为综合结果格式
            combined_results = []
            for ar in ai_results:
                combined_result = CombinedFilterResult(
                    article=ar.article,
                    keyword_result=None,
                    ai_result=ar,
                    final_score=ar.evaluation.total_score / 30.0,  # 归一化
                    selected=True,
                    rejection_reason=None
                )
                combined_results.append(combined_result)

            result.selected_articles = combined_results
            result.ai_filtered_count = len(ai_results)
            result.final_selected_count = len(combined_results)

            # 通知筛选完成
            if callback:
                callback.on_complete(len(combined_results))
            
        except Exception as e:
            result.errors.append(f"AI筛选失败: {str(e)}")
        
        finally:
            result.processing_end_time = datetime.now()
            result.total_processing_time = (
                result.processing_end_time - start_time
            ).total_seconds()
        
        return result
    
    def update_config(self, config_type: str, **kwargs):
        """更新筛选配置"""
        self.config_manager.update_config(config_type, **kwargs)
        
        # 重置筛选器以应用新配置
        if config_type == "keyword":
            self._keyword_filter = None
        elif config_type == "ai":
            self._ai_filter = None
        elif config_type == "chain":
            self._filter_chain = None
    
    def get_config(self, config_type: str) -> Dict[str, Any]:
        """获取筛选配置"""
        if config_type == "keyword":
            return self.config_manager.get_keyword_config().__dict__
        elif config_type == "ai":
            return self.config_manager.get_ai_config().__dict__
        elif config_type == "chain":
            return self.config_manager.get_chain_config().__dict__
        else:
            raise ValueError(f"Unknown config type: {config_type}")

    def reload_config(self):
        """重新加载配置"""
        self.config_manager.reload_configs()
        # 重置筛选器以应用新配置
        self._keyword_filter = None
        self._ai_filter = None
        self._filter_chain = None
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取筛选性能指标"""
        return self.filter_chain.get_metrics()
    
    def reset_metrics(self):
        """重置性能指标"""
        self.filter_chain.reset_metrics()
    
    def clear_cache(self):
        """清空AI筛选缓存"""
        if self._ai_filter:
            self._ai_filter.clear_cache()
    
    def cleanup_cache(self):
        """清理过期缓存"""
        if self._ai_filter:
            self._ai_filter.cleanup_cache()


class CLIProgressCallback(FilterProgressCallback):
    """命令行进度回调"""
    
    def __init__(self, show_progress: bool = True):
        self.show_progress = show_progress
        self.total_articles = 0
    
    def on_start(self, total_articles: int):
        """筛选开始"""
        self.total_articles = total_articles
        if self.show_progress:
            print(f"🔍 开始筛选 {total_articles} 篇文章...")
    
    def on_keyword_progress(self, processed: int, total: int):
        """关键词筛选进度"""
        if self.show_progress:
            percentage = (processed / total) * 100
            print(f"📝 关键词筛选进度: {processed}/{total} ({percentage:.1f}%)")
    
    def on_keyword_complete(self, results_count: int):
        """关键词筛选完成"""
        if self.show_progress:
            print(f"✅ 关键词筛选完成: {results_count} 篇文章通过")
    
    def on_ai_start(self, total_articles: int):
        """AI筛选开始"""
        if self.show_progress:
            print(f"🤖 开始AI智能评估 {total_articles} 篇文章...")

    def on_ai_article_start(self, article_title: str, current: int, total: int):
        """开始评估单篇文章"""
        if self.show_progress:
            display_title = article_title[:50] + "..." if len(article_title) > 50 else article_title
            print(f"🔍 [{current}/{total}] 评估: {display_title}")

    def on_ai_article_complete(self, article_title: str, evaluation_score: float, processing_time: float):
        """单篇文章评估完成"""
        if self.show_progress:
            display_title = article_title[:40] + "..." if len(article_title) > 40 else article_title
            score_emoji = "🟢" if evaluation_score >= 20 else "🟡" if evaluation_score >= 15 else "🔴"
            print(f"✅ {display_title} - 评分: {evaluation_score:.1f}/30 {score_emoji}")

    def on_ai_batch_start(self, batch_size: int, batch_number: int, total_batches: int):
        """AI批处理开始"""
        if self.show_progress:
            print(f"📦 处理第 {batch_number}/{total_batches} 批 ({batch_size} 篇)")

    def on_ai_batch_complete(self, batch_size: int, batch_number: int, total_batches: int, avg_score: float):
        """AI批处理完成"""
        if self.show_progress:
            print(f"✅ 第 {batch_number}/{total_batches} 批完成，平均评分: {avg_score:.1f}/30")

    def on_ai_progress(self, processed: int, total: int):
        """AI筛选进度"""
        if self.show_progress:
            percentage = (processed / total) * 100
            print(f"🤖 AI筛选进度: {processed}/{total} ({percentage:.1f}%)")

    def on_ai_ranking_start(self, total_results: int):
        """AI结果排序开始"""
        if self.show_progress:
            print(f"📊 正在对 {total_results} 个评估结果进行排序...")

    def on_ai_ranking_complete(self, selected_count: int, total_count: int):
        """AI结果排序完成"""
        if self.show_progress:
            print(f"🏆 排序完成，从 {total_count} 个结果中选出前 {selected_count} 篇")

    def on_ai_complete(self, results_count: int):
        """AI筛选完成"""
        if self.show_progress:
            print(f"✅ AI筛选完成: {results_count} 篇文章通过")

    def on_ai_error(self, article_title: str, error: str):
        """AI评估错误"""
        if self.show_progress:
            display_title = article_title[:40] + "..." if len(article_title) > 40 else article_title
            print(f"❌ {display_title} - 评估失败: {error}")

    def on_ai_fallback(self, article_title: str, reason: str):
        """AI降级处理"""
        if self.show_progress:
            display_title = article_title[:40] + "..." if len(article_title) > 40 else article_title
            print(f"⚠️ {display_title} - 使用降级评估: {reason}")

    def on_complete(self, final_count: int):
        """筛选完成"""
        if self.show_progress:
            print(f"🎉 筛选完成: 最终选出 {final_count} 篇文章")

    def on_error(self, error: str):
        """筛选错误"""
        print(f"❌ 筛选错误: {error}")


# 全局筛选服务实例
filter_service = FilterService()
