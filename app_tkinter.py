import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

import pandas as pd

from extractor import extract_tables, PdfExtractionError
from processor import clean_and_validate, archive_file, BalanceMismatchError


# Carregar variáveis de ambiente
load_dotenv()

EXPECTED_BALANCE: float = float(os.getenv("EXPECTED_BALANCE", "0.0"))
ARCHIVE_DIR: Path = Path(os.getenv("ARCHIVE_DIR", "./archive/processed"))
YEAR: int = int(os.getenv("YEAR", "2025"))


def fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Gestor Financeiro PDF")
        self.root.geometry("1200x800")
        self.root.configure(bg="#020205")
        self.df = None

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#020205", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("TFrame", background="#020205")
        style.configure("TLabel", background="#020205", foreground="#ffffff", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Metric.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#667eea", foreground="#ffffff")
        style.map("TButton", background=[("active", "#764ba2")])

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(main, text="Gestor Financeiro PDF", style="Header.TLabel")
        header.pack(pady=(0, 5))
        ttk.Label(main, text="Extracao inteligente de extratos bancarios", foreground="#a0a0a0").pack(pady=(0, 15))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=10)
        ttk.Button(btn_frame, text="Selecionar PDF", command=self._select_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Exportar CSV", command=self._export_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Exportar Excel", command=self._export_excel).pack(side=tk.LEFT, padx=5)

        self.metrics_frame = ttk.Frame(main)
        self.metrics_frame.pack(fill=tk.X, pady=10)

        self.lbl_debitos = ttk.Label(self.metrics_frame, text="Debitos: -", style="Metric.TLabel", foreground="#ff6b6b")
        self.lbl_debitos.pack(side=tk.LEFT, expand=True)
        self.lbl_creditos = ttk.Label(self.metrics_frame, text="Creditos: -", style="Metric.TLabel", foreground="#51cf66")
        self.lbl_creditos.pack(side=tk.LEFT, expand=True)
        self.lbl_saldo = ttk.Label(self.metrics_frame, text="Saldo: -", style="Metric.TLabel", foreground="#339af0")
        self.lbl_saldo.pack(side=tk.LEFT, expand=True)

        cols = ("DATA", "HISTORICO", "DEBITOS", "CREDITOS")
        self.tree = ttk.Treeview(main, columns=cols, show="headings", height=25)
        for col in cols:
            self.tree.heading(col, text=col)
            if col == "HISTORICO":
                self.tree.column(col, width=600)
            elif col == "DATA":
                self.tree.column(col, width=80)
            else:
                self.tree.column(col, width=150, anchor="e")
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)

        scrollbar = ttk.Scrollbar(self.tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        footer = ttk.Label(main, text="PDF Automation Tool", foreground="#666666")
        footer.pack(pady=(10, 0))

    def _select_file(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if not path:
            return
        self._process(path)

    def _process(self, file_path: str):
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                with open(file_path, "rb") as src:
                    tmp.write(src.read())
                temp_path = Path(tmp.name)

            df_raw = extract_tables(temp_path)
            df, total_debitos, total_creditos, saldo = clean_and_validate(df_raw, EXPECTED_BALANCE, YEAR)

            self.df = df
            self.lbl_debitos.config(text=f"Debitos: {fmt_brl(total_debitos)}")
            self.lbl_creditos.config(text=f"Creditos: {fmt_brl(total_creditos)}")
            self.lbl_saldo.config(text=f"Saldo: {fmt_brl(saldo)}")

            for item in self.tree.get_children():
                self.tree.delete(item)

            for _, row in df.iterrows():
                self.tree.insert("", tk.END, values=(
                    row["DATA"],
                    row["HISTORICO"],
                    fmt_brl(row["DEBITOS"]),
                    fmt_brl(row["CREDITOS"]),
                ))

            dest = archive_file(temp_path, ARCHIVE_DIR, Path(file_path).name)
            messagebox.showinfo("Sucesso", f"Arquivo processado e arquivado em:\n{dest}")

        except PdfExtractionError as e:
            messagebox.showerror("Erro de Extracao", str(e))
        except BalanceMismatchError as e:
            messagebox.showerror("Erro de Validacao", str(e))
        except Exception as e:
            messagebox.showerror("Erro Inesperado", str(e))
        finally:
            if temp_path and temp_path.exists():
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def _export_csv(self):
        if self.df is None:
            messagebox.showwarning("Aviso", "Processe um PDF primeiro.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            self.df[["DATA", "HISTORICO", "DEBITOS", "CREDITOS"]].to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("Sucesso", f"CSV salvo em:\n{path}")

    def _export_excel(self):
        if self.df is None:
            messagebox.showwarning("Aviso", "Processe um PDF primeiro.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if path:
            self.df[["DATA", "HISTORICO", "DEBITOS", "CREDITOS"]].to_excel(path, index=False, sheet_name="Extrato")
            messagebox.showinfo("Sucesso", f"Excel salvo em:\n{path}")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
