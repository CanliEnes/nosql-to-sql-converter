"""
Modül 3 + 4: Dinamik Veritabanı Motoru & SQL Yürütme Modülü
─────────────────────────────────────────────────────────────
• SQLite bağlantısı yönetimi
• Dinamik CREATE TABLE (tablo/sütun adları hardcoded değil, runtime üretiliyor)
• Primary Key & Foreign Key otomatik atama
• INSERT INTO
• Tablo listeleme & sorgulama (raporlama için)
"""

import sqlite3
from typing import Optional


class DatabaseEngine:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    # ─── Schema ───────────────────────────────────────────────────

    def create_table(self,
                     table_name: str,
                     columns: dict,          # {col_name: sql_type}
                     foreign_key: Optional[tuple] = None,  # (fk_col, ref_table, ref_col)
                     ) -> str:
        """
        Dinamik olarak CREATE TABLE sorgusu üretir ve çalıştırır.
        Otomatik olarak 'id' PRIMARY KEY eklenir.
        Döndürülen değer: üretilen SQL dizesi (loglama / rapor için).
        """
        col_defs = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]

        reserved = {"id"}
        if foreign_key:
            fk_col, ref_table, ref_col = foreign_key
            col_defs.append(f"{fk_col} INTEGER")
            reserved.add(fk_col)

        for col, sql_type in columns.items():
            if col in reserved:
                continue
            col_defs.append(f'"{col}" {sql_type}')

        fk_clause = ""
        if foreign_key:
            fk_col, ref_table, ref_col = foreign_key
            fk_clause = f",\n  FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col})"

        sql = (
            f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
            f"  {','.join(col_defs)}"
            f"{fk_clause}\n);"
        )
        self.conn.execute(sql)
        self.conn.commit()
        return sql

    def drop_all_tables(self):
        """Sıfırlama butonu için tüm tabloları sil."""
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in cursor.fetchall()]
        # FK kısıtı nedeniyle tersten sil
        self.conn.execute("PRAGMA foreign_keys = OFF")
        for t in reversed(tables):
            self.conn.execute(f"DROP TABLE IF EXISTS {t}")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    # ─── Data ─────────────────────────────────────────────────────

    def insert(self, table_name: str, data: dict) -> int:
        """
        Dinamik INSERT INTO. data = {col: value}.
        Son eklenen satırın id'sini döndürür.
        """
        if not data:
            # Sadece id sütunu olan tablo (nadiren)
            cursor = self.conn.execute(f"INSERT INTO {table_name} DEFAULT VALUES")
            self.conn.commit()
            return cursor.lastrowid

        cols = ", ".join(f'"{k}"' for k in data)
        placeholders = ", ".join("?" for _ in data)
        sql = f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders})"
        cursor = self.conn.execute(sql, list(data.values()))
        self.conn.commit()
        return cursor.lastrowid

    # ─── Query ────────────────────────────────────────────────────

    def list_tables(self) -> list[str]:
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [r[0] for r in cursor.fetchall()]

    def fetch_table(self, table_name: str) -> tuple[list, list]:
        """(column_names, rows) döndürür."""
        cursor = self.conn.execute(f"SELECT * FROM {table_name}")
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return cols, rows

    def table_exists(self, table_name: str) -> bool:
        cursor = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None

    def get_table_relations(self, table_name: str) -> list[dict]:
        """
        Tablonun yabancı anahtar (Foreign Key) ilişkilerini döner.
        [{'from': local_col, 'to_table': foreign_table, 'to': foreign_col}]
        """
        cursor = self.conn.execute(f"PRAGMA foreign_key_list({table_name})")
        relations = []
        for row in cursor.fetchall():
            # row: (id, seq, table, from, to, on_update, on_delete, match)
            relations.append({
                "from": row[3],
                "to_table": row[2],
                "to": row[4]
            })
        return relations

    def get_table_row_count(self, table_name: str) -> int:
        """Tablodaki toplam satır sayısını döner."""
        cursor = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def close(self):
        self.conn.close()