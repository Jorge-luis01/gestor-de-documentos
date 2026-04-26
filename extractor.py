import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class PdfExtractionError(Exception):
    pass


def _clean_text(text: str) -> str:
    if not text or text.lower() == "none":
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if text == "" or text == "-":
        return 0.0
    text = text.replace("R$", "").replace("D", "").replace("C", "").replace("-", "").strip()
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        parts = text.split(",")
        if len(parts[-1]) == 2 and len(parts) == 2:
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "." in text:
        parts = text.split(".")
        if len(parts[-1]) != 2 or len(parts) > 2:
            text = text.replace(".", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _find_col(headers: List[str], names: List[str]) -> Optional[int]:
    for name in names:
        for idx, header in enumerate(headers):
            if name.upper() in header.upper():
                return idx
    return None


def _merge_multiline_history(tables: List[List[List[str]]]) -> List[Dict[str, Any]]:
    raw_data: List[Dict[str, Any]] = []
    for table in tables:
        if not table or len(table) < 2:
            continue
        headers = [_clean_text(str(h)) for h in table[0]]
        dia_idx = _find_col(headers, ["DIA", "DATA", "Dia"])
        hist_idx = _find_col(headers, ["HISTÓRICO", "HISTORICO", "DESCRIÇÃO", "DESCRICAO"])
        deb_idx = _find_col(headers, ["DÉBITOS", "DEBITOS", "DÉBITO", "DEBITO", "SAÍDAS"])
        cred_idx = _find_col(headers, ["CRÉDITOS", "CREDITOS", "CRÉDITO", "CREDITO", "ENTRADAS"])
        max_idx = max(filter(None, [dia_idx, hist_idx, deb_idx, cred_idx]), default=-1)

        last_row: Optional[Dict[str, Any]] = None
        for row in table[1:]:
            if len(row) < max_idx + 1:
                continue
            has_dia = dia_idx is not None and _clean_text(str(row[dia_idx])) != ""
            if has_dia:
                reg: Dict[str, Any] = {}
                if dia_idx is not None:
                    reg["DIA"] = _clean_text(str(row[dia_idx]))
                if hist_idx is not None:
                    reg["HISTÓRICO"] = _clean_text(str(row[hist_idx]))
                if deb_idx is not None:
                    reg["DÉBITOS"] = _parse_float(row[deb_idx])
                if cred_idx is not None:
                    reg["CRÉDITOS"] = _parse_float(row[cred_idx])
                raw_data.append(reg)
                last_row = reg
            else:
                if last_row is not None and hist_idx is not None:
                    extra = _clean_text(str(row[hist_idx]))
                    if extra:
                        last_row["HISTÓRICO"] += " " + extra
    return raw_data


def extract_tables(file_path: Path) -> pd.DataFrame:
    logger.info(f"Extraindo tabelas do PDF: {file_path}")
    tables: List[List[List[str]]] = []
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            if not pdf.pages:
                raise PdfExtractionError("PDF não contém páginas.")
            for page in pdf.pages:
                page_tables = page.extract_tables()
                if page_tables:
                    tables.extend(page_tables)
    except Exception as e:
        raise PdfExtractionError(f"Erro na extração: {e}")

    raw_data = _merge_multiline_history(tables)
    if not raw_data:
        raise PdfExtractionError("Nenhuma tabela com dados financeiros encontrada.")

    df = pd.DataFrame(raw_data)
    for col in ["DÉBITOS", "CRÉDITOS"]:
        if col not in df.columns:
            df[col] = 0.0

    df = df[
        (df["DÉBITOS"] != 0)
        | (df["CRÉDITOS"] != 0)
        | (df["HISTÓRICO"].astype(str).str.strip() != "")
    ].reset_index(drop=True)

    logger.info(f"Extração concluída: {len(df)} registros.")
    return df
