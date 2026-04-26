import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import tempfile
import re
from pathlib import Path
from datetime import datetime
from typing import Set, List

import pdfplumber


def extract_ids_from_pdf(file_path: str) -> Set[str]:
    ids = set()
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            found = re.findall(r"\b\d{8}\b", text)
            ids.update(found)
    return ids


def validate_ids(ids: Set[str]) -> List[str]:
    return [i for i in ids if i.isdigit() and len(i) == 8]


def find_files_by_id(source_dir: Path, id_str: str) -> List[Path]:
    return [f for f in source_dir.iterdir() if f.is_file() and id_str in f.name]


def copy_with_versioning(source: Path, dest_folder: Path) -> Path:
    dest_folder.mkdir(parents=True, exist_ok=True)
    dest = dest_folder / source.name
    if dest.exists():
        version = 1
        while True:
            versioned_name = f"{source.stem}_v{version}{source.suffix}"
            dest = dest_folder / versioned_name
            if not dest.exists():
                break
            version += 1
            if version > 999:
                raise RuntimeError("Limite de versionamento excedido.")
    shutil.copy2(str(source), str(dest))
    return dest


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Document-Driven File Routing")
        self.root.geometry("900x700")
        self.root.configure(bg="#020205")
        self.pdf_path = ""
        self.source_dir = Path(".")
        self.dest_dir = Path("./destination")

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background="#020205", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("TFrame", background="#020205")
        style.configure("TLabel", background="#020205", foreground="#ffffff", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#667eea", foreground="#ffffff")
        style.map("TButton", background=[("active", "#764ba2")])

        main = ttk.Frame(self.root, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(main, text="Document-Driven File Routing", style="Header.TLabel")
        header.pack(pady=(0, 5))
        ttk.Label(main, text="Extracao de IDs e roteamento automatico de arquivos", foreground="#a0a0a0").pack(pady=(0, 15))

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Selecionar PDF", command=self._select_pdf).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Pasta Fonte", command=self._select_source).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Pasta Destino", command=self._select_dest).pack(side=tk.LEFT, padx=5)

        self.lbl_pdf = ttk.Label(main, text="PDF: Nenhum selecionado", foreground="#999999")
        self.lbl_pdf.pack(anchor=tk.W, pady=2)
        self.lbl_source = ttk.Label(main, text="Fonte: ./", foreground="#999999")
        self.lbl_source.pack(anchor=tk.W, pady=2)
        self.lbl_dest = ttk.Label(main, text="Destino: ./destination", foreground="#999999")
        self.lbl_dest.pack(anchor=tk.W, pady=2)

        ttk.Button(main, text="Iniciar Roteamento", command=self._run).pack(pady=15)

        self.progress = ttk.Progressbar(main, orient=tk.HORIZONTAL, length=800, mode="determinate")
        self.progress.pack(pady=5)

        ttk.Label(main, text="Log de Operacoes:", foreground="#cccccc").pack(anchor=tk.W, pady=(10, 0))
        self.log_box = scrolledtext.ScrolledText(
            main, wrap=tk.WORD, height=20, bg="#0a0a0f", fg="#a0ffa0",
            insertbackground="#a0ffa0", font=("Consolas", 10), state=tk.DISABLED
        )
        self.log_box.pack(fill=tk.BOTH, expand=True, pady=5)

        footer = ttk.Label(main, text="PDF Automation Tool", foreground="#555555")
        footer.pack(pady=(10, 0))

    def _select_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.lbl_pdf.config(text=f"PDF: {path}")

    def _select_source(self):
        path = filedialog.askdirectory()
        if path:
            self.source_dir = Path(path)
            self.lbl_source.config(text=f"Fonte: {path}")

    def _select_dest(self):
        path = filedialog.askdirectory()
        if path:
            self.dest_dir = Path(path)
            self.lbl_dest.config(text=f"Destino: {path}")

    def _log(self, msg: str):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def _run(self):
        if not self.pdf_path:
            messagebox.showwarning("Aviso", "Selecione um PDF de referencia.")
            return

        self.progress["value"] = 0
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                with open(self.pdf_path, "rb") as src:
                    tmp.write(src.read())
                temp_path = Path(tmp.name)

            self._log("Extraindo IDs do PDF...")
            ids = extract_ids_from_pdf(str(temp_path))
            valid_ids = validate_ids(ids)

            if not valid_ids:
                self._log("Nenhum ID valido encontrado.")
                messagebox.showerror("Erro", "Nenhum ID de 8 digitos encontrado no PDF.")
                return

            self._log(f"IDs extraidos: {', '.join(valid_ids)}")

            total_ops = 0
            for id_str in valid_ids:
                total_ops += len(find_files_by_id(self.source_dir, id_str))

            if total_ops == 0:
                self._log("Nenhum arquivo correspondente encontrado na pasta fonte.")
                messagebox.showinfo("Info", "Nenhum arquivo correspondente encontrado.")
                return

            done = 0
            for id_str in valid_ids:
                files = find_files_by_id(self.source_dir, id_str)
                dest_folder = self.dest_dir / id_str
                for f in files:
                    dest = copy_with_versioning(f, dest_folder)
                    self._log(f"ID {id_str} -> Copiando {f.name}... OK")
                    done += 1
                    self.progress["value"] = (done / total_ops) * 100
                    self.root.update_idletasks()

            self._log("Roteamento concluido com sucesso.")
            messagebox.showinfo("Sucesso", f"{done} arquivo(s) copiado(s) com sucesso!")

        except Exception as e:
            self._log(f"ERRO: {str(e)}")
            messagebox.showerror("Erro", str(e))
        finally:
            if temp_path and temp_path.exists():
                try:
                    os.remove(temp_path)
                except Exception:
                    pass


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
