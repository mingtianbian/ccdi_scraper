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
        
        # GLOBAL CONTROL
        self.running_event = asyncio.Event()
        self.running_event.set() # Initially running
        self.handling_lock = asyncio.Lock()
        
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
        Check if redirected to error page or blocked. If so, pause until resolved.
        Checks URL, Title, and Content.
        """
        try:
            # Wait a short moment for any redirects or JS to settle
            # await page.wait_for_timeout(1000) 
            
            # Get current state
            url = page.url
            try:
                title = await page.title()
            except:
                title = ""
            
            # Simple check first
            is_blocked = False
            
            if "/error/error.html" in url or "security_verify" in url:
                is_blocked = True
            elif "系统维护" in title or "403 Forbidden" in title or "Security Verify" in title:
                is_blocked = True
            
            if is_blocked:
                # Double check content if needed, but URL/Title usually enough
                pass

            if is_blocked:
                # 1. STOP THE WORLD
                self.running_event.clear()
                
                logger.warning(f"Risk control detected at {url}. Entering handling lock...")
                
                # 2. Serialize handling (Only one tab needs to scream "Fix me", others wait)
                async with self.handling_lock:
                    print(f"\n[!] WARN: Risk control (Thread {id(asyncio.current_task())})")
                    
                    while True:
                         # Double check status inside lock (maybe previous thread fixed it?)
                         try:
                            # We must reload THIS page to verify if it's clear
                            # If checking logic is simple check:
                            curr_url = page.url
                            curr_title = await page.title()
                            
                            still_blocked = False
                            if "/error/error.html" in curr_url or "security_verify" in curr_url:
                                still_blocked = True
                            elif "系统维护" in curr_title or "403 Forbidden" in curr_title or "Security Verify" in curr_title:
                                still_blocked = True
                                
                            if not still_blocked:
                                print(f"[!] Block resolved for this thread. Resuming...")
                                # Important: Set event so others can proceed
                                self.running_event.set()
                                break
                         except Exception as e:
                             logger.error(f"Error checking block: {e}")
                        
                         print(f"[!] PAUSED (Global). Please manually verify in browser.")
                         print(f"[!] Waiting 30s to retry...")
                         await asyncio.sleep(30)
                         
                         try:
                             print("[!] Retrying reload...")
                             await page.reload(timeout=TIMEOUT)
                             try:
                                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                             except:
                                pass
                         except Exception as e:
                             pass

        except Exception as e:
            logger.error(f"Error in _handle_block: {e}")

    async def random_sleep(self):
        """Sleep for a random interval to simulate human behavior."""
        delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
        await asyncio.sleep(delay)

    async def scrape_category(self, category_url, storage=None):
        """
        Scrape a category listing page for detail URLs.
        Yields detail URLs.
        """
        # WAIT FOR RUNNING STATUS
        await self.running_event.wait()
        
        logger.info(f"Scraping category list: {category_url}")
        
        # NEW APPROACH: scrape_category uses its OWN page.
        page = await self.context.new_page()
        
        try:
            await self.running_event.wait()
            try:
                await page.goto(category_url, timeout=TIMEOUT)
                await self._handle_block(page)
            except Exception as e:
                logger.error(f"Goto failed: {e}")

            try:
               await page.wait_for_load_state("networkidle", timeout=10000)
            except:
               pass 
            
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
            
            base_url = category_url.rstrip("/")
            
            for i in range(1, total_pages):
                await self.running_event.wait() # Check global pause
                
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

    async def get_page_content(self, url):
        """
        Navigate to a detail page and return its HTML content.
        Uses a temporary page to facilitate concurrency.
        """
        # WAIT FOR RUNNING STATUS
        await self.running_event.wait()
        
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
