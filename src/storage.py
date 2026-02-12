import sqlite3
import pandas as pd
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class Storage:
    def __init__(self, db_path="data/ccdi.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database and table."""
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path))
            
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Create table
        c.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                url TEXT PRIMARY KEY,
                title TEXT,
                name TEXT,
                position TEXT,
                category TEXT,
                subcategory TEXT,
                publish_time TEXT,
                source TEXT,
                content TEXT,
                scraped_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def is_scraped(self, url):
        """Check if URL has already been scraped."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        result = c.fetchone()
        conn.close()
        return result is not None

    def save_article(self, data):
        """Save a single article to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''
                INSERT OR REPLACE INTO articles (
                    url, title, name, position, category, subcategory, 
                    publish_time, source, content, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get("url"),
                data.get("title"),
                data.get("name"),
                data.get("position"),
                data.get("category"),
                data.get("subcategory"),
                data.get("publish_time"),
                data.get("source"),
                data.get("content"),
                datetime.now()
            ))
            conn.commit()
            # logger.info(f"Saved: {data.get('title')}")
        except Exception as e:
            logger.error(f"Error saving to DB: {e}")
        finally:
            conn.close()

    def export_to_excel(self, filepath):
        """Export database to Excel."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql_query("SELECT * FROM articles", conn)
        conn.close()
        
        if not df.empty:
            df.to_excel(filepath, index=False)
            logger.info(f"Exported {len(df)} records to {filepath}")
        else:
            logger.info("Database empty, nothing to export.")
