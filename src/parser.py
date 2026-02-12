from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def clean_html(html_content):
    """
    Remove scripts, styles, and other redundant tags from HTML.
    """
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Remove script and style elements
    for script in soup(["script", "style", "iframe", "noscript"]):
        script.extract()
        
    return soup

def extract_detail(html_content, url):
    """
    Extract title, source, time, and body content from the detail page.
    """
    soup = clean_html(html_content)
    
    data = {"url": url}
    
    # Title
    # Try common selectors for CCDI website
    title_selectors = [".daty_con_title", ".article-title", "h2", "h1"]
    for selector in title_selectors:
        element = soup.select_one(selector)
        if element:
            data["title"] = element.get_text(strip=True)
            break
    if "title" not in data:
        data["title"] = "Title Not Found"

    # Info (Source, Time)
    # Usually in a block like <div class="daty_con_bj">...</div>
    info_selectors = [".daty_con_bj", ".info", ".article-info"]
    for selector in info_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(" ", strip=True)
            
            # Extract Source
            # Format often: "来源：中央纪委国家监委网站"
            source_match = re.search(r"来源：(.*?)(?:\s|$)", text)
            data["source"] = source_match.group(1).strip() if source_match else "Unknown"
            
            # Extract Time
            # Format often: "发布时间：2023-01-01 10:00"
            time_match = re.search(r"发布时间：(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", text)
            if not time_match:
                 time_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", text)
            data["publish_time"] = time_match.group(1) if time_match else "Unknown"
            break
            
    if "source" not in data:
        data["source"] = "Unknown"
    if "publish_time" not in data:
        data["publish_time"] = "Unknown"

    # Content
    # usually in <div class="TRS_Editor"> or <div class="daty_con_text">
    content_selectors = [".TRS_Editor", ".daty_con_text", ".article-content", "#content"]
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            data["content"] = element.get_text("\n", strip=True)
            break
            
    if "content" not in data:
        # Fallback: try to find the longest text block
        logger.warning(f"Content selector failed for {url}, trying fallback.")
        data["content"] = soup.get_text("\n", strip=True)

    # Parse Name and Position from Title
    name, position = parse_title_info(data.get("title", ""))
    data["name"] = name
    data["position"] = position

    return data

def parse_title_info(title):
    """
    Extract Name and Position from title.
    Common pattern: "Name Position accept review"
    """
    # Simple heuristic: Split by keywords like "接受", "涉嫌"
    # Example: "贵州省政协原党组副书记、副主席周建琨严重违纪违法被开除党籍和公职"
    # Example: "中国石油天然气集团有限公司原党组副书记、副总经理徐文荣接受中央纪委国家监委审查调查"
    
    keywords = ["接受", "涉嫌", "严重", "被"]
    
    split_point = len(title)
    for kw in keywords:
        idx = title.find(kw)
        if idx != -1 and idx < split_point:
            split_point = idx
            
    relevant_part = title[:split_point]
    
    # Further heuristic: Name is usually at the end of the relevant part, 2-4 chars.
    # But often it's "Position + Name"
    # We can't perfectly separate without NLP, but we can try a regex for the name at the end.
    
    # Try to find a name pattern (2-4 Chinese chars) at the end of the string
    # This is a naive meaningful split.
    # Ideally: use Jieba or similar NLP. But user asked for simple regex/split.
    
    # Regex for name at the end of the string (assuming name is 2-4 chars)
    # Most names are 2 or 3 chars. Rare 4.
    
    # Strategy: Assume content before keyword is "Position + Name".
    # We leave it as one field "Person/Position" if we can't separate, 
    # OR we try to split by known titles... which is hard.
    
    # Let's try to extract the last 2-3 characters as name if they look like a name, everything before as position.
    
    if len(relevant_part) <= 4:
        # It's probably just the name
        return relevant_part, ""
    
    # Simple heuristic: last 3 chars as name if specific keywords not present
    # This is a very rough approximation without NLP
    name = relevant_part[-3:]
    position = relevant_part[:-3]
    
    return name, position

def save_to_excel(data_list, filepath):
    """
    Save list of dicts to Excel.
    """
    if not data_list:
        return
    
    df = pd.DataFrame(data_list)
    # Reorder columns
    cols = ["name", "position", "title", "publish_time", "source", "url", "content"]
    # Filter only existing cols
    cols = [c for c in cols if c in df.columns]
    
    df = df[cols + [c for c in df.columns if c not in cols]]
    
    df.to_excel(filepath, index=False)
