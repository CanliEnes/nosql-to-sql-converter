"""
Modül 2: Algoritmik Çözümleme (Parsing) Modülü
───────────────────────────────────────────────
• Veri tipi tespiti  (str → VARCHAR, int/float → REAL, bool → INTEGER)
• Düzleştirme        (nested obj → parent_child sütunları)
• Dizi tespiti       (array → ayrı alt tablo işaretçisi)
"""

from __future__ import annotations
from typing import Any


class JSONParser:
    """
    JSON verisini recursif olarak çözümler.

    parse(data, prefix="") → FlatResult
        FlatResult.columns : {col_name: sql_type}   düz sütunlar
        FlatResult.arrays  : {col_name: [items]}     tespit edilen diziler
    """

    SQL_TYPE_MAP = {
        str: "TEXT",
        int: "INTEGER",
        float: "REAL",
        bool: "INTEGER",   # SQLite boolean yok, 0/1 kullanılır
        type(None): "TEXT",
    }

    # ─── Public ───────────────────────────────────────────────────

    def parse(self, data: Any, prefix: str = "") -> "FlatResult":
        result = FlatResult()
        self._traverse(data, prefix, result)
        return result

    # ─── Private ──────────────────────────────────────────────────

    def _traverse(self, node: Any, prefix: str, result: "FlatResult"):
        if isinstance(node, dict):
            for key, value in node.items():
                full_key = f"{prefix}_{key}" if prefix else key
                self._traverse(value, full_key, result)

        elif isinstance(node, list):
            # Dizi → normalizasyon gerekiyor, ana tabloya yazma
            result.arrays[prefix] = node

        else:
            # Skaler değer → sütun
            sql_type = self.SQL_TYPE_MAP.get(type(node), "TEXT")
            col_name = self._sanitize(prefix)
            result.columns[col_name] = sql_type

    @staticmethod
    def _sanitize(name: str) -> str:
        """Sütun adlarını SQL-güvenli hâle getirir."""
        safe = name.replace("-", "_").replace(" ", "_").replace(".", "_")
        # Başında rakam varsa alt çizgi ekle
        if safe and safe[0].isdigit():
            safe = "_" + safe
        return safe.lower()


class FlatResult:
    """
    Bir objenin çözümleme sonucu.
    columns : {col_name: sql_type}
    arrays  : {col_name: list_of_items}
    """
    def __init__(self):
        self.columns: dict[str, str] = {}
        self.arrays:  dict[str, list] = {}

    def __repr__(self):
        return f"FlatResult(cols={list(self.columns)}, arrays={list(self.arrays)})"