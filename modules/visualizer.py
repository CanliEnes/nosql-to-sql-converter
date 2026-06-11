"""
Modül 5: Etkileşimli Görselleştirme Modülü (Visualizer)
───────────────────────────────────────────────────────
• ERDiagramCanvas: Tabloları düğüm (node) olarak çizen, sürüklemeyi destekleyen,
  ilişkileri (Foreign Key) oklarla bağlayan interaktif çizim alanı.
• StatsChartCanvas: Veri sayılarını modern bar grafikle gösteren,
  hover animasyonlu grafik alanı.
"""

import tkinter as tk
from tkinter import messagebox
import math


class ERDiagramCanvas(tk.Canvas):
    def __init__(self, parent, db_engine, **kwargs):
        # Koyu Catppuccin Mocha esintili renk paletiyle uyumlu varsayılanlar
        kwargs.setdefault("bg", "#11111b")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self.db = db_engine
        self.nodes = {}          # {table_name: {"x": x, "y": y, "w": w, "h": h, "columns": [...]}}
        self.relations = []      # [{"from_table": str, "from_col": str, "to_table": str}]
        self.dragged_node = None
        self.drag_offset = (0, 0)
        self._needs_layout = False

        # Bind olayları
        self.bind("<Button-1>", self._on_click)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if getattr(self, '_needs_layout', False):
            self.load_schema()
        elif self.nodes:
            self.redraw()

    def load_schema(self):
        """Veritabanındaki tabloları ve ilişkileri çekip yerleşimi hazırlar."""
        self.nodes.clear()
        self.relations.clear()

        tables = self.db.list_tables()
        if not tables:
            self.delete("all")
            self.create_text(
                self.winfo_width() / 2, self.winfo_height() / 2,
                text="Görüntülenecek tablo yok. Lütfen önce bir JSON dönüştürün.",
                fill="#585b70", font=("Consolas", 12, "bold"), justify="center"
            )
            return

        # Tablo konumlarını dairesel veya grid düzeninde başlangıç olarak dağıtalım
        num_tables = len(tables)
        
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Eğer sekme henüz görünmediyse boyutlar 1x1 gelir. 
        # Düzeni <Configure> (sekme açıldığında) event'ine ertele.
        if w < 50 or h < 50:
            self._needs_layout = True
            return
            
        self._needs_layout = False
        center_x = w / 2
        center_y = h / 2
        radius = min(center_x, center_y) * 0.65 if num_tables > 1 else 0

        for i, table in enumerate(tables):
            cols, _ = self.db.fetch_table(table)
            
            # Kolon tiplerini ve yabancı anahtar olup olmadıklarını öğrenelim
            relations = self.db.get_table_relations(table)
            fk_cols = {rel["from"]: rel["to_table"] for rel in relations}

            # Her kolon için etiket hazırlığı
            col_info = []
            for col in cols:
                if col == "id":
                    col_info.append((col, "🔑 id", "#a6e3a1"))  # Yeşil
                elif col in fk_cols:
                    col_info.append((col, f"🔗 {col} ({fk_cols[col]})", "#fab387"))  # Turuncu
                    # İlişki listesine ekle
                    self.relations.append({
                        "from_table": table,
                        "from_col": col,
                        "to_table": fk_cols[col]
                    })
                else:
                    col_info.append((col, f"🔹 {col}", "#cdd6f4"))  # Beyazımsı

            # Node boyutlarını hesapla
            longest_label = max([len(info[1]) for info in col_info] + [len(table) + 4])
            w = max(160, longest_label * 8 + 20)
            h = 30 + (len(cols) * 20) + 10

            # Koordinat ata
            if num_tables > 1:
                angle = (2 * math.pi * i) / num_tables
                x = center_x + radius * math.cos(angle) - w/2
                y = center_y + radius * math.sin(angle) - h/2
            else:
                x = center_x - w/2
                y = center_y - h/2

            self.nodes[table] = {
                "x": max(20, x),
                "y": max(20, y),
                "w": w,
                "h": h,
                "columns": col_info
            }

        self.redraw()

    def redraw(self):
        """Tüm canvası temizler ve tablo kartları ile ilişkileri yeniden çizer."""
        self.delete("all")

        # ── 1. İlişki Çizgilerini Çiz (Arka planda kalması için önce çiziyoruz) ──
        for rel in self.relations:
            t_from = rel["from_table"]
            t_to = rel["to_table"]
            if t_from in self.nodes and t_to in self.nodes:
                self._draw_connector(t_from, t_to)

        # ── 2. Tablo Kartlarını Çiz (Ön planda) ──
        for name, node in self.nodes.items():
            self._draw_node(name, node)

    def _draw_node(self, name, node):
        x, y, w, h = node["x"], node["y"], node["w"], node["h"]

        # Kart Arka Planı (Yuvarlatılmış Dikdörtgen Efekti)
        self._create_rounded_rect(x, y, x + w, y + h, radius=10, fill="#1e1e2e", outline="#313244", width=2, tags=f"node_{name}")
        
        # Kart Başlığı (Header) Arka Planı
        self._create_rounded_rect(x, y, x + w, y + 26, radius=10, fill="#313244", outline="", tags=f"node_{name}")
        self.create_rectangle(x, y + 15, x + w, y + 26, fill="#313244", outline="", tags=f"node_{name}") # Alt köşeleri düzeltmek için

        # Tablo Adı Text
        self.create_text(
            x + 12, y + 13,
            text=f"📂 {name.upper()}",
            anchor="w", fill="#89b4fa",
            font=("Consolas", 10, "bold"),
            tags=f"node_{name}"
        )

        # Kolonları Listele
        curr_y = y + 38
        for _, label, color in node["columns"]:
            self.create_text(
                x + 12, curr_y,
                text=label,
                anchor="w", fill=color,
                font=("Consolas", 9),
                tags=f"node_{name}"
            )
            curr_y += 20

    def _draw_connector(self, from_table, to_table):
        """İki tablo arasında yumuşak, oklu bir bağlantı çizgisi çizer."""
        n1 = self.nodes[from_table]
        n2 = self.nodes[to_table]

        # Merkez koordinatları
        cx1, cy1 = n1["x"] + n1["w"]/2, n1["y"] + n1["h"]/2
        cx2, cy2 = n2["x"] + n2["w"]/2, n2["y"] + n2["h"]/2

        # En yakın kenar noktalarını bulalım (Basit yaklaşım: merkezleri birleştiren doğrunun kutu sınırlarıyla kesişimi)
        # Pratik olarak, kutu sınırlarının orta noktalarından en yakın olanları seçelim
        pts1 = [
            (n1["x"] + n1["w"]/2, n1["y"]),              # Üst
            (n1["x"] + n1["w"]/2, n1["y"] + n1["h"]),     # Alt
            (n1["x"], n1["y"] + n1["h"]/2),              # Sol
            (n1["x"] + n1["w"], n1["y"] + n1["h"]/2)      # Sağ
        ]
        pts2 = [
            (n2["x"] + n2["w"]/2, n2["y"]),
            (n2["x"] + n2["w"]/2, n2["y"] + n2["h"]),
            (n2["x"], n2["y"] + n2["h"]/2),
            (n2["x"] + n2["w"], n2["y"] + n2["h"]/2)
        ]

        best_p1, best_p2 = pts1[0], pts2[0]
        min_dist = 999999
        for p1 in pts1:
            for p2 in pts2:
                d = (p1[0] - p2[0])**2 + (p1[1] - p2[1])**2
                if d < min_dist:
                    min_dist = d
                    best_p1, best_p2 = p1, p2

        x1, y1 = best_p1
        x2, y2 = best_p2

        # Çizgiyi çiz (hafif kavisli olması için orta noktayı bükebiliriz)
        # SQLite ilişkilerinde turuncu-şeftali tonları çok şık durur
        self.create_line(
            x1, y1, x2, y2,
            fill="#fab387", width=2, arrow=tk.LAST, arrowshape=(10, 12, 4),
            smooth=True
        )

    def _create_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [
            x1 + radius, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1 + radius,
            x1, y1
        ]
        return self.create_polygon(points, **kwargs, smooth=True)

    # ── Sürükle Bırak Olay Yönetimi ──

    def _on_click(self, event):
        # Tıklanan nesneyi bul
        clicked_item = self.find_withtag("current")
        if not clicked_item:
            return

        tags = self.gettags(clicked_item[0])
        # Tablo adını tag'den ayıklayalım (örn: node_kisi)
        node_tag = [t for t in tags if t.startswith("node_")]
        if node_tag:
            table_name = node_tag[0].replace("node_", "")
            self.dragged_node = table_name
            node = self.nodes[table_name]
            self.drag_offset = (event.x - node["x"], event.y - node["y"])

    def _on_drag(self, event):
        if not self.dragged_node:
            return

        node = self.nodes[self.dragged_node]
        new_x = event.x - self.drag_offset[0]
        new_y = event.y - self.drag_offset[1]

        # Sınırların dışına çıkmayı engelle
        canvas_w = self.winfo_width()
        canvas_h = self.winfo_height()
        node["x"] = max(10, min(new_x, canvas_w - node["w"] - 10))
        node["y"] = max(10, min(new_y, canvas_h - node["h"] - 10))

        self.redraw()

    def _on_release(self, event):
        self.dragged_node = None


