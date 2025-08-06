#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专门爬取科创板日报"每日全球科技要闻"的脚本
"""

import requests
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import logging
from typing import List, Dict, Any
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TechNewsCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session.headers.update(self.headers)
        self.driver = None
    
    def init_driver(self):
        """初始化Selenium WebDriver"""
        if self.driver is None:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            # 禁用代理设置
            chrome_options.add_argument('--no-proxy-server')
            chrome_options.add_argument('--disable-proxy')
            chrome_options.add_argument('--proxy-server="direct://"')
            chrome_options.add_argument('--proxy-bypass-list=*')
            # 其他网络相关设置
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
            try:
                self.driver = webdriver.Chrome(options=chrome_options)
                logger.info("Selenium WebDriver 初始化成功")
            except Exception as e:
                logger.error(f"Selenium WebDriver 初始化失败: {e}")
                self.driver = None
    
    def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        
    def get_article_detail(self, url: str) -> Dict[str, Any]:
        """获取文章详细内容"""
        try:
            logger.info(f"获取文章详情: {url}")
            
            # 使用Selenium获取动态渲染的页面
            if not self.driver:
                # 如果driver不存在，临时创建一个
                temp_driver = True
                self.init_driver()
            else:
                temp_driver = False
            
            if not self.driver:
                logger.error(f"无法初始化WebDriver，跳过文章: {url}")
                return None
            
            self.driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待额外时间让JavaScript执行
            time.sleep(2)
            
            # 获取页面源码
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 如果是临时创建的driver，使用完后关闭
            if temp_driver:
                self.close_driver()
            
            # 提取文章信息
            articles = []
            
            # 查找所有可能是标题的加粗标签
            # 这边需要根据实际情况调整选择器，strong, b, 或者特定的class
            title_elements = soup.select('p > strong, p > b')

            if not title_elements:
                # 如果页面上没有加粗的标题，就尝试把整个页面当作一篇文章
                # 这种是兼容之前的逻辑
                # return [super(TechNewsCrawler, self).get_article_detail(url)]
                logger.warning(f"在页面 {url} 中未找到加粗标题，将尝试提取全文。")
                content_elem = soup.find('body')
                if content_elem:
                    for script in content_elem(["script", "style", "nav", "header", "footer"]):
                        script.decompose()
                    full_content = content_elem.get_text(strip=True)
                    title = soup.title.string if soup.title else url
                    articles.append({
                        'url': url,
                        'title': title,
                        'content': full_content,
                        'published_time': '',
                        'author': '',
                        'tags': [],
                        'category': '',
                        'crawl_time': datetime.now().isoformat()
                    })
                return articles

            for i, title_elem in enumerate(title_elements):
                title_text = title_elem.get_text(strip=True)
                if not title_text:
                    continue

                # 提取真实标题和内容
                real_title = title_text
                content_parts = []
                # 从当前标题找到下一个标题之前的所有兄弟节点
                current_node = title_elem.parent
                while True:
                    current_node = current_node.find_next_sibling()
                    if not current_node or (current_node.find and (current_node.find('strong') or current_node.find('b'))):
                        break
                    content_parts.append(current_node.get_text(strip=True))
                
                content = "\n".join(filter(None, content_parts)).strip()

                article = {
                    'url': url,
                    'title': real_title,
                    'content': content,
                    'published_time': '', # 这些字段暂时留空
                    'author': '',
                    'tags': [],
                    'category': '',
                    'crawl_time': datetime.now().isoformat()
                }
                articles.append(article)

            return articles
            
        except Exception as e:
            logger.error(f"获取文章详情失败 {url}: {e}")
            return None
    
    def crawl_search_articles(self, load_all: bool = True) -> List[Dict[str, Any]]:
        """爬取搜索页面的文章"""
        articles = []
        keyword = "每日全球科技要闻"
        
        # 初始化Selenium
        self.init_driver()
        if not self.driver:
            logger.error("无法初始化WebDriver，跳过搜索页面爬取")
            return articles
        
        try:
            # 访问搜索页面
            search_url = f"https://www.chinastarmarket.cn/search?type=depth&keyword={quote(keyword)}"
            logger.info(f"正在访问搜索页面: {search_url}")
            
            self.driver.get(search_url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 等待额外时间让JavaScript执行
            time.sleep(3)
            
            # 如果需要加载所有文章，点击"加载更多"按钮
            if load_all:
                self._load_more_articles()
            
            # 获取页面源码
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # 调试：保存页面内容
            with open('debug_search_page_full.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            logger.info("已保存完整页面HTML内容到debug_search_page_full.html")
            
            # 查找文章链接
            article_links = self._extract_article_links(soup)
            logger.info(f"总共找到{len(article_links)}个文章链接")
            
            # 爬取每篇文章的详细内容
            for i, article_url in enumerate(article_links, 1):
                logger.info(f"正在处理第{i}/{len(article_links)}篇文章: {article_url}")
                
                article = self.get_article_detail(article_url)
                if article and article['content']:
                    # 过滤标题：只保留包含"每日全球科技要闻"的文章
                    if "每日全球科技要闻" in article['title']:
                        article['source'] = 'tech_news_search'
                        articles.append(article)
                        logger.info(f"✓ 成功获取文章: {article['title'][:50]}...")
                    else:
                        logger.info(f"✗ 跳过文章（标题不匹配）: {article['title'][:50]}...")
                else:
                    logger.warning(f"✗ 无法获取文章内容: {article_url}")
                
                # 添加延迟避免请求过快
                time.sleep(1)
            
        except Exception as e:
            logger.error(f"爬取过程中出错: {e}")
        
        finally:
            # 关闭WebDriver
            self.close_driver()
        
        return articles
    
    def _load_more_articles(self):
        """通过点击“加载更多”按钮加载所有文章"""
        logger.info("开始通过点击'加载更多'按钮加载文章...")
        click_count = 0
        max_clicks = 30  # 设置一个最大点击次数，防止无限循环

        while click_count < max_clicks:
            try:
                # 使用CSS选择器定位“加载更多”按钮，并等待其可点击
                load_more_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, ".list-more-button"))
                )
                # 使用JavaScript点击以避免被其他元素遮挡
                self.driver.execute_script("arguments[0].click();", load_more_button)
                click_count += 1
                logger.info(f"成功点击'加载更多'按钮，第 {click_count} 次")
                time.sleep(3)  # 等待新内容加载
            except TimeoutException:
                logger.info("未找到'加载更多'按钮，或按钮已不可见，停止加载。")
                break
            except Exception as e:
                logger.warning(f"点击'加载更多'按钮时出错: {e}")
                break
        
        # 最终统计
        final_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        final_article_count = len(self._extract_article_links(final_soup))
        logger.info(f"加载更多操作完成，共点击 {click_count} 次，最终文章数: {final_article_count}")
    
    def _extract_article_links(self, soup) -> set:
        """从页面中提取文章链接"""
        article_links = set()
        
        # 策略1: 查找search-content list-link类的链接
        search_links = soup.find_all('a', class_='search-content list-link')
        for link in search_links:
            href = link.get('href')
            if href and '/detail/' in href:
                if not href.startswith('http'):
                    href = urljoin('https://www.chinastarmarket.cn', href)
                article_links.add(href)
        
        # 策略2: 查找所有包含/detail/的链接
        detail_links = soup.find_all('a', href=lambda x: x and '/detail/' in x)
        for link in detail_links:
            href = link.get('href')
            if href:
                if not href.startswith('http'):
                    href = urljoin('https://www.chinastarmarket.cn', href)
                article_links.add(href)
        
        # 策略3: 查找list-right-item-box容器中的链接
        containers = soup.find_all('div', class_=lambda x: x and 'list-right-item-box' in str(x))
        for container in containers:
            links = container.find_all('a', href=lambda x: x and '/detail/' in x)
            for link in links:
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = urljoin('https://www.chinastarmarket.cn', href)
                    article_links.add(href)
        
        return article_links
    
    def save_articles(self, articles: List[Dict[str, Any]], filename: str = 'tech_news_articles.json'):
        """保存文章到JSON文件"""
        data = {
            'crawl_time': datetime.now().isoformat(),
            'total_articles': len(articles),
            'source': 'chinastarmarket.cn - 每日全球科技要闻',
            'articles': articles
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"文章已保存到: {filename}")
        logger.info(f"总共保存 {len(articles)} 篇文章")
        
        # 显示统计信息
        if articles:
            logger.info("最新5篇文章:")
            for i, article in enumerate(articles[:5], 1):
                logger.info(f"  {i}. {article['title'][:100]}...")

def main():
    """主函数"""
    crawler = TechNewsCrawler()
    
    logger.info("开始从 links.txt 文件中读取链接并爬取文章")

    try:
        with open('scripts/links.txt', 'r', encoding='utf-8') as f:
            article_urls = [line.strip() for line in f if line.strip()]
        logger.info(f"从 links.txt 文件中加载了 {len(article_urls)} 个链接")
    except FileNotFoundError:
        logger.error("links.txt 文件未找到，请确保 scripts/links.txt 文件存在")
        return

    # 初始化Selenium Driver，供所有文章爬取使用，以提高效率
    crawler.init_driver()
    if not crawler.driver:
        logger.error("无法初始化WebDriver，程序退出")
        return

    all_crawled_articles = []
    try:
        for i, url in enumerate(article_urls, 1):
            logger.info(f"正在处理第 {i}/{len(article_urls)} 篇文章: {url}")
            articles_from_page = crawler.get_article_detail(url)
            if articles_from_page:
                all_crawled_articles.extend(articles_from_page)
                logger.info(f"✓ 从 {url} 成功获取 {len(articles_from_page)} 篇文章")
            else:
                logger.warning(f"✗ 无法从 {url} 获取文章内容或数据")
            
            # 添加随机延迟
            time.sleep(random.uniform(1, 3))
    finally:
        # 确保WebDriver在所有操作完成后被关闭
        crawler.close_driver()

    if all_crawled_articles:
        # 保存文章
        output_filename = 'data/crawled_news.json'
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_crawled_articles, f, ensure_ascii=False, indent=2)
        
        logger.info("\n=== 爬取完成 ===")
        logger.info(f"总共获取: {len(all_crawled_articles)} 篇文章")
        logger.info(f"结果已保存到 {output_filename}")
    else:
        logger.warning("没有获取到任何符合条件的文章")

if __name__ == "__main__":
    main()