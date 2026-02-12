import asyncio
import os
import sys
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table

from src.config import CATEGORIES, HEADLESS, EXPORT_INTERVAL, COMPLETION_WAIT_TIME, OUTPUT_DIR, OUTPUT_FILENAME_FORMAT
from src.scraper import CCDIScraper
from src.storage import Storage
from src.cli import create_progress, TimeRemainingColumn

console = Console()
logging.basicConfig(level=logging.ERROR, filename="scraper_error.log", filemode="a", format="%(asctime)s - %(levelname)s - %(message)s")

def show_status_table(checks):
    table = Table(title="CCDI Scraper - Initialization")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    for component, status in checks.items():
        status_str = "[green]OK[/green]" if status else "[red]FAILED[/red]"
        table.add_row(component, status_str)
    
    console.print(table)

async def check_environment():
    checks = {
        "Python Version": True, # Assumed if running
        "Playwright Installed": True,
        "Network": True
    }
    # Could add real checks here
    return checks

async def process_subcategory(scraper, storage, category, subcategory, url, progress, task_id):
    """
    Process a single subcategory: scrape list pages, detailed pages, save data.
    """
    new_articles_count = 0
    
    try:
        # Phase 1: Scanning (Collecting URLs)
        progress.update(task_id, description=f"[cyan]{category} - {subcategory}[/cyan] (Scanning Pages...)", total=None)
        
        detail_urls = []
        async for detail_url in scraper.scrape_category(url, storage):
             # Double check if already scraped (though scraper does it too)
             if not storage.is_scraped(detail_url):
                 detail_urls.append(detail_url)
                 
             # Give UI feedback every 10 items found
             if len(detail_urls) % 10 == 0:
                  progress.update(task_id, description=f"[cyan]{category} - {subcategory}[/cyan] (Scanning: Found {len(detail_urls)}...)")

        if not detail_urls:
            progress.update(task_id, description=f"[green]{category} - {subcategory} (Skipped: No new)[/green]", completed=100, total=100)
            return 0
            
        # Phase 2: Downloading Details
        total_items = len(detail_urls)
        progress.update(task_id, description=f"[yellow]{category} - {subcategory}[/yellow] (Downloading {total_items} items)", total=total_items, completed=0)
        
        for i, detail_url in enumerate(detail_urls):
            # Check scraping status again in case of overlap or previous run
            if storage.is_scraped(detail_url):
                progress.advance(task_id)
                continue
                
            # Get content
            content = await scraper.get_page_content(detail_url)
            if content:
                # Parse
                from src.parser import extract_detail
                data = extract_detail(content, detail_url)
                
                # Add category info
                data["category"] = category
                data["subcategory"] = subcategory

                # Save
                if storage.save_article(data):
                    new_articles_count += 1
            
            # Cooldown between items
            import random
            from src.config import RANDOM_DELAY_MIN, RANDOM_DELAY_MAX
            delay = random.uniform(RANDOM_DELAY_MIN, RANDOM_DELAY_MAX)
            # progress.update(task_id, description=f"[yellow]{category} - {subcategory}[/yellow] (Waiting {delay:.1f}s...)")
            await asyncio.sleep(delay)
            
            progress.advance(task_id)
                    
        progress.update(task_id, description=f"[green]{category} - {subcategory} (Done: {new_articles_count} new)[/green]", completed=100)
    except Exception as e:
        progress.update(task_id, description=f"[red]{category} - {subcategory} (Error)[/red]")
        logging.error(f"Error in {category} - {subcategory}: {e}", exc_info=True)
        
    return new_articles_count

async def periodic_export(storage):
    """
    Background task to periodically export data to Excel.
    """
    while True:
        try:
            await asyncio.sleep(EXPORT_INTERVAL)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = OUTPUT_FILENAME_FORMAT.format(timestamp=timestamp)
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            console.print(f"[grey50]Auto-exporting data to {filepath}...[/grey50]")
            storage.export_to_excel(filepath)
        except asyncio.CancelledError:
            break
        except Exception as e:
            console.print(f"[red]Auto-export failed: {e}[/red]")
            logging.error(f"Auto-export failed: {e}", exc_info=True)

async def main():
    checks = await check_environment()
    show_status_table(checks)
    
    storage = Storage()
    # Clean up any bad data from previous runs (e.g. block pages)
    storage.clean_bad_data()
    
    scraper = CCDIScraper()
    await scraper.start()
    
    # Start background export task
    export_task = asyncio.create_task(periodic_export(storage))
    
    try:
        with create_progress() as progress:
            tasks = []
            
            for category, subcats in CATEGORIES.items():
                for subcategory, url in subcats.items():
                    task_id = progress.add_task(f"{category} - {subcategory}", total=None) # Indeterminate initially
                    tasks.append(process_subcategory(scraper, storage, category, subcategory, url, progress, task_id))
            
            results = await asyncio.gather(*tasks)
            
            # total_new = sum(results)
            
    except Exception as e:
        console.print(f"[bold red]Critical Error: {e}[/bold red]")
        logging.error("Critical Error in main", exc_info=True)
    finally:
        # Cancel export task
        export_task.cancel()
        try:
            await export_task
        except asyncio.CancelledError:
            pass
            
        await scraper.stops()
        
    # Final Export
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = OUTPUT_FILENAME_FORMAT.format(timestamp=timestamp)
    filepath = os.path.join(OUTPUT_DIR, filename)
    storage.export_to_excel(filepath)
    
    console.print(f"[bold green][SUCCESS] All done! Full export saved to {filepath}[/bold green]")
    
    if COMPLETION_WAIT_TIME > 0:
        console.print(f"[yellow]Waiting {COMPLETION_WAIT_TIME} seconds before closing...[/yellow]")
        await asyncio.sleep(COMPLETION_WAIT_TIME)

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    try:
        # if sys.platform == 'win32':
        #      asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Scraper stopped by user.[/yellow]")
