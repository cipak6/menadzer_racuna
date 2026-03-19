"""
Manages the local invoice image index.
Copies images to an organized folder structure and records metadata in SQLite.
"""

import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


class InvoiceIndex:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.images_dir = self.base_dir / 'invoice_images'
        self.db_path = self.base_dir / 'invoices.db'
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS invoices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    company_tin TEXT,
                    company_details TEXT,
                    company_name TEXT,
                    store_name TEXT,
                    store_address TEXT,
                    store_place TEXT,
                    store_municipality TEXT,
                    total_price REAL,
                    total_vat REAL,
                    pfr_number TEXT,
                    url TEXT UNIQUE,
                    image_path TEXT,
                    added_at TEXT
                )
            ''')
            conn.execute('''
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    invoice_id INTEGER,
                    name TEXT,
                    unit TEXT,
                    quantity REAL,
                    price REAL,
                    total REAL,
                    vat TEXT,
                    FOREIGN KEY (invoice_id) REFERENCES invoices(id)
                )
            ''')

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def _target_image_path(self, date_str: str, total_price, base_filename: str) -> Path:
        folder = self.images_dir
        folder.mkdir(parents=True, exist_ok=True)

        try:
            date_part = date_str.split(' ')[0].split('T')[0]
            date_compact = date_part.replace('-', '')
            amount = f"{float(total_price or 0):.2f}".replace('.', '_')
            base = f"{date_compact}_{amount}"
        except Exception:
            base = Path(base_filename).stem

        ext = Path(base_filename).suffix or '.png'
        candidate = folder / f"{base}{ext}"
        counter = 1
        while candidate.exists():
            candidate = folder / f"{base}_{counter}{ext}"
            counter += 1
        return candidate

    def exists(self, url: str) -> bool:
        with self._conn() as conn:
            row = conn.execute('SELECT id FROM invoices WHERE url = ?', (url,)).fetchone()
            return row is not None

    def add(self, invoice: dict, source_image_path: str = None) -> dict:
        """
        Adds invoice to index, copies image to organized folder.
        Returns {'id': int, 'duplicate': bool, 'image_dest': str}
        """
        url = invoice.get('url', '')
        if self.exists(url):
            return {'id': None, 'duplicate': True, 'image_dest': None}

        image_dest = None
        image_filename = ''

        # Always render receipt as image from pre_text
        if invoice.get('pre_text'):
            try:
                from core.receipt_image import render_receipt_image
                date_str = invoice.get('date', 'unknown').replace('-', '')
                pfr = invoice.get('pfr_number', 'nopfr').replace('/', '-')
                prefix = f"{date_str}_{pfr}"
                dest_path = self._target_image_path(invoice.get('date', ''), invoice.get('total_price', 0), 'receipt.png')
                rendered = render_receipt_image(
                    invoice['pre_text'],
                    str(dest_path.parent),
                    filename_prefix=dest_path.stem
                )
                image_dest = rendered
                image_filename = str(Path(rendered).relative_to(self.base_dir))
            except Exception as e:
                print(f"Receipt render failed: {e}")

            from core.receipt_image import add_qr_to_receipt
            add_qr_to_receipt(rendered, invoice.get('url', ''))
        
        elif source_image_path and os.path.exists(source_image_path):
            try:
                dest_path = self._target_image_path(
                    invoice.get('date', ''),
                    invoice.get('total_price', 0),
                    os.path.basename(source_image_path)
                )
                shutil.copy2(source_image_path, dest_path)
                image_dest = str(dest_path)
                image_filename = str(dest_path.relative_to(self.base_dir))
            except Exception as e:
                print(f"Image copy failed: {e}")

        with self._conn() as conn:
            cursor = conn.execute('''
                INSERT INTO invoices
                    (date,company_tin, company_details, company_name, store_name, store_address, store_place,
                    store_municipality, total_price, total_vat, pfr_number, url, image_path, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice.get('date'),
                invoice.get('company_tin'),
                invoice.get('company_details', ''),
                invoice.get('company_name'),
                invoice.get('store_name'),
                invoice.get('store_address'),
                invoice.get('store_place'),
                invoice.get('store_municipality'),
                invoice.get('total_price'),
                invoice.get('total_vat'),
                invoice.get('pfr_number'),
                url,
                image_dest,
                datetime.now().isoformat(),
            ))
            invoice_id = cursor.lastrowid

            for item in invoice.get('items', []):
                conn.execute('''
                    INSERT INTO items (invoice_id, name, unit, quantity, price, total, vat)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    invoice_id,
                    item.get('name'),
                    item.get('unit'),
                    item.get('quantity'),
                    item.get('price'),
                    item.get('total'),
                    item.get('vat'),
                ))

        return {'id': invoice_id, 'duplicate': False, 'image_dest': image_dest, 'image_filename': image_filename}

    def search(self, query: str = '', date_from: str = None, date_to: str = None) -> list:
        sql = 'SELECT * FROM invoices WHERE 1=1'
        params = []
        if query:
            sql += ' AND (company_name LIKE ? OR store_name LIKE ? OR store_place LIKE ?)'
            q = f'%{query}%'
            params += [q, q, q]
        if date_from:
            sql += ' AND date >= ?'
            params.append(date_from)
        if date_to:
            sql += ' AND date <= ?'
            params.append(date_to)
        sql += ' ORDER BY date DESC'
        with self._conn() as conn:
            cursor = conn.execute(sql, params)
            cols = [d[0] for d in cursor.description]
            rows = cursor.fetchall()
        return [dict(zip(cols, row)) for row in rows]

    def get_items(self, invoice_id: int) -> list:
        with self._conn() as conn:
            rows = conn.execute('SELECT * FROM items WHERE invoice_id = ?', (invoice_id,)).fetchall()
            cols = [d[0] for d in conn.execute('SELECT * FROM items LIMIT 0').description]
        return [dict(zip(cols, row)) for row in rows]

    def get_all(self) -> list:
        return self.search()

    def delete(self, invoice_id: int):
        with self._conn() as conn:
            row = conn.execute('SELECT image_path FROM invoices WHERE id = ?', (invoice_id,)).fetchone()
            if row and row[0] and os.path.exists(row[0]):
                os.remove(row[0])
            conn.execute('DELETE FROM items WHERE invoice_id = ?', (invoice_id,))
            conn.execute('DELETE FROM invoices WHERE id = ?', (invoice_id,))

    def stats(self) -> dict:
        with self._conn() as conn:
            total = conn.execute('SELECT COUNT(*), SUM(total_price), SUM(total_vat) FROM invoices').fetchone()
        return {
            'count': total[0] or 0,
            'total_spent': total[1] or 0.0,
            'total_vat': total[2] or 0.0,
        }
    def update_company_details(self, invoice_id: int, company_details: str):
        with self._conn() as conn:
            conn.execute('UPDATE invoices SET company_details = ? WHERE id = ?', 
                        (company_details, invoice_id))
