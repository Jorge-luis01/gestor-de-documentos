import logging
import shutil
from pathlib import Path
from typing import Tuple

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


class BalanceMismatchError(Exception):
    pass


def clean_and_validate(
    df: pd.DataFrame, expected_balance: float, year: int = 2025
) -> Tuple[pd.DataFrame, float, float, float]:
    logger.info("Iniciando sanitização e validação.")

    df = df.copy()
    df["DÉBITOS"] = df["DÉBITOS"].astype(float)
    df["CRÉDITOS"] = df["CRÉDITOS"].astype(float)

    df["DATA"] = df["DIA"].astype(str).str.zfill(2) + f"/{year}"
    df["DATA_ISO"] = f"{year}-" + df["DIA"].astype(str).str.zfill(2) + "-01"

    total_debitos = df["DÉBITOS"].sum()
    total_creditos = df["CRÉDITOS"].sum()
    saldo_calculado = total_creditos - total_debitos

    logger.info(f"Débitos={total_debitos:.2f} | Créditos={total_creditos:.2f} | Saldo={saldo_calculado:.2f}")

    diferenca = abs(saldo_calculado - expected_balance)
    if diferenca >= 0.01:
        logger.error(f"Saldo divergente. Esperado={expected_balance:.2f} | Calculado={saldo_calculado:.2f}")
        raise BalanceMismatchError(
            f"Saldo divergente: esperado {expected_balance:.2f}, calculado {saldo_calculado:.2f} "
            f"(diferença {diferenca:.2f})"
        )

    logger.info("Validação de saldo aprovada.")
    return df, total_debitos, total_creditos, saldo_calculado


def archive_file(source_path: Path, destination_dir: Path, new_filename: str) -> Path:
    logger.info(f"Arquivando {source_path} em {destination_dir}")
    destination_dir.mkdir(parents=True, exist_ok=True)
    dest = destination_dir / new_filename

    try:
        shutil.copy2(str(source_path), str(dest))
        logger.info(f"Arquivo copiado para {dest}")
    except Exception as e:
        logger.error(f"Falha ao copiar arquivo: {e}")
        raise
    return dest
