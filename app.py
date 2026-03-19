"""
Računi App - Serbian Invoice Manager
Main UI built with CustomTkinter
"""
import sys
if sys.stderr is None:
    sys.stderr = open('nul', 'w')
if sys.stdout is None:
    sys.stdout = open('nul', 'w')

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.scraper import scrape_invoice
from core.qr_reader import extract_url_from_file
from core.excel_export import append_invoice
from core.index import InvoiceIndex

# ── Theme ──────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

THEMES = {
    'dark': {
        'DARK_BG':  '#0F0F1A',
        'PANEL_BG': '#1A1A2E',
        'ACCENT':   '#E8D5B7',
        'ACCENT2':  '#C9A96E',
        'GREEN':    '#4CAF50',
        'RED':      '#EF5350',
        'MUTED':    '#888899',
    },
    'light': {
        'DARK_BG':  '#EEEEF4',
        'PANEL_BG': '#F8F8FC',
        'ACCENT':   "#BABACB",
        'ACCENT2':  '#5B4FCF',
        'GREEN':    '#2E7D32',
        'RED':      '#C62828',
        'MUTED':    '#666680',
    }
}
FONT_TITLE  = ("Georgia", 22, "bold")
FONT_HEAD   = ("Georgia", 13, "bold")
FONT_BODY   = ("Calibri", 11)
FONT_SMALL  = ("Calibri", 10)
FONT_MONO   = ("Consolas", 10)


_theme = THEMES['dark']
DARK_BG  = _theme['DARK_BG']
PANEL_BG = _theme['PANEL_BG']
ACCENT   = _theme['ACCENT']
ACCENT2  = _theme['ACCENT2']
GREEN    = _theme['GREEN']
RED      = _theme['RED']
MUTED    = _theme['MUTED']


class StatusBar(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, height=28, fg_color=PANEL_BG, corner_radius=0)
        self.label = ctk.CTkLabel(self, text="Ready", font=FONT_SMALL,
                                  text_color=MUTED, anchor='w')
        self.label.pack(side='left', padx=12)
        self.progress = ctk.CTkProgressBar(self, width=150, height=8,
                                           fg_color='#2A2A4A', progress_color=ACCENT2)
        self.progress.set(0)
        self.progress.pack(side='right', padx=12, pady=10)
        self.progress.pack_forget()  # hidden by default
        self.counter_label = ctk.CTkLabel(self, text="", font=FONT_SMALL,
                                           text_color=ACCENT2)
        self.counter_label.pack(side='right', padx=4, pady=10)

    def set(self, text, color=None):
        self.label.configure(text=text, text_color=color or MUTED)
        self.update_idletasks()

    def show_progress(self, value, current=None, total=None):
        self.progress.pack(side='right', padx=12, pady=10)
        self.progress.set(value)
        if current and total:
            self.counter_label.configure(text=f"{current}/{total}")
            self.counter_label.pack(side='right', padx=4)
        self.update_idletasks()

    def hide_progress(self):
        self.progress.pack_forget()
        self.counter_label.pack_forget()
        self.update_idletasks()



class InvoiceRow(ctk.CTkFrame):
    """Single row in the invoice list."""
    def __init__(self, master, invoice: dict, on_select, **kwargs):
        super().__init__(master, fg_color=PANEL_BG, corner_radius=8, **kwargs)
        self.invoice = invoice
        self.configure(cursor='hand2')

        date = invoice.get('date', '')[:10]
        company = invoice.get('company_name', 'Unknown')[:28]
        store = invoice.get('store_name', '')[:24]
        total = f"{float(invoice.get('total_price') or 0):,.2f} RSD"
        has_img = '📷' if invoice.get('image_path') else '  '

        ctk.CTkLabel(self, text=date, font=FONT_MONO, text_color=ACCENT2, width=90, anchor='w').grid(row=0, column=0, padx=(10,4), pady=6)
        ctk.CTkLabel(self, text=company, font=FONT_BODY, text_color=ACCENT, width=180, anchor='w').grid(row=0, column=1, padx=4)
        ctk.CTkLabel(self, text=store, font=FONT_BODY, text_color=MUTED, width=160, anchor='w').grid(row=0, column=2, padx=4)
        ctk.CTkLabel(self, text=total, font=FONT_BODY, text_color=GREEN, width=120, anchor='e').grid(row=0, column=3, padx=4)
        ctk.CTkLabel(self, text=has_img, font=FONT_BODY, width=24).grid(row=0, column=4, padx=(4,10))

        self.bind('<Button-1>', lambda e: on_select(invoice))
        for widget in self.winfo_children():
            widget.bind('<Button-1>', lambda e: on_select(invoice))

    def highlight(self, on: bool):
        self.configure(fg_color='#2A2A4A' if on else PANEL_BG)

