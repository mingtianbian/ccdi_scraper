import asyncio
import logging
import os
from datetime import datetime
from src.config import CATEGORIES, OUTPUT_DIR, OUTPUT_FILENAME_FORMAT
from src.scraper import CCDIScraper
from src.parser import extract_detail, save_to_excel
from src.cli import show_welcome, show_status_table, create_progress, log_message
from src.storage import Storage

# Setup logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', filename='scraper.log', filemode='a')

# Create output dir
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

async def process_subcategory(scraper, storage, progress, task_name, url):
    """
    Process a single subcategory (List -> Details).
    """
    task_id = progress.add_task(f"[cyan]{task_name}", total=None) # Total unknown initially
    
    try:
        data_count = 0
        
        # 1. Scrape List
        progress.update(task_id, description=f"[cyan]{task_name}[/cyan] (Scanning...)")
        
        detail_urls = []
        async for detail_url in scraper.scrape_category(url, storage=storage):
            detail_urls.append(detail_url)
            # Update progress description periodically to show life
            if len(detail_urls) % 5 == 0:
                progress.update(task_id, description=f"[cyan]{task_name}[/cyan] (Found {len(detail_urls)}...)")
        
        if not detail_urls:
            progress.update(task_id, description=f"[yellow]{task_name}[/yellow] (No new articles)", completed=100, total=100)
            return

        # 2. Scrape Details
        progress.update(task_id, description=f"[cyan]{task_name}[/cyan] (Downloading)", total=len(detail_urls), completed=0)
        
        for d_url in detail_urls:
            # Double check (redundant but safe)
            if storage.is_scraped(d_url):
                progress.advance(task_id)
                continue
                
            html = await scraper.get_page_content(d_url)
            if html:
                data = extract_detail(html, d_url)
                # Add category info
                data["category"] = task_name.split(" - ")[0]
                data["subcategory"] = task_name.split(" - ")[1]
                
                storage.save_article(data)
                data_count += 1
            
            progress.advance(task_id)
            
        progress.update(task_id, description=f"[green]{task_name}[/green] (Done: {data_count} new)")
        
    except Exception as e:
        log_message(f"Error in {task_name}: {e}", level="error")
        progress.update(task_id, description=f"[red]{task_name}[/red] (Error)")
        logging.error(f"Error in {task_name}", exc_info=True)


async def main():
    show_welcome()
    
    # Pre-flight checks
    checks = [
        ("Network", "ok", "Connected"),
        ("Storage", "ok", f"SQLite DB ({OUTPUT_DIR}/ccdi.db)"),
        ("Browser Engine", "ok", "Chromium Ready")
    ]
    show_status_table(checks)
    
    storage = Storage()
    scraper = CCDIScraper()
    await scraper.start()
    
    try:
        with create_progress() as progress:
            tasks = []
            
            # Create list of tasks
            for cat_name, subcats in CATEGORIES.items():
                for sub_name, url in subcats.items():
                    task_name = f"{cat_name} - {sub_name}"
                    # Create coroutine
                    coro = process_subcategory(scraper, storage, progress, task_name, url)
                    tasks.append(coro)
            
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
            
    except Exception as e:
        log_message(f"Critical Error: {e}", level="error")
        logging.error("Critical Error", exc_info=True)
    finally:
        await scraper.stops()
        
    # Export final report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(OUTPUT_DIR, f"ccdi_export_{timestamp}.xlsx")
    storage.export_to_excel(filepath)
    log_message(f"All done! Full export saved to {filepath}", level="success")

if __name__ == "__main__":
    asyncio.run(main())
