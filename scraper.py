#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import hashlib
import os
import random
import re
import sqlite3
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup

# Choose the best available parser (no crash if lxml missing)
try:
    import lxml  # noqa: F401
    _BS_PARSER = "lxml"
except Exception:
    try:
        import html5lib  # noqa: F401
        _BS_PARSER = "html5lib"
    except Exception:
        _BS_PARSER = "html.parser"

DB_PATH = os.environ.get("CCDI_DB", "ccdi.sqlite3")
EXPORT_DIR = os.environ.get("CCDI_EXPORT_DIR", "export")
os.makedirs(EXPORT_DIR, exist_ok=True)

HEADERS_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36",
]

BASE = "https://www.ccdi.gov.cn"
CATEGORIES = [
    ("中管干部>执纪审查", "中管干部", "执纪审查", "https://www.ccdi.gov.cn/scdcn/zggb/zjsc/"),
    ("中管干部>党纪政务处分", "中管干部", "党纪政务处分", "https://www.ccdi.gov.cn/scdcn/zggb/djcf/"),
    ("中央一级>执纪审查", "中央一级", "执纪审查", "https://www.ccdi.gov.cn/scdcn/zyyj/zjsc/"),
    ("中央一级>党纪政务处分", "中央一级", "党纪政务处分", "https://www.ccdi.gov.cn/scdcn/zyyj/djcf/"),
    ("省管干部>执纪审查", "省管干部", "执纪审查", "https://www.ccdi.gov.cn/scdcn/sggb/zjsc/"),
    ("省管干部>党纪政务处分", "省管干部", "党纪政务处分", "https://www.ccdi.gov.cn/scdcn/sggb/djcf/"),
]

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
})

def pick_headers() -> Dict[str, str]:
    h = dict(SESSION.headers)
    h["User-Agent"] = random.choice(HEADERS_POOL)
    return h

