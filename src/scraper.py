import asyncio
import random
import logging
from playwright.async_api import async_playwright
from .config import HEADLESS, TIMEOUT, RANDOM_DELAY_MIN, RANDOM_DELAY_MAX, USER_AGENTS

logger = logging.getLogger(__name__)

class CCDIScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None

    async def start(self):
        """Initialize the browser and context."""
        self.playwright = await async_playwright().start()
        
        # Launch options
        self.browser = await self.playwright.chromium.launch(
            headless=HEADLESS,
            args=["--disable-blink-features=AutomationControlled"] # Basic anti-detect
        )
        
        # Context options for stealth
        user_agent = random.choice(USER_AGENTS)
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1366, "height": 768},
            locale="zh-CN",
            timezone_id="Asia/Shanghai"
        )
        
        # Inject stealth scripts
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        self.page = await self.context.new_page()
        logger.info("Browser initialized successfully.")

    async def stops(self):
        """Close the browser."""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed.")

    async def random_sleep(self):
        """Sleep for a random interval to simulate human behavior."""
        delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
        await asyncio.sleep(delay)

    async def scrape_category(self, category_url):
        """
        Scrape a category listing page for detail URLs.
        Yields detail URLs.
        """
        logger.info(f"Scraping category list: {category_url}")
        try:
            await self.page.goto(category_url, timeout=TIMEOUT)
            await self.page.wait_for_load_state("networkidle")
            
            # Extract links
            # Selectors specific to CCDI listing pages
            # Usually strict list items are in 'ul.list_news_dl li a' or similar
            # We will grab all relevant links
            
            # Wait for the list to appear
            await self.page.wait_for_selector("ul", timeout=10000)
            
            links = await self.page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                return anchors.map(a => {
                    return {
                        href: a.href,
                        text: a.innerText
                    }
                }).filter(link => link.href.includes('/t20') || link.href.includes('.html')); 
                // CCDI articles often have date-based IDs like t2023... or .html
            }""")
            
            logger.info(f"Found {len(links)} potential links on page.")
            
            unique_links = set()
            for link in links:
                url = link['href']
                if url not in unique_links and "ccdi.gov.cn" in url:
                    unique_links.add(url)
                    yield url
                    
        except Exception as e:
            logger.error(f"Error scraping category {category_url}: {e}")

    async def get_page_content(self, url):
        """
        Navigate to a detail page and return its HTML content.
        """
        logger.info(f"Navigating to detail page: {url}")
        try:
            await self.page.goto(url, timeout=TIMEOUT)
            # await self.random_sleep() # Random sleep before or after? After loading.
            
            # Simulate some human interaction
            await self.page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            
            content = await self.page.content()
            await self.random_sleep() # Sleep after reading
            return content
        except Exception as e:
            logger.error(f"Error getting content for {url}: {e}")
            return None
