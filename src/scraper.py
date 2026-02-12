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
        Handles pagination via createPageHTML(count, ...) logic.
        """
        logger.info(f"Scraping category list: {category_url}")
        
        # 1. Scrape first page
        try:
            await self.page.goto(category_url, timeout=TIMEOUT)
            await self.page.wait_for_load_state("networkidle")
            
            # Extract total pages
            # Look for script content: createPageHTML(22, 0, "index", "html")
            content = await self.page.content()
            import re
            page_match = re.search(r'createPageHTML\((\d+),', content)
            total_pages = 1
            if page_match:
                total_pages = int(page_match.group(1))
                logger.info(f"Found {total_pages} pages in pagination.")
            else:
                logger.info("No pagination info found, assuming single page.")

            # Iterate pages
            # Page 0 (First page) is already loaded, but let's standardize loop or Just extract now.
            
            # Helper to extract links from current page
            async def extract_links_current_page():
                await self.page.wait_for_selector("span", timeout=5000) # Generic wait
                
                # Check for list
                # Try specific selectors or generic
                links = await self.page.evaluate("""() => {
                    const anchors = Array.from(document.querySelectorAll('a'));
                    return anchors.map(a => {
                        return {
                            href: a.href,
                            text: a.innerText
                        }
                    }).filter(link => 
                        (link.href.includes('/t20') || link.href.includes('.html')) && 
                        !link.href.includes('index') &&
                        link.text.length > 5 // Filter short nav links
                    ); 
                }""")
                return links

            # Process Page 1 (Current)
            links = await extract_links_current_page()
            logger.info(f"Page 1: Found {len(links)} links.")
            for link in links:
                yield link['href']
            
            # Process Subsequent Pages (index_1.html, index_2.html... index_{total_pages-1}.html)
            # Note: createPageHTML(22, ...) usually means 22 pages. 
            # Page indices usually 0 to 21.
            # Page 1 is index.html (or index_0.html sometimes? No, usually index.html).
            # Page 2 is index_1.html.
            
            base_url = category_url.rstrip("/")
            
            for i in range(1, total_pages):
                page_url = f"{base_url}/index_{i}.html"
                logger.info(f"Scraping page {i+1}/{total_pages}: {page_url}")
                
                try:
                    await self.page.goto(page_url, timeout=TIMEOUT)
                    # await self.page.wait_for_load_state("networkidle") 
                    # Networkidle can be slow/flaky on static sites, wait for domcontentloaded
                    await self.random_sleep()
                    
                    links = await extract_links_current_page()
                    logger.info(f"Page {i+1}: Found {len(links)} links.")
                    for link in links:
                        yield link['href']
                        
                except Exception as e:
                    logger.error(f"Error scraping page {i+1} ({page_url}): {e}")
                    continue
                    
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