class StatsChartCanvas(tk.Canvas):
    def __init__(self, parent, db_engine, **kwargs):
        kwargs.setdefault("bg", "#11111b")
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(parent, **kwargs)

        self.db = db_engine
        self.bars = []  # [{"table": str, "x1": x, "y1": y, "x2": x, "y2": y, "count": int}]
        self.hovered_bar_idx = None
        self._needs_draw = False

        self.bind("<Motion>", self._on_mouse_move)
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        # Ekran boyutu değiştiğinde veya sekme açıldığında grafiği yeniden boyutlandır/çiz
        if self.bars or getattr(self, '_needs_draw', False):
            self.load_stats()

    def load_stats(self):
        """Veritabanındaki her tablonun satır sayısını alıp bar grafiği çizer."""
        self.bars.clear()
        self.hovered_bar_idx = None
        self.delete("all")

        tables = self.db.list_tables()
        if not tables:
            self.create_text(
                self.winfo_width() / 2, self.winfo_height() / 2,
                text="Görüntülenecek veri yok.",
                fill="#585b70", font=("Consolas", 12, "bold")
            )
            return

        # Verileri topla
        stats = []
        max_count = 0
        for table in tables:
            count = self.db.get_table_row_count(table)
            stats.append((table, count))
            if count > max_count:
                max_count = count

        # Boş veritabanı durumunda
        if max_count == 0:
            max_count = 1

        # Grafik sınırlarını belirle
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Eğer sekme henüz ekranda gösterilmediyse boyutlar 1x1 gelir.
        # Bu durumda çizmeyi ertele. <Configure> tetiklendiğinde çizilecek.
        if w < 50 or h < 50:
            self._needs_draw = True
            return
            
        self._needs_draw = False
        
        pad_left = 60
        pad_right = 30
        pad_top = 40
        pad_bottom = 80

        graph_w = w - pad_left - pad_right
        graph_h = h - pad_top - pad_bottom

        # ── Kılavuz Çizgileri ve Y Ekseni Değerleri ──
        self.create_line(pad_left, pad_top, pad_left, h - pad_bottom, fill="#313244", width=2)
        self.create_line(pad_left, h - pad_bottom, w - pad_right, h - pad_bottom, fill="#313244", width=2)

        # 4 Yatay kılavuz çizgisi
        for i in range(5):
            val = int((max_count / 4) * i)
            y_pos = h - pad_bottom - (graph_h * (i / 4))
            self.create_line(pad_left, y_pos, w - pad_right, y_pos, fill="#1e1e2e", dash=(4, 4))
            self.create_text(pad_left - 10, y_pos, text=str(val), fill="#a6e3a1", font=("Consolas", 9), anchor="e")

        # ── Sütunları Çiz ──
        num_bars = len(stats)
        bar_gap = 15
        total_gaps_w = bar_gap * (num_bars + 1)
        bar_w = max(20, (graph_w - total_gaps_w) / num_bars)

        for i, (table, count) in enumerate(stats):
            # Koordinatları hesapla
            bx1 = pad_left + bar_gap + i * (bar_w + bar_gap)
            bx2 = bx1 + bar_w
            
            # Sıfır ise 2 piksellik bir yükseklik ver ki görünür olsun
            bar_height = (count / max_count) * graph_h if count > 0 else 2
            by1 = h - pad_bottom - bar_height
            by2 = h - pad_bottom

            # Sütun nesnesi kaydet
            self.bars.append({
                "table": table,
                "x1": bx1, "y1": by1,
                "x2": bx2, "y2": by2,
                "count": count,
                "rect_id": None,
                "text_id": None
            })

            # Sütunu Çiz (Varsayılan renk: Açık Mavi #89b4fa)
            rect_id = self.create_rectangle(
                bx1, by1, bx2, by2,
                fill="#89b4fa", outline="#b4befe", width=1
            )
            self.bars[-1]["rect_id"] = rect_id

            # Alt Etiket (Tablo Adı)
            display_name = table[5:] if table.startswith("root_") else table
            short_name = display_name if len(display_name) <= 22 else display_name[:19] + "..."
            
            self.create_text(
                bx1 + bar_w/2, h - pad_bottom + 15,
                text=short_name, fill="#cdd6f4",
                font=("Consolas", 8, "bold"), angle=30, anchor="ne"
            )

        # Başlık
        self.create_text(
            w / 2, 20,
            text="Tablolardaki Toplam Satır Sayıları (Veri Yoğunluğu)",
            fill="#cdd6f4", font=("Consolas", 11, "bold")
        )

    def _on_mouse_move(self, event):
        """Mouse sütunların üzerine geldiğinde rengi değiştirir ve veri ipucu (tooltip) gösterir."""
        active_idx = None
        for idx, bar in enumerate(self.bars):
            if bar["x1"] <= event.x <= bar["x2"] and bar["y1"] <= event.y <= bar["y2"]:
                active_idx = idx
                break

        # Durum değiştiyse aksiyon al (Hover mikro-animasyonu)
        if active_idx != self.hovered_bar_idx:
            # Önceki aktif barı eski rengine döndür
            if self.hovered_bar_idx is not None:
                prev_bar = self.bars[self.hovered_bar_idx]
                self.itemconfig(prev_bar["rect_id"], fill="#89b4fa", outline="#b4befe")
                if prev_bar["text_id"]:
                    self.delete(prev_bar["text_id"])
                    prev_bar["text_id"] = None

            # Yeni aktif barı yeşile (#a6e3a1) boya ve üstüne satır sayısı değerini yaz
            if active_idx is not None:
                bar = self.bars[active_idx]
                self.itemconfig(bar["rect_id"], fill="#a6e3a1", outline="#a6e3a1")
                
                # Sütunun üzerine sayısal değeri yaz
                text_id = self.create_text(
                    bar["x1"] + (bar["x2"] - bar["x1"])/2, bar["y1"] - 12,
                    text=f"{bar['count']} satır", fill="#a6e3a1",
                    font=("Consolas", 9, "bold")
                )
                bar["text_id"] = text_id

            self.hovered_bar_idx = active_idx
