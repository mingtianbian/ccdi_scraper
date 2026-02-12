# src/config.py

BASE_URL = "https://www.ccdi.gov.cn"

# Category Mapping
CATEGORIES = {
    "中管干部": {
        "执纪审查": "https://www.ccdi.gov.cn/scdcn/zggb/zjsc/",
        "党纪政务处分": "https://www.ccdi.gov.cn/scdcn/zggb/djcf/"
    },
    "中央一级党和国家机关、国企和金融单位干部": {
        "执纪审查": "https://www.ccdi.gov.cn/scdcn/zyyj/zjsc/",
        "党纪政务处分": "https://www.ccdi.gov.cn/scdcn/zyyj/djcf/"
    },
    "省管干部": {
        "执纪审查": "https://www.ccdi.gov.cn/scdcn/sggb/zjsc/",
        "党纪政务处分": "https://www.ccdi.gov.cn/scdcn/sggb/djcf/"
    }
}

# Scraper Settings
HEADLESS = False  # Keep browser visible for manual intervention
TIMEOUT = 30000   # 30 seconds
RANDOM_DELAY_MIN = 2
RANDOM_DELAY_MAX = 5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

# Output
OUTPUT_DIR = "data"
OUTPUT_FILENAME_FORMAT = "ccdi_data_{timestamp}.xlsx"