class ManualEntryDialog(ctk.CTkToplevel):
    def __init__(self, master, on_submit):
        super().__init__(master)
        self.title("Ručni unos računa")
        self.geometry("500x700")
        self.resizable(False, False)
        self.configure(fg_color=DARK_BG)
        self.on_submit = on_submit
        self.image_path = None
        self.grab_set()
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color=DARK_BG)
        scroll.pack(fill='both', expand=True, padx=16, pady=16)

        def field(label, placeholder='', default=''):
            ctk.CTkLabel(scroll, text=label, font=FONT_SMALL, text_color=MUTED, anchor='w').pack(fill='x', pady=(8,2))
            entry = ctk.CTkEntry(scroll, placeholder_text=placeholder, font=FONT_BODY,
                                 fg_color=PANEL_BG, border_color=MUTED, text_color=ACCENT)
            entry.pack(fill='x')
            if default:
                entry.insert(0, default)
            return entry

        from datetime import date
        self.e_date = field("Datum", "YYYY-MM-DD", date.today().strftime('%Y-%m-%d'))
        self.e_company = field("Naziv kompanije", "npr. Mercator")
        self.e_store = field("Prodajno mesto", "npr. 1234-Naziv radnje")
        self.e_address = field("Adresa", "npr. Ulica bb")
        self.e_place = field("Grad", "npr. Beograd")
        self.e_municipality = field("Opština", "npr. Vracar")
        self.e_tin = field("PIB", "npr. 100115129")
        self.e_total = field("Ukupan iznos (RSD)", "npr. 1500.00")
        self.e_vat = field("PDV (RSD)", "npr. 250.00")
        self.e_pfr = field("Brojač računa (TC/UKUPANPP)", "npr. 169368/169371PP")

        # Image attachment
        ctk.CTkFrame(scroll, height=1, fg_color=MUTED).pack(fill='x', pady=12)
        ctk.CTkLabel(scroll, text="Slika računa (opciono)", font=FONT_SMALL,
                     text_color=MUTED, anchor='w').pack(fill='x')
        img_frame = ctk.CTkFrame(scroll, fg_color='transparent')
        img_frame.pack(fill='x', pady=4)
        self.img_label = ctk.CTkLabel(img_frame, text="Nije izabrana slika",
                                       font=FONT_SMALL, text_color=MUTED, anchor='w')
        self.img_label.pack(side='left', expand=True)
        ctk.CTkButton(img_frame, text="Izaberi…", font=FONT_SMALL, width=80,
                      fg_color=PANEL_BG, hover_color='#3A3A6A', text_color=ACCENT,
                      command=self._pick_image).pack(side='right')

        # Buttons
        ctk.CTkFrame(scroll, height=1, fg_color=MUTED).pack(fill='x', pady=12)
        btn_frame = ctk.CTkFrame(scroll, fg_color='transparent')
        btn_frame.pack(fill='x')
        ctk.CTkButton(btn_frame, text="Otkaži", font=FONT_BODY,
                      fg_color=PANEL_BG, hover_color=RED, text_color=ACCENT,
                      command=self.destroy).pack(side='left')
        ctk.CTkButton(btn_frame, text="Sačuvaj račun", font=FONT_BODY,
                      fg_color=ACCENT2, hover_color='#B8956E', text_color='#1A1A2E',
                      command=self._submit).pack(side='right')

    def _pick_image(self):
        path = filedialog.askopenfilename(
            title="Izaberi sliku računa",
            filetypes=[("Slike", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.pdf"), ("Sve", "*.*")]
        )
        if path:
            self.image_path = path
            self.img_label.configure(text=os.path.basename(path), text_color=ACCENT)

    def _submit(self):
        try:
            total = float(self.e_total.get().strip().replace(',', '.') or 0)
            vat = float(self.e_vat.get().strip().replace(',', '.') or 0)
        except ValueError:
            messagebox.showerror("Greška", "Iznos mora biti broj.")
            return

        date_val = self.e_date.get().strip()
        pfr = self.e_pfr.get().strip()

        # Generate a unique fake URL for manual entries so duplicate detection works
        import hashlib
        unique = f"manual_{pfr}_{date_val}_{total}"
        fake_url = f"manual://{hashlib.md5(unique.encode()).hexdigest()}"

        invoice = {
            'url': fake_url,
            'date': date_val,
            'company_tin': self.e_tin.get().strip(),
            'company_name': self.e_company.get().strip(),
            'company_details': '',
            'store_name': self.e_store.get().strip(),
            'store_address': self.e_address.get().strip(),
            'store_place': self.e_place.get().strip(),
            'store_municipality': self.e_municipality.get().strip(),
            'total_price': total,
            'total_vat': vat,
            'pfr_number': pfr,
            'items': [],
            'pre_text': None,  # no pre_text for manual entries
        }

        self.on_submit(invoice, self.image_path)
        self.destroy()

class App(ctk.CTk):
    def _toggle_theme(self):
        global DARK_BG, PANEL_BG, ACCENT, ACCENT2, GREEN, RED, MUTED
        current = 'dark' if DARK_BG == THEMES['dark']['DARK_BG'] else 'light'
        new = 'light' if current == 'dark' else 'dark'
        t = THEMES[new]
        DARK_BG  = t['DARK_BG']
        PANEL_BG = t['PANEL_BG']
        ACCENT   = t['ACCENT']
        ACCENT2  = t['ACCENT2']
        GREEN    = t['GREEN']
        RED      = t['RED']
        MUTED    = t['MUTED']
        ctk.set_appearance_mode('light' if new == 'light' else 'dark')
        # Rebuild UI
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        self._refresh_list()

    def __init__(self, data_dir: str):
        super().__init__()
        self.title("Menadžer računa")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=DARK_BG)

        self.index = InvoiceIndex(data_dir)
        self.data_dir = data_dir
        self.excel_path = os.path.join(data_dir, 'racuni.xlsx')
        self.selected_invoice = None
        self.invoice_rows: list[InvoiceRow] = []

        self._build_ui()
        self._refresh_list()

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self._build_sidebar()
        self._build_main()

        self.status = StatusBar(self)
        self.status.grid(row=1, column=0, columnspan=2, sticky='ew')

    def _build_sidebar(self):
        sidebar = ctk.CTkFrame(self, width=260, fg_color=PANEL_BG, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(8, weight=1)

        # Title
        ctk.CTkLabel(sidebar, text="RAČUNI", font=FONT_TITLE,
                     text_color=ACCENT).grid(row=0, column=0, padx=20, pady=(24,2), sticky='w')
        ctk.CTkLabel(sidebar, text="Menadžer računa", font=FONT_SMALL,
                     text_color=MUTED).grid(row=1, column=0, padx=20, pady=(0,20), sticky='w')

        ctk.CTkFrame(sidebar, height=1, fg_color='#333355').grid(row=2, column=0, sticky='ew', padx=16, pady=4)
        #toggle dark mode button
        ctk.CTkButton(sidebar, text="☀ / ☾", font=FONT_SMALL, width=60,
              fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
              command=self._toggle_theme).grid(row=0, column=0, padx=20, pady=(24,2), sticky='e')

        # Add invoice section
        ctk.CTkLabel(sidebar, text="DODAJ RAČUN", font=("Calibri", 10, "bold"),
                     text_color=MUTED).grid(row=3, column=0, padx=20, pady=(16,6), sticky='w')

        self.url_entry = ctk.CTkEntry(sidebar, placeholder_text="Nalepi URL sa purs.gov.rs…",
                                      font=FONT_SMALL, fg_color=DARK_BG,
                                      border_color=MUTED, text_color=ACCENT)
        self.url_entry.grid(row=4, column=0, padx=16, pady=(0,8), sticky='ew')

        ctk.CTkButton(sidebar, text="↵  Dodaj sa URL", font=FONT_BODY,
                      fg_color=ACCENT2, hover_color='#B8956E', text_color='#1A1A2E',
                      command=self._add_from_url).grid(row=5, column=0, padx=16, pady=(0,6), sticky='ew')

        ctk.CTkButton(sidebar, text="📷  Dodaj sa slike", font=FONT_BODY,
                      fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
                      command=self._add_from_image).grid(row=6, column=0, padx=16, pady=(0,6), sticky='ew')

        ctk.CTkButton(sidebar, text="✏  Ručni unos", font=FONT_BODY,
                      fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
                      command=self._add_manual).grid(row=7, column=0, padx=16, pady=(0,6), sticky='ew')

        ctk.CTkFrame(sidebar, height=1, fg_color='#333355').grid(row=8, column=0, sticky='ew', padx=16, pady=8)

        # Stats panel
        self.stats_frame = ctk.CTkFrame(sidebar, fg_color=DARK_BG, corner_radius=8)
        self.stats_frame.grid(row=8, column=0, padx=16, pady=8, sticky='new')
        self._build_stats_panel()

        # Excel settings
        ctk.CTkFrame(sidebar, height=1, fg_color='#333355').grid(row=9, column=0, sticky='ew', padx=16, pady=4)
        ctk.CTkLabel(sidebar, text="EXCEL FAJL", font=("Calibri", 10, "bold"),
                     text_color=MUTED).grid(row=10, column=0, padx=20, pady=(8,4), sticky='w')
        self.excel_label = ctk.CTkLabel(sidebar, text=os.path.basename(self.excel_path),
                                         font=FONT_SMALL, text_color=ACCENT2, anchor='w')
        self.excel_label.grid(row=11, column=0, padx=20, sticky='w')
        ctk.CTkButton(sidebar, text="Promeni…", font=FONT_SMALL, width=80,
                      fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
                      command=self._pick_excel).grid(row=12, column=0, padx=16, pady=(4,16), sticky='w')

    def _build_stats_panel(self):
        for w in self.stats_frame.winfo_children():
            w.destroy()
        stats = self.index.stats()
        ctk.CTkLabel(self.stats_frame, text="Ukupno računa", font=FONT_SMALL,
                     text_color=MUTED).grid(row=0, column=0, padx=12, pady=(10,0), sticky='w')
        ctk.CTkLabel(self.stats_frame, text=str(stats['count']), font=("Georgia", 18, "bold"),
                     text_color=ACCENT).grid(row=1, column=0, padx=12, sticky='w')
        ctk.CTkLabel(self.stats_frame, text="Ukupno potrošeno", font=FONT_SMALL,
                     text_color=MUTED).grid(row=2, column=0, padx=12, pady=(8,0), sticky='w')
        ctk.CTkLabel(self.stats_frame, text=f"{stats['total_spent']:,.0f} RSD",
                     font=("Georgia", 15, "bold"), text_color=GREEN).grid(row=3, column=0, padx=12, sticky='w')
        ctk.CTkLabel(self.stats_frame, text="Ukupno PDV", font=FONT_SMALL,
                     text_color=MUTED).grid(row=4, column=0, padx=12, pady=(8,0), sticky='w')
        ctk.CTkLabel(self.stats_frame, text=f"{stats['total_vat']:,.0f} RSD",
                     font=FONT_BODY, text_color=MUTED).grid(row=5, column=0, padx=12, pady=(0,10), sticky='w')

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color=DARK_BG, corner_radius=0)
        main.grid(row=0, column=1, sticky='nsew')
        main.grid_rowconfigure(2, weight=1)
        main.grid_columnconfigure(0, weight=1)

        # Search bar
        search_frame = ctk.CTkFrame(main, fg_color=PANEL_BG, corner_radius=0, height=50)
        search_frame.grid(row=0, column=0, columnspan=2, sticky='ew')
        search_frame.grid_propagate(False)

        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._refresh_list())
        ctk.CTkEntry(search_frame, textvariable=self.search_var,
                    placeholder_text="🔍  Pretraži",
                    font=FONT_BODY, fg_color=DARK_BG,
                    border_color=MUTED, text_color=ACCENT,
                    width=320).pack(side='left', padx=16, pady=10)

        ctk.CTkLabel(search_frame, text="", fg_color=PANEL_BG).pack(side='left', expand=True)

        ctk.CTkButton(search_frame, text="Otvori Excel", font=FONT_SMALL,
                    fg_color='#2A2A4A', hover_color=GREEN, text_color=ACCENT,
                    command=self._open_excel).pack(side='right', padx=8, pady=10)
        ctk.CTkButton(search_frame, text="Otvori Folder", font=FONT_SMALL,
                    fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
                    command=self._open_folder).pack(side='right', padx=4, pady=10)

        # Columns header
        header = ctk.CTkFrame(main, fg_color=DARK_BG, corner_radius=0, height=30)
        header.grid(row=1, column=0, columnspan=2, sticky='ew')
        for i, (label, w) in enumerate([('Datum', 90), ('Preduzeće', 180), ('Prodavnica', 160), ('Ukupno', 120), ('📷', 24)]):
            ctk.CTkLabel(header, text=label, font=("Calibri", 9, "bold"),
                        text_color=MUTED, width=w, anchor='w').grid(row=0, column=i, padx=(10 if i == 0 else 4, 4), pady=4)

        # Scrollable list
        self.list_frame = ctk.CTkScrollableFrame(main, fg_color=DARK_BG, corner_radius=0)
        self.list_frame.grid(row=2, column=0, sticky='nsew', padx=0, pady=0)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Detail panel
        self.detail_panel = ctk.CTkFrame(main, fg_color=PANEL_BG, corner_radius=12, width=340)
        self.detail_panel.grid(row=2, column=1, sticky='nsew', padx=12, pady=12)
        self.detail_panel.grid_propagate(False)
        main.grid_columnconfigure(1, weight=0, minsize=0)
        self._build_detail_panel()

    def _build_detail_panel(self, invoice=None):
        for w in self.detail_panel.winfo_children():
            w.destroy()

        if not invoice:
            ctk.CTkLabel(self.detail_panel, text="Izaberi račun\nda vidiš detalje",
                        font=FONT_BODY, text_color=MUTED).pack(expand=True)
            return

        self.detail_panel.master.grid_columnconfigure(1, weight=0, minsize=340)

        scroll = ctk.CTkScrollableFrame(self.detail_panel, fg_color='transparent')
        scroll.pack(fill='both', expand=True)
        
        def _bind_scroll(widget):
            widget.bind('<MouseWheel>', lambda e: scroll._parent_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
            for child in widget.winfo_children():
                _bind_scroll(child)

        scroll.bind('<MouseWheel>', lambda e: scroll._parent_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        scroll._parent_canvas.bind('<MouseWheel>', lambda e: scroll._parent_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        # Header
        ctk.CTkLabel(scroll, text=invoice.get('company_name', ''),
                    font=FONT_HEAD, text_color=ACCENT, wraplength=300).pack(padx=16, pady=(16,2), anchor='w')
        ctk.CTkLabel(scroll, text=invoice.get('store_name', ''),
                    font=FONT_BODY, text_color=MUTED).pack(padx=16, anchor='w')
        ctk.CTkLabel(scroll, text=invoice.get('store_address', ''),
                    font=FONT_SMALL, text_color=MUTED).pack(padx=16, anchor='w')

        ctk.CTkFrame(scroll, height=1, fg_color='#333355').pack(fill='x', padx=16, pady=10)

        def row(label, value, color=ACCENT):
            f = ctk.CTkFrame(scroll, fg_color='transparent')
            f.pack(fill='x', padx=16, pady=2)
            ctk.CTkLabel(f, text=label, font=FONT_SMALL, text_color=MUTED, width=100, anchor='w').pack(side='left')
            ctk.CTkLabel(f, text=str(value), font=FONT_BODY, text_color=color, anchor='w').pack(side='left')

        row("Datum", invoice.get('date', '')[:16])
        row("Ukupno", f"{float(invoice.get('total_price') or 0):,.2f} RSD", GREEN)
        row("PDV", f"{float(invoice.get('total_vat') or 0):,.2f} RSD", MUTED)
        pfr = invoice.get('pfr_number', '')
        row("Brojač računa", pfr)
        if pfr:
            ctk.CTkButton(scroll, text="Copy", font=FONT_SMALL, width=60,
                  fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
                  command=lambda p=pfr: self.clipboard_clear() or self.clipboard_append(p) or self.status.set("✓  Copied to clipboard.", GREEN)
                  ).pack(padx=16, pady=(0,4), anchor='w')
        row("TIN", invoice.get('company_tin', ''))
        tin = invoice.get('company_tin', '')
        if tin:
            ctk.CTkButton(scroll, text="Pretraži na PURS →", font=FONT_SMALL,
                        fg_color='transparent', hover_color='#2A2A4A', text_color=ACCENT2,
                        anchor='w', command=lambda t=tin: os.system(f'open "https://www.purs.gov.rs/pib.html?pib={t}"') if os.name != 'nt' else os.system(f'start "" "https://www.purs.gov.rs/pib.html?pib={t}"')
                        ).pack(padx=16, anchor='w')

        ctk.CTkFrame(scroll, height=1, fg_color='#333355').pack(fill='x', padx=16, pady=8)
        ctk.CTkLabel(scroll, text="DETALJI PREDUZEĆA", font=("Calibri", 9, "bold"),
                    text_color=MUTED).pack(padx=16, anchor='w')
        details_entry = ctk.CTkEntry(scroll, placeholder_text="Unesite detalje preduzeća…",
                                    font=FONT_BODY, fg_color='#0F0F1A',
                                    border_color='#333355', text_color=ACCENT)
        details_entry.pack(fill='x', padx=16, pady=(4,0))
        if invoice.get('company_details'):
            details_entry.insert(0, invoice['company_details'])

        def save_details():
            val = details_entry.get().strip()
            self.index.update_company_details(invoice['id'], val)
            invoice['company_details'] = val
            self.status.set("✓  Detalji preduzeća sačuvani.", GREEN)

        ctk.CTkButton(scroll, text="Sačuvaj", font=FONT_SMALL,
                    fg_color=ACCENT2, hover_color='#B8956E', text_color='#1A1A2E',
                    command=save_details).pack(padx=16, pady=4, anchor='w')

        ctk.CTkFrame(scroll, height=1, fg_color='#333355').pack(fill='x', padx=16, pady=10)
        ctk.CTkLabel(scroll, text="STAVKE", font=("Calibri", 9, "bold"),
                    text_color=MUTED).pack(padx=16, anchor='w')

      
        # Actions
        ctk.CTkFrame(scroll, height=1, fg_color='#333355').pack(fill='x', padx=16, pady=8)

        if invoice.get('image_path') and os.path.exists(invoice['image_path']):
            ctk.CTkButton(scroll, text="Pogledaj sliku", font=FONT_SMALL,
                        fg_color='#2A2A4A', hover_color='#3A3A6A', text_color=ACCENT,
                        command=lambda: self._open_image(invoice['image_path'])).pack(fill='x', padx=12, pady=2)

        ctk.CTkButton(scroll, text="Exportuj Red", font=FONT_SMALL,
                    fg_color=ACCENT2, hover_color='#B8956E', text_color='#1A1A2E',
                    command=lambda: self._export_single(invoice)).pack(fill='x', padx=12, pady=2)

        ctk.CTkButton(scroll, text="Obriši", font=FONT_SMALL,
                    fg_color='#3A1A1A', hover_color=RED, text_color='#FFAAAA',
                    command=lambda: self._delete_invoice(invoice['id'])).pack(fill='x', padx=12, pady=(2,12))
        _bind_scroll(scroll)
    # ── Data actions ────────────────────────────────────────────────────────
    def _add_from_url(self):
        url = self.url_entry.get().strip()
        if not url:
            self.status.set("Molimo unesite URL.", RED)
            return
        self.url_entry.delete(0, 'end')
        self._do_add(url=url, image_path=None)

    def _add_from_image(self):
        paths = filedialog.askopenfilenames(
            title="Izaberite slike ili PDF-ove računa",
            filetypes=[("Slike & PDF-ovi", "*.jpg *.jpeg *.png *.bmp *.tiff *.webp *.pdf"), ("Sve", "*.*")]
        )
        if not paths:
            return
        self._do_add_batch(paths)

    def _add_manual(self):
        def on_submit(invoice, image_path):
            self._do_add_manual(invoice, image_path)
        ManualEntryDialog(self, on_submit)

    def _do_add_manual(self, invoice, image_path):
        self.status.set("Čuvanje…", ACCENT2)
        def worker():
            try:
                result = self.index.add(invoice, source_image_path=image_path)
                if result['duplicate']:
                    self.status.set("⚠  Račun već postoji.", ACCENT2)
                    return
                append_invoice(self.excel_path, invoice,
                            image_filename=result.get('image_filename', ''))
                self.status.set(f"✓  Dodat: {invoice.get('company_name', '')} — {invoice.get('total_price', 0):,.2f} RSD", GREEN)
                self.after(0, self._refresh_list)
                self.after(0, self._build_stats_panel)
            except Exception as e:
                self.status.set(f"✗  Greška: {e}", RED)
        threading.Thread(target=worker, daemon=True).start()

    def _do_add_batch(self, paths):
        total = len(paths)
        completed = [0]
        semaphore = threading.Semaphore(4)  # max 4 concurrent

        def on_done():
            completed[0] += 1
            progress = completed[0] / total
            self.after(0, lambda c=completed[0], t=total: self.status.show_progress(progress, c, t))
            if completed[0] == total:
                self.after(0, self.status.hide_progress)
                self.after(0, self._refresh_list)
                self.after(0, self._build_stats_panel)

        def throttled_worker(path):
            with semaphore:
                import time
                time.sleep(0.5)  # 500ms delay da sprecimo limitiranje ip-ja od strane purs.gov.rs promeniti na vise po potrebi
                self._worker(None, path, on_done)

        self.status.show_progress(0)
        for path in paths:
            threading.Thread(target=throttled_worker, args=(path,), daemon=True).start()

    def _do_add(self, url=None, image_path=None):
        self.status.set("Obrada…", ACCENT2)
        threading.Thread(target=self._worker, args=(url, image_path, None), daemon=True).start()

    def _worker(self, url, image_path, on_done=None):
        try:
            resolved_url = url
            if not resolved_url and image_path:
                self.after(0, lambda: self.status.set("Dekodiranje QR koda…", ACCENT2))
                resolved_url = extract_url_from_file(image_path)

            if not resolved_url:
                self.after(0, lambda: self.status.set("✗  Nema URL-a ili slike.", RED))
                return

            self.after(0, lambda: self.status.set("Preuzimanje podataka o računu…", ACCENT2))
            invoice = scrape_invoice(resolved_url)

            result = self.index.add(invoice, source_image_path=image_path)
            if result['duplicate']:
                self.after(0, lambda: self.status.set("⚠  Već postoji (duplikat URL-a).", ACCENT2))
                if on_done: on_done()
                return

            append_invoice(self.excel_path, invoice,
                        image_filename=result.get('image_filename', ''))

            msg = f"✓  Dodato: {invoice.get('company_name', '')} — {invoice.get('total_price', 0):,.2f} RSD"
            self.after(0, lambda m=msg: self.status.set(m, GREEN))
            if not on_done:
                self.after(0, self._refresh_list)
                self.after(0, self._build_stats_panel)

        except Exception as e:
            self.after(0, lambda err=e: self.status.set(f"✗  Greška: {err}", RED))
        finally:
            if on_done:
                on_done()
    def _export_single(self, invoice):
        try:
            # Refresh from DB to get latest company_details
            fresh = self.index.search()
            fresh_invoice = next((i for i in fresh if i['id'] == invoice['id']), invoice)
            result = append_invoice(self.excel_path, fresh_invoice, force=True)
            if result.get('duplicate') and not True:
                self.status.set("Već izvezeno u Excel.", ACCENT2)
            else:
                self.status.set(f"✓  Izvezeno u {os.path.basename(self.excel_path)}", GREEN)
        except Exception as e:
            self.status.set(f"✗  Greška pri izvozu: {e}", RED)

    def _delete_invoice(self, invoice_id):
        if not messagebox.askyesno("Obriši račun", "Da li želite da obrišete ovaj račun iz indeksa?\nOvo će takođe obrisati sačuvanu kopiju slike."):
            return
        self.index.delete(invoice_id)
        self.selected_invoice = None
        self._build_detail_panel(None)
        self._refresh_list()
        self._build_stats_panel()
        self.status.set("Račun obrisan.", MUTED)

    # ── List ────────────────────────────────────────────────────────────────
    def _refresh_list(self):
        query = self.search_var.get() if hasattr(self, 'search_var') else ''
        invoices = self.index.search(query=query)

        for w in self.list_frame.winfo_children():
            w.destroy()
        self.invoice_rows = []

        if not invoices:
            ctk.CTkLabel(self.list_frame, text="Nema računa.\nDodajte jedan koristeći bočnu traku.",
                         font=FONT_BODY, text_color=MUTED).pack(expand=True, pady=60)
            return

        for inv in invoices:
            r = InvoiceRow(self.list_frame, inv, self._on_select_invoice)
            r.pack(fill='x', padx=8, pady=2)
            self.invoice_rows.append(r)

    def _on_select_invoice(self, invoice):
        self.selected_invoice = invoice
        for row in self.invoice_rows:
            row.highlight(row.invoice['id'] == invoice['id'])
        self._build_detail_panel(invoice)

    # ── Utilities ───────────────────────────────────────────────────────────
    def _open_excel(self):
        if not os.path.exists(self.excel_path):
            self.status.set("Excel fajl još nije kreiran — dodajte račun prvo.", MUTED)
            return
        os.startfile(self.excel_path) if os.name == 'nt' else os.system(f'open "{self.excel_path}"')

    def _open_folder(self):
        path = self.data_dir
        os.startfile(path) if os.name == 'nt' else os.system(f'open "{path}"')

    def _open_image(self, path):
        os.startfile(path) if os.name == 'nt' else os.system(f'open "{path}"')

    def _pick_excel(self):
        path = filedialog.asksaveasfilename(
            title="Izaberite Excel fajl",
            defaultextension='.xlsx',
            filetypes=[("Excel", "*.xlsx")],
            initialfile='invoices.xlsx',
        )
        if path:
            self.excel_path = path
            self.excel_label.configure(text=os.path.basename(path))
            self.status.set(f"Excel target: {path}", ACCENT2)


def main():
    import sys
    data_dir = os.path.join(os.path.expanduser('~'), 'Racuni')
    os.makedirs(data_dir, exist_ok=True)
    app = App(data_dir=data_dir)
    app.mainloop()


if __name__ == '__main__':
    main()
