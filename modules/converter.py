"""
Dönüştürücü Motor (Converter Engine)
──────────────────────────────────────
Projenin kalbi. JSONParser + DatabaseEngine modüllerini birleştirerek
rekursif dönüşümü yönetir.

Algoritma (1NF → 2NF → 3NF):
  1. Veriyi JSONParser ile düzleştir.
  2. Bulunan düz sütunlar için CREATE TABLE yap.
  3. Bulunan her array için:
       a. Alt tablo adı = üst_tablo + "_" + dizi_anahtarı
       b. parent_id Foreign Key ile alt tablo oluştur.
       c. Dizi elemanlarını recursive olarak işle.
  4. Verinin satırlarını INSERT INTO ile yaz.
"""

from __future__ import annotations
from typing import Any, Callable, Optional

from .parser import JSONParser
from .db_engine import DatabaseEngine


class ConverterEngine:
    def __init__(self, db_engine: DatabaseEngine):
        self.db = db_engine
        self.parser = JSONParser()
        self._created_tables: set[str] = set()

    # ─── Public ───────────────────────────────────────────────────

    def convert(self,
                data: Any,
                table_name: str,
                parent_fk: Optional[tuple] = None,   # (fk_col_name, parent_id)
                log_fn: Callable = print,
                schema_collector: Optional[list] = None):
        """
        data       : JSON nesnesi (dict, list ya da skaler)
        table_name : oluşturulacak/kullanılacak SQL tablosunun adı
        parent_fk  : üst tablodan gelen (fk_sütun_adı, üst_id) bilgisi
        """
        # Kök liste ise her elemanı ayrı satır say
        if isinstance(data, list):
            for item in data:
                self.convert(item, table_name, parent_fk, log_fn, schema_collector)
            return

        if not isinstance(data, dict):
            # Skaler liste elemanı → value sütununa yaz
            data = {"value": data}

        flat = self.parser.parse(data)

        # ── Tablo oluştur (ilk kez) ──────────────────────────────
        fk_def = None
        fk_col_name = None
        if parent_fk:
            fk_col_name, _ = parent_fk
            parent_table = fk_col_name.replace("_id", "")
            fk_def = (fk_col_name, parent_table, "id")

        if table_name not in self._created_tables:
            sql = self.db.create_table(table_name, flat.columns, foreign_key=fk_def)
            self._created_tables.add(table_name)
            log_fn(f"[CREATE] {table_name}  sütunlar: {list(flat.columns.keys())}")
            if schema_collector is not None:
                schema_collector.append(f"-- Tablo: {table_name}\n{sql}")
        else:
            # Tablo zaten var: yeni sütunlar eklenebilir (ALTER TABLE)
            self._ensure_columns(table_name, flat.columns, log_fn)

        # ── Satır yaz ────────────────────────────────────────────
        row_data = dict(flat.columns)            # şema için type bilgisi değil, değerleri alalım
        row_data = self._extract_flat_values(data)

        if parent_fk:
            fk_col_name, parent_id = parent_fk
            row_data[fk_col_name] = parent_id

        inserted_id = self.db.insert(table_name, row_data)
        log_fn(f"[INSERT] {table_name} id={inserted_id}  data={row_data}")

        # ── Alt tablolar (diziler) ────────────────────────────────
        for array_key, items in flat.arrays.items():
            child_table = f"{table_name}_{array_key}"
            child_fk_col = f"{table_name}_id"
            log_fn(f"[ARRAY ] '{array_key}' → alt tablo: {child_table}")
            for item in items:
                self.convert(
                    item,
                    child_table,
                    parent_fk=(child_fk_col, inserted_id),
                    log_fn=log_fn,
                    schema_collector=schema_collector,
                )

    # ─── Helpers ─────────────────────────────────────────────────

    def _extract_flat_values(self, data: dict, prefix: str = "") -> dict:
        """
        Nested dict'i düzleştirip değerleriyle birlikte döndürür.
        (Parser sütun tiplerini, bu metod gerçek değerleri çıkarır.)
        """
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}_{key}" if prefix else key
            full_key = full_key.replace("-", "_").replace(" ", "_").replace(".", "_").lower()
            if full_key and full_key[0].isdigit():
                full_key = "_" + full_key

            if isinstance(value, dict):
                nested = self._extract_flat_values(value, full_key)
                result.update(nested)
            elif isinstance(value, list):
                pass   # diziler ayrı tabloya gidecek
            elif isinstance(value, bool):
                result[full_key] = int(value)
            else:
                result[full_key] = value
        return result

    def _ensure_columns(self, table_name: str, columns: dict, log_fn: Callable):
        """
        Farklı yapıda JSON geldiğinde eksik sütunları ALTER TABLE ile ekler.
        (Örn: array elemanları heterojen ise)
        """
        existing_cols_query = self.db.conn.execute(
            f"PRAGMA table_info({table_name})"
        )
        existing = {row[1] for row in existing_cols_query.fetchall()}

        for col, sql_type in columns.items():
            if col not in existing:
                try:
                    self.db.conn.execute(
                        f'ALTER TABLE {table_name} ADD COLUMN "{col}" {sql_type}'
                    )
                    self.db.conn.commit()
                    log_fn(f"[ALTER ] {table_name} + sütun: {col} ({sql_type})")
                except Exception as e:
                    log_fn(f"[WARN  ] ALTER başarısız {table_name}.{col}: {e}")