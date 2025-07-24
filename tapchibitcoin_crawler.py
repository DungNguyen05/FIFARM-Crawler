import asyncio
import json
import re
import os
import logging
from datetime import datetime, timezone
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from urllib.parse import urlparse, urljoin
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TapchiBitcoinCrawler:
    def __init__(self):
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=50)
        self.home_url = os.getenv("TAPCHIBITCOIN_HOME_URL", "https://tapchibitcoin.io/")
        self.api_endpoint = os.getenv("TAPCHIBITCOIN_API_ENDPOINT", os.getenv("API_ENDPOINT", "http://localhost:8080/admin/news-articles"))
        self.max_articles = int(os.getenv("TAPCHIBITCOIN_MAX_ARTICLES", os.getenv("MAX_ARTICLES", "5")))
        self.is_running = False
        
        logger.info(f"TapchiBitcoin Crawler initialized - URL: {self.home_url}")
        logger.info(f"TapchiBitcoin API: {self.api_endpoint}")
        
    async def get_article_links(self):
        """Get all article links from homepage - specifically from lasted_post section"""
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=self.home_url, config=self.run_config)
                
                if not result.success:
                    logger.error("TapchiBitcoin: Failed to crawl homepage")
                    return []
                
                # Parse the HTML content
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Find the lasted_post section
                lasted_post_section = soup.find('div', class_='lasted_post')
                if not lasted_post_section:
                    logger.warning("TapchiBitcoin: Could not find lasted_post section")
                    return []
                
                # Find the list_post div within lasted_post
                list_post = lasted_post_section.find('div', class_='list_post')
                if not list_post:
                    logger.warning("TapchiBitcoin: Could not find list_post section")
                    return []
                
                # Find all item divs within list_post
                items = list_post.find_all('div', class_='item')
                
                article_links = []
                for item in items:
                    # Find all <a> tags with href attributes in each item
                    links = item.find_all('a', href=True)
                    
                    for link in links:
                        href = link['href']
                        # Skip if href is empty or just a fragment
                        if not href or href.startswith('#'):
                            continue
                            
                        # Ensure absolute URL
                        absolute_url = urljoin(self.home_url, href)
                        
                        # Validate if it's an article link
                        if self.is_article_link(absolute_url):
                            article_links.append(absolute_url)
                
                # Remove duplicates while preserving order
                unique_links = list(dict.fromkeys(article_links))
                
                logger.info(f"TapchiBitcoin: Found {len(unique_links)} article links from lasted_post section")
                
                # Log first few links for debugging
                for i, link in enumerate(unique_links[:5]):
                    logger.debug(f"TapchiBitcoin: Article {i+1}: {link}")
                
                return unique_links
                
        except Exception as e:
            logger.error(f"TapchiBitcoin: Error getting article links: {e}")
            return []
    
    def is_article_link(self, url):
        """Check if URL is an article link for TapchiBitcoin"""
        if not url or not isinstance(url, str):
            return False
            
        # Must be from tapchibitcoin.io domain
        parsed = urlparse(url)
        if not parsed.netloc.endswith('tapchibitcoin.io'):
            return False
            
        # TapchiBitcoin specific exclude patterns
        exclude_paths = [
            '/category', '/tag', '/author', '/page', '/search',
            '/contact', '/about', '/privacy', '/terms', '/sitemap',
            '/wp-admin', '/wp-content', '/wp-includes', '/feed',
            '/comments', '/trackback', '/#', '/login', '/register',
            '/wp-json', '/xmlrpc', '.xml', '.rss'
        ]
        
        path = parsed.path.lower()
        
        # Must be a meaningful path
        if len(path) <= 1 or path == '/':
            return False
            
        # Check for excluded paths
        if any(exclude in path for exclude in exclude_paths):
            return False
        
        # TapchiBitcoin article URLs typically end with .html
        if path.endswith('.html'):
            return True
            
        # Also accept paths that look like article slugs
        if re.match(r'^/[a-zA-Z0-9-]+/?$', path) and len(path) > 10:
            return True
            
        return False
    
    async def crawl_article(self, url):
        """Crawl individual article"""
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=self.run_config)
                if result.success:
                    return self.extract_article_data(url, result)
                else:
                    logger.warning(f"TapchiBitcoin: Failed to crawl: {url}")
                    return None
        except Exception as e:
            logger.error(f"TapchiBitcoin: Error crawling {url}: {e}")
            return None
    
    def extract_article_data(self, url, result):
        """Extract and format article data for TapchiBitcoin - Extract only the_content div"""
        # Get title from HTML title tag only
        title = self.extract_title_simple(result.html)
        
        # Extract ONLY content from the_content div
        content = self.extract_content_from_div(result.html)
        
        # Get image URL from media
        image_url = self.extract_main_image(result.media.get('images', []))
        
        # Get dates from HTML
        dates = self.extract_dates(result.html)
        
        return {
            "title": title,
            "content": content,  # Only content from the_content div
            "source": "tapchibitcoin.io",
            "extra_information": {
                "crawled_at": datetime.now().isoformat(),
                "raw_html": result.html,  # Include raw HTML for additional processing
                "extracted_text": result.extracted_content if hasattr(result, 'extracted_content') else "",
                "media_info": result.media if result.media else {}
            },
            "article_url": url,
            "image_url": image_url,
            "created_at": self._to_unix_timestamp(dates.get("created_at", "")),
            "updated_at": self._to_unix_timestamp(dates.get("updated_at", ""))
        }
    
    def extract_content_from_div(self, html):
        """Extract content specifically from div with class 'the_content'"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find the div with class 'the_content'
            content_div = soup.find('div', class_='the_content')
            
            if content_div:
                # Get all text content from this div, preserving structure
                content_text = content_div.get_text(separator='\n', strip=True)
                
                # Alternative: Get as markdown-like format
                # You can also convert to markdown format here if needed
                markdown_content = self.html_to_markdown(content_div)
                
                return markdown_content if markdown_content else content_text
            else:
                logger.warning("Could not find div with class 'the_content'")
                # Fallback to full markdown if the_content div is not found
                return ""
                
        except Exception as e:
            logger.error(f"Error extracting content from the_content div: {e}")
            return ""
    
    def html_to_markdown(self, soup_element):
        """Convert HTML element to markdown-like format"""
        try:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = False
            h.body_width = 0  # Don't wrap lines
            
            # Convert the specific element to markdown
            return h.handle(str(soup_element))
        except ImportError:
            # If html2text is not available, fall back to simple text extraction
            logger.warning("html2text not available, falling back to simple text extraction")
            return soup_element.get_text(separator='\n\n', strip=True)
        except Exception as e:
            logger.error(f"Error converting HTML to markdown: {e}")
            return soup_element.get_text(separator='\n\n', strip=True)
    
    def extract_title_simple(self, html):
        """Extract title from HTML title tag only - minimal processing"""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Get title from title tag
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
                # Remove common site branding
                title = re.sub(r'\s*-\s*TapchiBitcoin.*$', '', title, flags=re.IGNORECASE)
                title = re.sub(r'\s*\|\s*TapchiBitcoin.*$', '', title, flags=re.IGNORECASE)
                if title.strip():
                    return title.strip()
            
            # Fallback to first h1
            h1_tag = soup.find('h1')
            if h1_tag:
                return h1_tag.get_text(strip=True)
                
            return "Untitled"
            
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
            return "Untitled"
    
    def _to_unix_timestamp(self, date_string):
        """Convert date string to Unix timestamp"""
        if not date_string:
            return 0
            
        try:
            dt_object = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            if dt_object.tzinfo is None:
                dt_object = dt_object.replace(tzinfo=timezone.utc)
            return int(dt_object.timestamp())
        except ValueError:
            # TapchiBitcoin specific date formats
            formats = [
                '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d', 
                '%b %d, %Y', '%d/%m/%Y', '%d %B %Y', '%B %d, %Y'
            ]
            for fmt in formats:
                try:
                    dt_object = datetime.strptime(date_string, fmt)
                    if dt_object.tzinfo is None:
                        dt_object = dt_object.replace(tzinfo=timezone.utc)
                    return int(dt_object.timestamp())
                except ValueError:
                    continue
            return 0
    
    def extract_main_image(self, images):
        """Extract main image URL for TapchiBitcoin - minimal filtering"""
        # Just return the first valid image URL found
        for img in images:
            src = img.get('src', '')
            if src and any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                return src
        return ""
    
    def extract_dates(self, html):
        """Extract dates from HTML for TapchiBitcoin - minimal processing"""
        dates = {"created_at": "", "updated_at": ""}
        
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Try to find dates in the post_meta section
            post_meta = soup.find('ul', class_='post_meta')
            if post_meta:
                meta_items = post_meta.find_all('li')
                date_str = ""
                time_str = ""
                
                for item in meta_items:
                    text = item.get_text(strip=True)
                    # Check if it looks like a date (contains numbers and slashes)
                    if re.match(r'\d{1,2}/\d{1,2}/\d{4}', text):
                        date_str = text
                    # Check if it looks like time (contains colons)
                    elif re.match(r'\d{1,2}:\d{2}', text):
                        time_str = text
                
                # Combine date and time if both found
                if date_str:
                    if time_str:
                        combined_datetime = f"{date_str} {time_str}"
                        try:
                            dt_object = datetime.strptime(combined_datetime, '%d/%m/%Y %H:%M')
                            dates["created_at"] = dt_object.isoformat()
                        except ValueError:
                            dates["created_at"] = date_str
                    else:
                        dates["created_at"] = date_str
            
            # Try JSON-LD as fallback
            if not dates["created_at"]:
                json_ld_pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
                json_matches = re.findall(json_ld_pattern, html, re.DOTALL | re.IGNORECASE)
                
                for json_str in json_matches:
                    try:
                        data = json.loads(json_str)
                        if isinstance(data, dict):
                            if 'datePublished' in data:
                                dates["created_at"] = data['datePublished']
                            if 'dateModified' in data:
                                dates["updated_at"] = data['dateModified']
                            if dates["created_at"] and dates["updated_at"]:
                                break
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict):
                                    if 'datePublished' in item:
                                        dates["created_at"] = item['datePublished']
                                    if 'dateModified' in item:
                                        dates["updated_at"] = item['dateModified']
                                    if dates["created_at"] and dates["updated_at"]:
                                        break
                    except:
                        continue

        except Exception as e:
            logger.error(f"Error extracting dates: {e}")

        return dates
    
    async def send_to_api(self, data):
        """Send data to API"""        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_endpoint, json=data) as response:
                    response.raise_for_status()
                    logger.info(f"TapchiBitcoin ✅ Sent: {data.get('title', 'Untitled')[:50]}...")
                    return True
            except Exception as e:
                logger.error(f"TapchiBitcoin ❌ API Error: {e}")
                return False

    async def run_workflow(self):
        """Single crawl workflow"""
        if self.is_running:
            logger.warning("TapchiBitcoin ⚠️ Crawl already in progress, skipping...")
            return
            
        self.is_running = True
        start_time = datetime.now()
        
        try:
            logger.info("TapchiBitcoin 🚀 Starting crawl workflow...")
            
            # Get article links
            article_links = await self.get_article_links()
            if not article_links:
                logger.error("TapchiBitcoin ❌ No articles found")
                return
            
            if self.max_articles:
                article_links = article_links[:self.max_articles]
            
            logger.info(f"TapchiBitcoin 📰 Processing {len(article_links)} articles")
            
            # Crawl articles
            successful_count = 0
            for i, url in enumerate(article_links, 1):
                logger.info(f"TapchiBitcoin [{i}/{len(article_links)}] Crawling: {url}")
                article_data = await self.crawl_article(url)
                
                if article_data:
                    success = await self.send_to_api(article_data)
                    if success:
                        successful_count += 1
                
                await asyncio.sleep(2)  # Slightly longer rate limiting for politeness
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"TapchiBitcoin ✅ Completed in {duration:.1f}s - Success: {successful_count}/{len(article_links)} articles")
            
        except Exception as e:
            logger.error(f"TapchiBitcoin ❌ Workflow error: {e}")
        finally:
            self.is_running = False