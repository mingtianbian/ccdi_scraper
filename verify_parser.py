import requests
from src.parser import extract_detail
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def verify_parser():
    # A known article URL from CCDI (or one from the list)
    # Let's try to get one from the main page or searching
    # Example: "http://www.ccdi.gov.cn/scdcn/zggb/zjsc/202401/t20240129_326694.html" (Example URL, might be old)
    # I'll use a generic one if I can find one, or just the main structure test.
    
    # Actually, I'll valid a specific URL if I can find one.
    # Let's use a recent one if possible, or just the structure of a typical page.
    # I will just fetch the main category page and see if I can find a link, then parse that link.
    
    category_url = "https://www.ccdi.gov.cn/scdcn/zggb/zjsc/"
    print(f"Fetching category: {category_url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(category_url, headers=headers, timeout=10)
        resp.encoding = 'utf-8' # CCDI is utf-8 usually
        
        if resp.status_code != 200:
            print("Failed to fetch category page.")
            return

        # Find a link to a detail page
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'lxml')
        
        links = soup.select('ul.list_news_dl li a')
        if not links:
            print("No links found on category page using selector 'ul.list_news_dl li a'. Trying generic 'a'.")
            links = soup.select('a')
            
        detail_url = None
        for link in links:
            href = link.get('href')
            if href and ('.html' in href or '/t20' in href):
                if href.startswith('./'):
                    # relative path
                    detail_url = category_url + href[2:]
                elif href.startswith('/'):
                    detail_url = "https://www.ccdi.gov.cn" + href
                elif href.startswith('http'):
                    detail_url = href
                else:
                     detail_url = category_url + href
                break
        
        if not detail_url:
            print("Could not find a detail URL to test.")
            return
            
        print(f"Testing parser on: {detail_url}")
        
        # Fetch detail page
        resp_detail = requests.get(detail_url, headers=headers, timeout=10)
        resp_detail.encoding = 'utf-8'
        
        if resp_detail.status_code != 200:
            print("Failed to fetch detail page.")
            return
            
        # Run Parser
        data = extract_detail(resp_detail.text, detail_url)
        
        print("\n--- Extracted Data ---")
        for k, v in data.items():
            if k == 'content':
                print(f"{k}: {v[:100]}...") # Show snippet
            else:
                print(f"{k}: {v}")
        
        if data['title'] != "Title Not Found" and data['content']:
            print("\n[SUCCESS] Parser verification passed!")
        else:
            print("\n[FAILURE] Parser extraction failed.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    verify_parser()
