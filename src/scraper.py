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

    async def _handle_block(self, page):
        """
        Check if redirected to error page. If so, pause until resolved.
        """
        # Check standard error URL or generic error indicators
        if "/error/error.html" in page.url or "security_verify" in page.url:
            logger.warning(f"Risk control detected at {page.url}. Pausing...")
            
            # Print explicit message to console
            print(f"\n[!] WARN: Risk control Detected! Redirected to: {page.url}")
            print(f"[!] The scraper is PAUSED. Please check the browser window.")
            print(f"[!] Resolve the captcha or change IP, then wait for auto-retry.")
            
            while "/error/error.html" in page.url or "security_verify" in page.url:
                print(f"[!] Paused... Retrying in 30 seconds...")
                await asyncio.sleep(30)
                try:
                    logger.info("Retrying page reload...")
                    await page.reload(timeout=TIMEOUT)
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except:
                        pass
                except Exception as e:
                    logger.error(f"Reload failed: {e}")
            
            print(f"[!] Block resolved. Resuming...")
            logger.info("Block resolved. Resuming...")

    async def random_sleep(self):
        """Sleep for a random interval to simulate human behavior."""
        delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
        await asyncio.sleep(delay)

    async def scrape_category(self, category_url, storage=None):
        """
        Scrape a category listing page for detail URLs.
        Yields detail URLs.
        Handles pagination via createPageHTML(count, ...) logic.
        """
        logger.info(f"Scraping category list: {category_url}")
        
        # 1. Scrape first page
        try:
            # Create a localized page for this task if not reusing the main one
            # For concurrency, we should ideally have a page per task. 
            # But the class design currently has self.page.
            # We will refactor in main.py to separate instances or handle locking.
            # For now, let's assume self.page is safe or we use a lock.
            # actually better: create a new page for this category transaction if possible.
            # BUT efficient way: use self.page and serialize navigation (bad for concurrency).
            # BETTER: The Class instance should represent ONE browser context.
            # We will create Multiple Scraper Instances in main.py or multiple pages.
            
            # Let's assume this instance owns self.page and main.py creates one scraper per task?
            # No, creating 6 browsers is heavy.
            # Better: One Browser, Multiple Contexts/Pages.
            # Let's adjust Scraper to create a new page for this task if needed.
            
            # NEW APPROACH: scrape_category uses its OWN page.
            page = await self.context.new_page()
            
            try:
                await page.goto(category_url, timeout=TIMEOUT)
                await self._handle_block(page)

                try:
                   await page.wait_for_load_state("networkidle", timeout=10000)
                except:
                   pass # Networkidle might timeout
                
                # Extract total pages
                content = await page.content()
                import re
                page_match = re.search(r'createPageHTML\((\d+),', content)
                total_pages = 1
                if page_match:
                    total_pages = int(page_match.group(1))
                    logger.info(f"Found {total_pages} pages in pagination for {category_url}.")
                else:
                    logger.info(f"No pagination info found for {category_url}, assuming single page.")

                # Helper to extract links
                async def extract_links(p):
                    # await p.wait_for_selector("span", timeout=5000) # Generic wait
                    # Check for list
                    links = await p.evaluate("""() => {
                        const anchors = Array.from(document.querySelectorAll('a'));
                        return anchors.map(a => {
                            return {
                                href: a.href,
                                text: a.innerText
                            }
                        }).filter(link => 
                            (link.href.includes('/t20') || link.href.includes('.html')) && 
                            !link.href.includes('index') &&
                            link.text.length > 5 
                        ); 
                    }""")
                    return links

                # Process Page 1
                links = await extract_links(page)
                # logger.info(f"Page 1: Found {len(links)} links.")
                for link in links:
                    if storage and storage.is_scraped(link['href']):
                        continue
                    yield link['href']
                
                # Close page 1's content relation? No, keep using this page for subsequent requests if simple
                
                base_url = category_url.rstrip("/")
                
                for i in range(1, total_pages):
                    page_url = f"{base_url}/index_{i}.html"
                    # logger.info(f"Scraping page {i+1}/{total_pages}: {page_url}")
                    
                    try:
                        await page.goto(page_url, timeout=TIMEOUT)
                        await self._handle_block(page)
                        # await self.random_sleep() # Removing long sleep for speed
                        await asyncio.sleep(0.5) 
                        
                        links = await extract_links(page)
                        for link in links:
                            if storage and storage.is_scraped(link['href']):
                                continue
                            yield link['href']
                            
                    except Exception as e:
                        logger.error(f"Error scraping page {i+1} ({page_url}): {e}")
                        continue
            finally:
                await page.close()
                    
        except Exception as e:
            logger.error(f"Error scraping category {category_url}: {e}")

    async def get_page_content(self, url):
        """
        Navigate to a detail page and return its HTML content.
        Uses a temporary page to facilitate concurrency.
        """
        # logger.info(f"Navigating to detail page: {url}")
        page = await self.context.new_page()
        try:
            await page.goto(url, timeout=TIMEOUT)
            await self._handle_block(page)
            
            # Simulate minimal human interaction
            # await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            
            content = await page.content()
            # await self.random_sleep() 
            return content
        except Exception as e:
            logger.error(f"Error getting content for {url}: {e}")
            return None
        finally:
            await page.close()
