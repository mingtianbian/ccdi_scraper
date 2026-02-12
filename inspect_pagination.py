import requests
from bs4 import BeautifulSoup

def inspect_pagination():
    url = "https://www.ccdi.gov.cn/scdcn/zggb/zjsc/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')
        
        # Look for common pagination classes
        pagination = soup.select_one('.page') or soup.select_one('.pagination') or soup.find(string=lambda t: '下一页' in t if t else False)
        
        if pagination:
            if hasattr(pagination, 'prettify'):
                print(pagination.prettify())
            else:
                print(f"Found text-based pagination: {pagination.parent.prettify()}")
        else:
            # Print the bottom of the page or look for scripts
            print("No obvious pagination element found. searching scripts...")
            scripts = soup.find_all('script')
            for s in scripts:
                if s.string and ('createPageHTML' in s.string or 'countPage' in s.string):
                    print("Found pagination script:")
                    print(s.string[:500])
                    
    except Exception as e:
        print(e)

if __name__ == "__main__":
    inspect_pagination()