def md5_text(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def request_html(url: str, retry: int = 3, timeout: int = 20) -> Optional[str]:
    for attempt in range(1, retry + 1):
        try:
            headers = pick_headers()
            headers["Referer"] = url.rsplit("/", 1)[0] + "/"
            headers["Cache-Control"] = "no-cache"
            resp = SESSION.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", "text/html"):
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            if resp.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(0.8 * attempt + random.random() * 0.8)
    return None

def clean_text(s: str) -> str:
    s = re.sub(r"\r|\t|\xa0", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def detect_total_pages(first_page_html: str) -> int:
    m = re.search(r'createPageHTML\(\s*(\d+)\s*,', first_page_html, flags=re.I)
    if m:
        total = int(m.group(1))
        if total >= 1:
            return total
    soup = BeautifulSoup(first_page_html, _BS_PARSER)
    a_last = soup.select_one("a.first[title*='末'], a.last[title*='末'], a[title*='末页']")
    if a_last and a_last.get("href"):
        m2 = re.search(r'index_(\d+)\.html', a_last["href"])
        if m2:
            return int(m2.group(1)) + 1
    return 200

def iter_list_pages(list_url: str, max_pages: int) -> List[str]:
    first_candidates = [list_url.rstrip('/') + '/index.html', list_url.rstrip('/') + '/']
    first_html = None
    first_url = None
    for u in first_candidates:
        html = request_html(u)
        if html:
            first_html = html
            first_url = u
            break
    if not first_html:
        return []
    total = detect_total_pages(first_html)
    if max_pages:
        total = min(total, max_pages)
    pages = [first_url]
    base = list_url.rstrip('/')
    for i in range(1, total):
        pages.append(f"{base}/index_{i}.html")
    return pages

def parse_list(html: str, page_url: str) -> List[Tuple[str, Optional[str], Optional[str]]]:
    soup = BeautifulSoup(html, _BS_PARSER)
    def norm_url(href: str) -> str:
        return urljoin(page_url, href)
    out: List[Tuple[str, Optional[str], Optional[str]]] = []

    for sel in ["ul.list_news_dl2.fixed > li", "ul.list_news_dl2 > li", "ul.list_news_dl > li", "ul.list > li", "ul.list_news > li"]:
        lis = soup.select(sel)
        if lis:
            for li in lis:
                a = li.find("a", href=True)
                if not a: 
                    continue
                href = a["href"]
                title = clean_text(a.get_text())
                date_text = None
                more = li.select_one(".more")
                if more:
                    m = re.search(r"(20\d{2}-\d{1,2}-\d{1,2})", more.get_text(" ", strip=True))
                    if m:
                        date_text = m.group(1)
                out.append((norm_url(href), title, date_text))
            if out:
                break

    if not out:
        mblock = re.search(r"<ul[^>]*class=['\"]list_news_dl2[^>]*>([\s\S]*?)</ul>", html, flags=re.I)
        if mblock:
            block = mblock.group(1)
            for m in re.finditer(r"<a[^>]+href=['\"]([^'\"]+\.html)['\"][^>]*>([\s\S]*?)</a>[\s\S]*?(20\d{2}-\d{1,2}-\d{1,2})", block, flags=re.I):
                href = m.group(1)
                title = clean_text(re.sub(r"<[^>]+>", "", m.group(2)))
                date_text = m.group(3)
                out.append((norm_url(href), title, date_text))

    if not out:
        anchors = soup.find_all("a", href=True)
        for a in anchors:
            href = a["href"]
            if href.endswith(".html"):
                title = clean_text(a.get_text())
                date_text = None
                par = a.parent
                if par:
                    s = " ".join(el.get_text(" ", strip=True) for el in par.find_all(["span","em","i","div"], recursive=False))
                    m = re.search(r"(20\d{2}[-/年]\d{1,2}[-/月]\d{1,2})", s)
                    if m:
                        date_text = m.group(1).replace("年","-").replace("月","-").replace("日","")
                out.append((norm_url(href), title, date_text))

    seen = set()
    final = []
    for u, t, d in out:
        if "ccdi.gov.cn" in u and u.endswith(".html") and u not in seen:
            seen.add(u)
            final.append((u, t, d))
    return final

def parse_detail(html: str) -> Tuple[str, str, str, str]:
    soup = BeautifulSoup(html, _BS_PARSER)
    title = ""
    for sel in ["h1", "h2", ".tit", ".title", ".article-title", "h3"]:
        el = soup.select_one(sel)
        if el and clean_text(el.get_text()):
            title = clean_text(el.get_text())
            break
    if not title:
        title = clean_text(soup.title.get_text()) if soup.title else ""

    published = ""
    source = ""
    meta_pub = soup.select_one('meta[name="PubDate"]')
    if meta_pub and meta_pub.get("content"):
        published = clean_text(meta_pub["content"]).replace("年","-").replace("月","-").replace("日","")
    meta_src = soup.select_one('meta[name="ContentSource"]')
    if meta_src and meta_src.get("content"):
        source = clean_text(meta_src["content"])

    if not source:
        el = soup.select_one(".daty_con .e.e1, .source, .xxgk-source, .info .source")
        if el:
            txt = clean_text(el.get_text()).replace("来源：", "")
            source = clean_text(txt)
    if not published:
        el = soup.select_one(".daty_con .e.e2, .time, .pubtime, .xxgk-time, .info")
        if el:
            txt = clean_text(el.get_text())
            m = re.search(r"(\d{4})[-年/](\d{1,2})[-月/](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?", txt)
            if m:
                yyyy, mm, dd, hh, mi = m.groups()
                if hh and mi:
                    published = f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d} {int(hh):02d}:{int(mi):02d}"
                else:
                    published = f"{int(yyyy):04d}-{int(mm):02d}-{int(dd):02d}"

    body_parts = []
    container = None
    for sel in ["#content", ".content", ".article", ".xxgk-content", ".TRS_Editor", ".article-content", ".con", ".Article_61 .content"]:
        el = soup.select_one(sel)
        if el:
            container = el
            break
    if container:
        for p in container.find_all(["p","div"]):
            t = clean_text(p.get_text())
            if t:
                body_parts.append(t)
    else:
        for p in soup.find_all("p"):
            t = clean_text(p.get_text())
            if t:
                body_parts.append(t)
    body = "\n".join(body_parts)
    return title, published, source, body

def extract_name_position(title: str) -> Tuple[Optional[str], Optional[str]]:
    m = re.search(r"^(?P<position>.+?)(?P<name>[\u4e00-\u9fa5·]{2,6})接受", title)
    if m:
        return m.group("name"), clean_text(m.group("position"))
    m = re.search(r"^(?P<name>[\u4e00-\u9fa5·]{2,6})(?P<position>.+?)(?:被|接受)", title)
    if m:
        return m.group("name"), clean_text(m.group("position"))
    return None, None

PROVINCE_LIST = [
    "北京","天津","上海","重庆","河北","山西","辽宁","吉林","黑龙江","江苏","浙江","安徽","福建","江西","山东","河南",
    "湖北","湖南","广东","海南","四川","贵州","云南","陕西","甘肃","青海","台湾",
    "内蒙古","广西","西藏","宁夏","新疆","香港","澳门"
]

def extract_regions(title: str, body: str) -> List[str]:
    text = title + "\n" + body
    found, seen = [], set()
    for prov in PROVINCE_LIST:
        if prov in text and prov not in seen:
            seen.add(prov)
            found.append(prov)
    return found

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS records (
          url TEXT PRIMARY KEY,
          category_label TEXT,
          level TEXT,
          type TEXT,
          title TEXT,
          published TEXT,
          source TEXT,
          position TEXT,
          names TEXT,
          regions TEXT,
          body TEXT,
          raw_html TEXT,
          md5 TEXT,
          first_seen TEXT,
          last_seen TEXT
        )
    ''')
    conn.commit()
    c.execute("PRAGMA table_info(records)")
    cols = {row[1] for row in c.fetchall()}
    if "position" not in cols:
        c.execute("ALTER TABLE records ADD COLUMN position TEXT")
    if "raw_html" not in cols:
        c.execute("ALTER TABLE records ADD COLUMN raw_html TEXT")
    if "source" not in cols:
        c.execute("ALTER TABLE records ADD COLUMN source TEXT")
    conn.commit()
    conn.close()

def upsert_record(conn, rec: Dict):
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    c.execute("SELECT md5 FROM records WHERE url=?", (rec["url"],))
    row = c.fetchone()
    if row is None:
        c.execute("""
            INSERT INTO records (url, category_label, level, type, title, published, source, position, names, regions, body, raw_html, md5, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (rec["url"], rec["category_label"], rec["level"], rec["type"], rec["title"], rec["published"],
              rec.get("source",""), rec.get("position",""), ",".join(rec["names"]), ",".join(rec["regions"]),
              rec["body"], rec.get("raw_html",""), rec["md5"], now, now))
        conn.commit()
        return "inserted"
    else:
        old_md5 = row[0]
        if old_md5 != rec["md5"]:
            c.execute("""
                UPDATE records
                SET category_label=?, level=?, type=?, title=?, published=?, source=?, position=?, names=?, regions=?, body=?, raw_html=?, md5=?, last_seen=?
                WHERE url=?
            """, (rec["category_label"], rec["level"], rec["type"], rec["title"], rec["published"],
                  rec.get("source",""), rec.get("position",""), ",".join(rec["names"]), ",".join(rec["regions"]),
                  rec["body"], rec.get("raw_html",""), rec["md5"], now, rec["url"]))
            conn.commit()
            return "updated"
        else:
            c.execute("UPDATE records SET last_seen=? WHERE url=?", (now, rec["url"])),
            conn.commit()
            return "unchanged"

def _bar_line(prefix: str, done: int, total: int, width: int = 30) -> str:
    done = max(0, min(done, total))
    pct = (done / total) if total else 0.0
    filled = int(width * pct)
    bar = "#" * filled + "-" * (width - filled)
    return f"{prefix} [{bar}] {done}/{total} ({int(pct*100)}%)"

def crawl_category(label: str, level: str, typ: str, list_url: str, max_pages: int, show_progress: bool=False):
    pages = iter_list_pages(list_url, max_pages)
    if not pages:
        print(f"[WARN] No list pages found for {label}: {list_url}")
        return

    os.makedirs("debug", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    new_count = upd_count = unchanged = 0
    total_pages = len(pages)

    for idx, page_url in enumerate(pages, 1):
        html = None
        for _try in range(3):
            html = request_html(page_url)
            if html:
                break
            time.sleep(0.6 + random.random()*0.6)
        if not html:
            print(f"[END] Stop at missing page: {page_url}")
            break

        items = parse_list(html, page_url)

        if not items:
            with open(os.path.join("debug", f"page_{idx}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            for _retry in range(2):
                time.sleep(1.0 + random.random()*1.0)
                html2 = request_html(page_url)
                if html2:
                    items = parse_list(html2, page_url)
                    if items:
                        html = html2
                        break

        if not items:
            print(f"[WARN] No items on page {idx}: {page_url}. Continue...")
            time.sleep(1.0 + random.random()*0.8)
            continue

        total_items = len(items)
        if show_progress:
            print(_bar_line("条目", 0, total_items))
            print(_bar_line("页数", idx-1, total_pages))

        cur_item = 0
        for detail_url, title_guess, date_guess in items:
            cur_item += 1
            if show_progress:
                print("\r" + _bar_line("条目", cur_item, total_items), end="", flush=True)

            dhtml = request_html(detail_url, retry=3, timeout=20)
            if not dhtml:
                if show_progress: print()
                print(f"  [SKIP] 404/ERR detail: {detail_url}")
                continue

            title, published, site_source, body = parse_detail(dhtml)
            if not published and date_guess:
                published = date_guess
            body_clean = clean_text(body)

            name, position = extract_name_position(title)
            names = [name] if name else []
            regions = extract_regions(title, body_clean)
            md5 = md5_text("|".join([title, published or "", site_source or "", position or "", body_clean]))

            rec = {
                "url": detail_url,
                "category_label": label,
                "level": level,
                "type": typ,
                "title": title or (title_guess or ""),
                "published": published or "",
                "source": site_source or "",
                "position": position or "",
                "names": names,
                "regions": regions,
                "body": body_clean,
                "raw_html": dhtml,
                "md5": md5,
            }
            status = upsert_record(conn, rec)
            if status == "inserted":
                new_count += 1
            elif status == "updated":
                upd_count += 1
            else:
                unchanged += 1

            time.sleep(0.45 + random.random()*0.55)

        if show_progress:
            print()
            print(_bar_line("页数", idx, total_pages))

        time.sleep(1.0 + random.random()*1.2)

    conn.close()
    print(f"[DONE] {label} -> new:{new_count} updated:{upd_count} unchanged:{unchanged}")

def export_records(fmt: str):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("""
        SELECT
            category_label as 来源分类,
            level as 层级,
            type as 类型,
            title as 标题,
            source as 来源,
            position as 职务,
            published as 发布时间,
            names as 姓名,
            regions as 地区,
            url as 原文链接,
            first_seen as 首次抓取,
            last_seen as 最近刷新
        FROM records
        ORDER BY 发布时间 DESC, 最近刷新 DESC
    """, conn)
    conn.close()
    if fmt.lower() == "csv":
        path = os.path.join(EXPORT_DIR, f"ccdi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        df.to_csv(path, index=False, encoding="utf-8-sig")
    elif fmt.lower() in ("xlsx", "excel"):
        path = os.path.join(EXPORT_DIR, f"ccdi_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="CCDI", index=False)
    else:
        raise SystemExit("Format must be csv or xlsx")
    print(f"[EXPORT] Saved to {path}")

def reparse_single(url: str):
    html = request_html(url, retry=3, timeout=20)
    if not html:
        print("[ERR] Cannot fetch URL")
        return
    title, published, site_source, body = parse_detail(html)
    body_clean = clean_text(body)
    name, position = extract_name_position(title)
    regions = extract_regions(title, body_clean)
    print("标题:", title)
    print("来源:", site_source)
    print("发布时间:", published)
    print("姓名:", name or "")
    print("职务:", position or "")
    print("地区:", ",".join(regions))

def list_categories():
    for i, (label, _level, _typ, _url) in enumerate(CATEGORIES, start=1):
        print(f"{i}. {label}")

def get_category_label_by_id(cid: int) -> str:
    if 1 <= cid <= len(CATEGORIES):
        return CATEGORIES[cid-1][0]
    raise ValueError("category id out of range")

def main():
    parser = argparse.ArgumentParser(description="CCDI six-category scraper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="crawl categories")
    p_run.add_argument("--max-pages", type=int, default=200, help="max pages per category")
    p_run.add_argument("--only", type=str, default=None, help="only crawl by label, e.g. '省管干部>执纪审查'")
    p_run.add_argument("--only-id", type=int, default=None, help="only crawl by id 1..6")

    p_export = sub.add_parser("export", help="export to CSV/Excel")
    p_export.add_argument("--format", type=str, default="csv", choices=["csv", "xlsx", "excel"])

    p_reparse = sub.add_parser("reparse", help="parse a single detail page")
    p_reparse.add_argument("--url", required=True)

    sub.add_parser("list", help="list category ids and labels")

    args = parser.parse_args()
    init_db()

    if args.cmd == "run":
        if args.only_id and not args.only:
            try:
                args.only = get_category_label_by_id(args.only_id)
            except Exception:
                print("[ERR] --only-id must be between 1 and", len(CATEGORIES))
                return
        for label, level, typ, url in CATEGORIES:
            if args.only and args.only != label:
                continue
            crawl_category(label, level, typ, url, max_pages=args.max_pages, show_progress=bool(args.only or args.only_id))
        print("[ALL DONE]")
    elif args.cmd == "export":
        export_records(args.format)
    elif args.cmd == "reparse":
        reparse_single(args.url)
    elif args.cmd == "list":
        list_categories()

if __name__ == "__main__":
    main()
