"""
NoSQL'den SQL'e Dönüşüm Sistemi
Kocaeli Üniversitesi - Bilgisayar Mühendisliği
Programlama Laboratuvarı II - III. Proje
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os

from modules.parser import JSONParser
from modules.db_engine import DatabaseEngine
from modules.converter import ConverterEngine
from modules.visualizer import ERDiagramCanvas, StatsChartCanvas


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NoSQL → SQL Dönüşüm Sistemi")
        self.geometry("1200x750")
        self.configure(bg="#1e1e2e")

        self.db_engine = DatabaseEngine(":memory:")
        self.converter = ConverterEngine(self.db_engine)
        self.json_data = None

        self._build_ui()

    # ─────────────────────────── UI ────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e2e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#313244", foreground="#cdd6f4",
                        padding=[12, 5], font=("Consolas", 10))
        style.map("TNotebook.Tab", background=[("selected", "#89b4fa")],
                  foreground=[("selected", "#1e1e2e")])
        style.configure("Treeview", background="#181825", foreground="#cdd6f4",
                        fieldbackground="#181825", font=("Consolas", 10))
        style.configure("Treeview.Heading", background="#313244", foreground="#89b4fa",
                        font=("Consolas", 10, "bold"))

        # ── Top bar ──
        top = tk.Frame(self, bg="#181825", pady=8)
        top.pack(fill="x")

        tk.Label(top, text="⚡ NoSQL → SQL", bg="#181825", fg="#89b4fa",
                 font=("Consolas", 14, "bold")).pack(side="left", padx=14)

        btn_cfg = dict(bg="#313244", fg="#cdd6f4", activebackground="#45475a",
                       activeforeground="#cdd6f4", relief="flat", padx=12, pady=4,
                       font=("Consolas", 10), cursor="hand2")

        self.btn_open = tk.Button(top, text="📂 JSON Yükle", command=self.load_json, **btn_cfg)
        self.btn_open.pack(side="left", padx=4)

        self.btn_convert = tk.Button(top, text="🔄 Dönüştür", command=self.convert,
                                     state="disabled", **btn_cfg)
        self.btn_convert.pack(side="left", padx=4)

        self.btn_reset = tk.Button(top, text="🗑 Sıfırla", command=self.reset, **btn_cfg)
        self.btn_reset.pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="JSON dosyası seçin…")
        tk.Label(top, textvariable=self.status_var, bg="#181825", fg="#a6e3a1",
                 font=("Consolas", 9)).pack(side="right", padx=14)

        # ── Notebook ──
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_json   = self._make_tab("🌲 JSON Görünümü")
        self.tab_schema = self._make_tab("🗂 SQL Şeması")
        self.tab_data   = self._make_tab("📊 Tablo Verileri")
        self.tab_visualizer = self._make_tab("📊 ER & İstatistik")
        self.tab_log    = self._make_tab("📋 Log")

        self._build_json_tab()
        self._build_schema_tab()
        self._build_data_tab()
        self._build_visualizer_tab()
        self._build_log_tab()

    def _make_tab(self, title):
        frame = tk.Frame(self.nb, bg="#1e1e2e")
        self.nb.add(frame, text=title)
        return frame

    def _build_json_tab(self):
        frame = tk.Frame(self.tab_json, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        # Treeview (sol)
        left = tk.Frame(frame, bg="#1e1e2e")
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="Hiyerarşik Ağaç", bg="#1e1e2e", fg="#89b4fa",
                 font=("Consolas", 10, "bold")).pack(anchor="w")

        self.tree = ttk.Treeview(left)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        # Raw JSON (sağ)
        right = tk.Frame(frame, bg="#1e1e2e")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(right, text="Ham JSON", bg="#1e1e2e", fg="#89b4fa",
                 font=("Consolas", 10, "bold")).pack(anchor="w")
        self.txt_json = scrolledtext.ScrolledText(right, bg="#181825", fg="#cdd6f4",
                                                   font=("Consolas", 10), state="disabled")
        self.txt_json.pack(fill="both", expand=True)

    def _build_schema_tab(self):
        tk.Label(self.tab_schema, text="Üretilen CREATE TABLE Sorguları",
                 bg="#1e1e2e", fg="#89b4fa", font=("Consolas", 10, "bold")).pack(anchor="w", padx=6, pady=4)
        self.txt_schema = scrolledtext.ScrolledText(self.tab_schema, bg="#181825", fg="#a6e3a1",
                                                     font=("Consolas", 10), state="disabled")
        self.txt_schema.pack(fill="both", expand=True, padx=6, pady=4)

    def _build_data_tab(self):
        ctrl = tk.Frame(self.tab_data, bg="#1e1e2e")
        ctrl.pack(fill="x", padx=6, pady=4)
        tk.Label(ctrl, text="Tablo:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Consolas", 10)).pack(side="left")
        self.table_var = tk.StringVar()
        self.table_cb = ttk.Combobox(ctrl, textvariable=self.table_var, state="readonly", width=30)
        self.table_cb.pack(side="left", padx=6)
        self.table_cb.bind("<<ComboboxSelected>>", lambda _: self.show_table())

        self.data_frame = tk.Frame(self.tab_data, bg="#1e1e2e")
        self.data_frame.pack(fill="both", expand=True, padx=6, pady=4)

        self.data_tree = ttk.Treeview(self.data_frame, show="headings")
        vsb = ttk.Scrollbar(self.data_frame, orient="vertical", command=self.data_tree.yview)
        hsb = ttk.Scrollbar(self.data_frame, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.data_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")
        hsb.pack(side="bottom", fill="x")

    def _build_log_tab(self):
        self.txt_log = scrolledtext.ScrolledText(self.tab_log, bg="#181825", fg="#fab387",
                                                  font=("Consolas", 9), state="disabled")
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)

    def _build_visualizer_tab(self):
        frame = tk.Frame(self.tab_visualizer, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=6, pady=6)

        # Sol Panel: ER Diyagramı
        left_frame = tk.LabelFrame(frame, text=" 📐 İlişkisel Şema (ER Diyagramı) - Sürükle-Bırak ",
                                   bg="#1e1e2e", fg="#89b4fa", font=("Consolas", 10, "bold"), bd=1, relief="solid")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
        
        self.er_canvas = ERDiagramCanvas(left_frame, self.db_engine)
        self.er_canvas.pack(fill="both", expand=True, padx=4, pady=4)

        # Sağ Panel: İstatistik Grafiği
        right_frame = tk.LabelFrame(frame, text=" 📈 Tablo Veri Dağılımları (Satır Sayıları) ",
                                    bg="#1e1e2e", fg="#a6e3a1", font=("Consolas", 10, "bold"), bd=1, relief="solid")
        right_frame.pack(side="left", fill="both", expand=True, padx=(4, 0))

        self.stats_canvas = StatsChartCanvas(right_frame, self.db_engine)
        self.stats_canvas.pack(fill="both", expand=True, padx=4, pady=4)

    # ─────────────────────────── Actions ────────────────────────────

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Dosyaları", "*.json"), ("Tüm Dosyalar", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.json_data = json.load(f)
            self._show_json(self.json_data)
            self.status_var.set(f"✅ Yüklendi: {os.path.basename(path)}")
            self.btn_convert.config(state="normal")
            self._log(f"Dosya yüklendi: {path}")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def convert(self):
        if self.json_data is None:
            return
        try:
            self._log("─── Dönüşüm başladı ───")
            root_name = "root"
            schema_lines = []
            self.converter.convert(self.json_data, root_name, log_fn=self._log,
                                   schema_collector=schema_lines)

            # Schema tab
            self._set_text(self.txt_schema, "\n\n".join(schema_lines))

            # Populate table combobox
            tables = self.db_engine.list_tables()
            self.table_cb["values"] = tables
            if tables:
                self.table_var.set(tables[0])
                self.show_table()

            # ER ve İstatistik grafiklerini yükle
            self.er_canvas.load_schema()
            self.stats_canvas.load_stats()

            self.nb.select(1)
            self.status_var.set(f"✅ Dönüşüm tamamlandı — {len(tables)} tablo oluşturuldu")
            self._log(f"Dönüşüm tamamlandı. Oluşturulan tablolar: {tables}")
        except Exception as e:
            messagebox.showerror("Dönüşüm Hatası", str(e))
            self._log(f"HATA: {e}")

    def show_table(self):
        table = self.table_var.get()
        if not table:
            return
        cols, rows = self.db_engine.fetch_table(table)
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree["columns"] = cols
        for c in cols:
            self.data_tree.heading(c, text=c)
            self.data_tree.column(c, width=max(80, len(c) * 10), anchor="w")
        for row in rows:
            self.data_tree.insert("", "end", values=[str(v) if v is not None else "NULL" for v in row])

    def reset(self):
        self.db_engine.close()
        self.db_engine = DatabaseEngine(":memory:")
        self.converter = ConverterEngine(self.db_engine)
        
        # Görselleştirme modüllerinin db referansını güncelle
        self.er_canvas.db = self.db_engine
        self.stats_canvas.db = self.db_engine
        
        self.json_data = None
        self.tree.delete(*self.tree.get_children())
        self._set_text(self.txt_json, "")
        self._set_text(self.txt_schema, "")
        self._set_text(self.txt_log, "")
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree["columns"] = []
        self.table_cb["values"] = []
        self.table_var.set("")
        self.btn_convert.config(state="disabled")
        
        # Çizimleri temizle
        self.er_canvas.delete("all")
        self.stats_canvas.delete("all")
        
        self.status_var.set("Sıfırlandı. Yeni bir JSON dosyası seçin…")
        self._log("Sistem sıfırlandı.")

    # ─────────────────────────── Helpers ────────────────────────────

    def _show_json(self, data):
        # Tree view
        self.tree.delete(*self.tree.get_children())
        self._fill_tree("", "root", data)

        # Raw text
        pretty = json.dumps(data, ensure_ascii=False, indent=2)
        self._set_text(self.txt_json, pretty)

    def _fill_tree(self, parent, key, value):
        if isinstance(value, dict):
            node = self.tree.insert(parent, "end", text=f"📁 {key}", open=True)
            for k, v in value.items():
                self._fill_tree(node, k, v)
        elif isinstance(value, list):
            node = self.tree.insert(parent, "end", text=f"📋 {key} [{len(value)}]", open=False)
            for i, item in enumerate(value):
                self._fill_tree(node, f"[{i}]", item)
        else:
            self.tree.insert(parent, "end", text=f"🔹 {key}: {value}")

    def _set_text(self, widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def _log(self, msg):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()