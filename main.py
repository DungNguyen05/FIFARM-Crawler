import asyncio
import json
import re
from datetime import datetime, timezone
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from urllib.parse import urlparse
import aiohttp

# Configuration Constants
API_ENDPOINT = "http://localhost:8080/admin/news-articles"
HOME_URL = "https://coin98.net/home/moi-nhat"
MAX_ARTICLES = 5

class Coin98ArticleCrawler:
    def __init__(self):
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, word_count_threshold=50)
        self.home_url = HOME_URL
        self.api_endpoint = API_ENDPOINT
        
    async def get_article_links(self):
        """Get all article links from homepage"""
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=self.home_url, config=self.run_config)
            
            if not result.success:
                return []
            
            internal_links = []
            for link in result.links['internal']:
                href = link['href'] if isinstance(link, dict) and 'href' in link else link
                if self.is_article_link(href):
                    internal_links.append(href)
            
            return list(set(internal_links))
    
    def is_article_link(self, url):
        """Check if URL is an article link"""
        if not url or not isinstance(url, str):
            return False
            
        exclude_paths = ['/learn', '/series', '/report', '/courses', '/signin',
                        '/home', '/#', '/about', '/contact', '/privacy',
                        '/terms', '/categories', '/tags', '/inside-coin98']
        
        parsed = urlparse(url)
        path = parsed.path.lower()
        
        return len(path) > 3 and path != '/' and not any(exclude in path for exclude in exclude_paths)
    
    async def crawl_article(self, url):
        """Crawl individual article"""
        try:
            async with AsyncWebCrawler(config=self.browser_config) as crawler:
                result = await crawler.arun(url=url, config=self.run_config)
                return self.extract_article_data(url, result) if result.success else None
        except Exception:
            return None
    
    def extract_article_data(self, url, result):
        """Extract and format article data"""
        title = self.extract_title(result.markdown, result.html)
        content = self.clean_content(result.markdown)
        image_url = self.extract_main_image(result.media.get('images', []))
        dates = self.extract_dates(result.html)
        
        return {
            "title": title,
            "content": content,
            "source": "coin98.net",
            "extra_information": {},
            "article_url": url,
            "image_url": image_url,
            "created_at": self._to_unix_timestamp(dates.get("created_at", "")),
            "updated_at": self._to_unix_timestamp(dates.get("updated_at", ""))
        }
    
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
            formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d', '%b %d, %Y', '%d/%m/%Y']
            for fmt in formats:
                try:
                    dt_object = datetime.strptime(date_string, fmt)
                    if dt_object.tzinfo is None:
                        dt_object = dt_object.replace(tzinfo=timezone.utc)
                    return int(dt_object.timestamp())
                except ValueError:
                    continue
            return 0
    
    def extract_title(self, markdown, html):
        """Extract title from markdown or HTML"""
        # Try markdown heading first
        for line in markdown.split('\n'):
            line = line.strip()
            if line.startswith('# ') and len(line) > 10:
                title = re.sub(r'\[.*?\]\(.*?\)', '', line[2:]).strip()
                if not any(noise in title.lower() for noise in ['search', 'logo', 'follow']):
                    return title
        
        # Fallback to HTML title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
        if title_match:
            title = title_match.group(1).strip()
            return re.sub(r'\s*-\s*Coin98.*$', '', title)
        
        return "Untitled"
    
    def clean_content(self, markdown):
        """Clean markdown content"""
        if not markdown:
            return ""
        
        skip_patterns = ['Language edition', 'Search', 'logo', 'Follow', 'Channel logo',
                        'AVAILABLE EDITIONS', 'Vietnamese', 'English', 'Coin98 Insights',
                        'Published', 'Updated', 'ago', 'min read', 'Save', 'Copy link',
                        'RELEVANT SERIES', '© 2024', 'All Rights Reserved', 'Powered by',
                        '![Vietnamese]', '![English]', 'flagcdn.com', '_next/image',
                        'thumbnail', 'files.amberblocks.com', 'Follow us', 'Subscribe']
        
        lines = markdown.split('\n')
        cleaned_lines = []
        content_started = False
        
        for line in lines:
            line = line.strip()
            
            if not line and not content_started:
                continue
            
            if line.startswith('# ') and len(line) > 10:
                content_started = True
                cleaned_lines.append(line)
                continue
            
            if not content_started:
                continue

            if any(pattern in line for pattern in skip_patterns) or len(line) < 5:
                continue
            
            # Remove images and links
            line = re.sub(r'!\[.*?\]\(.*?\)', '', line)
            line = re.sub(r'\[.*?\]\(.*?\)', '', line)
            
            if line:
                cleaned_lines.append(line)
        
        content = '\n'.join(cleaned_lines)
        return re.sub(r'\n\s*\n\s*\n+', '\n\n', content).strip()
    
    def extract_main_image(self, images):
        """Extract main image URL"""
        # Prioritize amberblocks images
        for img in images:
            src = img.get('src', '')
            if (src and 'files.amberblocks.com' in src and
                any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                not any(skip in src.lower() for skip in ['logo', 'icon', 'avatar', 'flag'])):
                return src
        
        # Fallback to any good image
        for img in images:
            src = img.get('src', '')
            if (src and 
                any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                not any(skip in src.lower() for skip in ['logo', 'icon', 'flag'])):
                return src
        return ""
    
    def extract_dates(self, html):
        """Extract dates from HTML"""
        dates = {"created_at": "", "updated_at": ""}
        
        # Try JSON-LD first
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
            except:
                continue
        
        # Fallback to time tags
        if not dates["created_at"]:
            time_patterns = [
                r'<time[^>]*datetime=["\']([^"\']+)["\']',
                r'<span[^>]*class=["\']date[^"\']*["\'][^>]*>([^<]+)</span>'
            ]
            for pattern in time_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    for match in matches:
                        if any(str(y) in match for y in range(2020, datetime.now().year + 1)):
                            dates["created_at"] = match
                            break
                    if dates["created_at"]:
                        break

        return dates
    
    async def send_to_api(self, data):
        """Send data to API"""
        if not self.api_endpoint or "localhost" not in self.api_endpoint:
            return False
            
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.api_endpoint, json=data) as response:
                    response.raise_for_status()
                    print(f"✅ Sent: {data.get('title', 'Untitled')[:50]}...")
                    return True
            except Exception as e:
                print(f"❌ API Error: {e}")
                return False

    async def run_workflow(self, max_articles=MAX_ARTICLES):
        
        # Get article links
        article_links = await self.get_article_links()
        if not article_links:
            print("❌ No articles found")
            return
        
        if max_articles:
            article_links = article_links[:max_articles]
        
        print(f"📰 Found {len(article_links)} articles to crawl")
        
        # Crawl articles
        successful_count = 0
        for i, url in enumerate(article_links, 1):
            print(f"[{i}/{len(article_links)}] Crawling...")
            article_data = await self.crawl_article(url)
            
            if article_data:
                success = await self.send_to_api(article_data)
                if success:
                    successful_count += 1
            
            await asyncio.sleep(1)
        
        print(f"✅ Completed! Successfully sent {successful_count}/{len(article_links)} articles")

async def main():
    crawler = Coin98ArticleCrawler()
    await crawler.run_workflow(max_articles=MAX_ARTICLES)

if __name__ == "__main__":
    asyncio.run(main())