from bs4 import BeautifulSoup
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from src.parser import extract_detail

html_content = """
<div class="daty_con_bj">
来源：中央纪委国家监委网站
发布时间：
                               
                         2026-02-12 13:15
分享
</div>
"""

def test():
    data = extract_detail(html_content, "http://test.com")
    print(f"Extracted Data: {data}")
    
    if data['source'] == '中央纪委国家监委网站' and data['publish_time'] == '2026-02-12 13:15':
        print("SUCCESS: Parser works correctly!")
    else:
        print("FAILURE: Parser failed.")

if __name__ == "__main__":
    test()
