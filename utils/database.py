import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os


class RentalDatabase:
    """SQLite database for storing rental property listings"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to data/rentals.db
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "rentals.db")

        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        self.cursor = self.conn.cursor()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS rentals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                address TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                rent_eur REAL,
                rent_period TEXT,
                original_rent REAL,
                summary TEXT,
                beds INTEGER,
                baths INTEGER,
                furnished TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create index on URL for faster duplicate checking
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_url ON rentals(url)
        ''')

        # Create index on source for filtering
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_source ON rentals(source)
        ''')

        self.conn.commit()

    def insert_listing(self, listing: Dict) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO rentals
                (source, address, url, rent_eur, rent_period, original_rent,
                 summary, beds, baths, furnished)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                listing.get('source'),
                listing.get('address'),
                listing.get('url'),
                listing.get('rent_eur'),
                listing.get('rent_period', 'monthly'),
                listing.get('original_rent', listing.get('rent_eur')),
                listing.get('summary'),
                listing.get('beds'),
                listing.get('baths'),
                listing.get('furnished')
            ))
            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            # URL already exists - update instead
            self._update_listing(listing)
            return False

    def _update_listing(self, listing: Dict):
        """Update existing listing with new data"""
        self.cursor.execute('''
            UPDATE rentals
            SET source = ?, address = ?, rent_eur = ?, rent_period = ?,
                original_rent = ?, summary = ?, beds = ?, baths = ?,
                furnished = ?, updated_at = CURRENT_TIMESTAMP
            WHERE url = ?
        ''', (
            listing.get('source'),
            listing.get('address'),
            listing.get('rent_eur'),
            listing.get('rent_period', 'monthly'),
            listing.get('original_rent', listing.get('rent_eur')),
            listing.get('summary'),
            listing.get('beds'),
            listing.get('baths'),
            listing.get('furnished'),
            listing.get('url')
        ))
        self.conn.commit()

    def insert_many(self, listings: List[Dict]) -> tuple:
        """
        Insert multiple listings into the database.

        Returns:
            tuple: (inserted_count, updated_count)
        """
        inserted = 0
        updated = 0

        for listing in listings:
            if self.insert_listing(listing):
                inserted += 1
            else:
                updated += 1

        return inserted, updated

    def get_all_listings(self) -> List[Dict]:
        """Retrieve all listings from the database"""
        self.cursor.execute('''
            SELECT source, address, url, rent_eur, rent_period, original_rent,
                   summary, beds, baths, furnished, scraped_at, updated_at
            FROM rentals
            ORDER BY scraped_at DESC
        ''')

        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_listings_by_source(self, source: str) -> List[Dict]:
        """Retrieve listings from a specific source"""
        self.cursor.execute('''
            SELECT source, address, url, rent_eur, rent_period, original_rent,
                   summary, beds, baths, furnished, scraped_at, updated_at
            FROM rentals
            WHERE source = ?
            ORDER BY scraped_at DESC
        ''', (source,))

        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_stats(self) -> Dict:
        """Get database statistics"""
        self.cursor.execute('SELECT COUNT(*) as total FROM rentals')
        total = self.cursor.fetchone()['total']

        self.cursor.execute('''
            SELECT source, COUNT(*) as count
            FROM rentals
            GROUP BY source
        ''')
        by_source = {row['source']: row['count'] for row in self.cursor.fetchall()}

        self.cursor.execute('''
            SELECT
                COUNT(CASE WHEN rent_period = 'weekly' THEN 1 END) as weekly_count,
                COUNT(CASE WHEN rent_period = 'monthly' THEN 1 END) as monthly_count
            FROM rentals
        ''')
        periods = self.cursor.fetchone()

        return {
            'total': total,
            'by_source': by_source,
            'weekly_converted': periods['weekly_count'],
            'monthly_original': periods['monthly_count']
        }

    def clear_all(self):
        """Clear all listings from the database"""
        self.cursor.execute('DELETE FROM rentals')
        self.conn.commit()

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
