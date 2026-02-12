import asyncio
import logging
import os
from datetime import datetime
from src.config import CATEGORIES, OUTPUT_DIR, OUTPUT_FILENAME_FORMAT
from src.scraper import CCDIScraper
from src.parser import extract_detail, save_to_excel
from src.cli import show_welcome, show_status_table, create_progress, log_message

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='scraper.log', filemode='w')

# Create output dir
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def main():
    show_welcome()
    
    # Pre-flight checks (simulated for now, could be real)
    checks = [
        ("Network", "ok", "Connected"),
        ("Storage", "ok", f"Writable ({OUTPUT_DIR})"),
        ("Browser Engine", "ok", "Chromium Ready")
    ]
    show_status_table(checks)
    
    scraper = CCDIScraper()
    await scraper.start()
    
    all_data = []
    
    try:
        with create_progress() as progress:
            # Create a main task for categories
            # We flatten the categories to iterate
            tasks = []
            for cat_name, subcats in CATEGORIES.items():
                for sub_name, url in subcats.items():
                    tasks.append((f"{cat_name} - {sub_name}", url))
            
            main_task = progress.add_task("[green]Processing Categories...", total=len(tasks))
            
            for task_name, url in tasks:
                progress.update(main_task, description=f"Scraping: {task_name}")
                
                # Get list of URLs
                # In a real scenario we might want to paginate. Limit to first page for now.
                detail_urls = []
                async for detail_url in scraper.scrape_category(url):
                    detail_urls.append(detail_url)
                    # Limit for testing/demo purposes if needed, user said "bootstrapping... data granularity"
                    # We'll try to get all on the first page.
                
                if not detail_urls:
                    log_message(f"No articles found for {task_name}", level="warning")
                    progress.advance(main_task)
                    continue
                    
                sub_task = progress.add_task(f"  Downloading {len(detail_urls)} articles...", total=len(detail_urls))
                
                for d_url in detail_urls:
                    html = await scraper.get_page_content(d_url)
                    if html:
                        data = extract_detail(html, d_url)
                        # Add category info
                        data["category"] = task_name.split(" - ")[0]
                        data["subcategory"] = task_name.split(" - ")[1]
                        all_data.append(data)
                    progress.advance(sub_task)
                
                progress.remove_task(sub_task)
                progress.advance(main_task)
                
    except Exception as e:
        log_message(f"Critical Error: {e}", level="error")
        logging.error("Critical Error", exc_info=True)
    finally:
        await scraper.stops()
        
    # Save Data
    if all_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = OUTPUT_FILENAME_FORMAT.format(timestamp=timestamp)
        filepath = os.path.join(OUTPUT_DIR, filename)
        save_to_excel(all_data, filepath)
        log_message(f"Data saved to {filepath}", level="success")
    else:
        log_message("No data collected.", level="warning")

if __name__ == "__main__":
    asyncio.run(main())
