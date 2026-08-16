from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import shutil
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path("data") / "caixa"
EXPECTED_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

KEY = "Nº do imóvel"

FIELDS_FOR_HASH = [
    "Preço",
    "Valor de avaliação",
    "Desconto",
    "Modalidade de venda",
    "Cidade",
    "Bairro",
]

PREFERRED_COLS = [
    "Nº do imóvel",
    "UF",
    "Cidade",
    "Bairro",
    "Endereço",
    "Preço",
    "Valor de avaliação",
    "Desconto",
    "Descrição",
    "Modalidade de venda",
    "Link de acesso",
]

HEADER_MARKERS = [
    "Nº do imóvel",
    "N° do imóvel",
    "N do imóvel",
    "No do imóvel",
    "N do imvel",
    "UF",
    "Cidade",
    "Bairro",
    "Endereço",
    "Endereo",
    "Preo",
    "Preço",
    "Valor de avalia",
    "Descri",
    "Modalidade",
    "Link",
]

CANONICAL_HEADER_MAP = {
    "Nº do imóvel": KEY,
    "N° do imóvel": KEY,
    "NÂº do imÃ³vel": KEY,
    "NÂ° do imÃ³vel": KEY,
    "Preço": "Preço",
    "PreÃ§o": "Preço",
    "Valor de avaliação": "Valor de avaliação",
    "Valor de avaliaÃ§Ã£o": "Valor de avaliação",
    "Endereço": "Endereço",
    "EndereÃ§o": "Endereço",
    "Descrição": "Descrição",
    "DescriÃ§Ã£o": "Descrição",
}


def snapshot_dir(dt: str) -> Path:
    return BASE_DIR / f"dt={dt}"


def configure_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("ingest")


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("host"),
        port=os.getenv("port"),
        user=os.getenv("user", "").replace('"', ""),
        password=os.getenv("password", "").replace('"', ""),
        database=os.getenv("database", "db_leiloes").replace('"', ""),
        sslmode=os.getenv("sslmode", "disable"),
    )


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin1", errors="replace")


def canonicalize_header(col: str) -> str:
    stripped = str(col).strip()
    if stripped in CANONICAL_HEADER_MAP:
        return CANONICAL_HEADER_MAP[stripped]

    lowered = stripped.lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("º", "o").replace("°", "o")
    normalized = re.sub(r"\s+", " ", normalized).strip()

    aliases = {
        "no do imovel": KEY,
        "n do imovel": KEY,
        "preco": "Preço",
        "valor de avaliacao": "Valor de avaliação",
        "endereco": "Endereço",
        "descricao": "Descrição",
    }
    return aliases.get(normalized, stripped)


def find_header_line_index(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        score = 0
        low = line.lower()
        for marker in HEADER_MARKERS:
            if marker.lower() in low:
                score += 1
        if score >= 3:
            return i
    return -1


def parse_caixa_csv_text(text: str) -> pd.DataFrame:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    header_idx = find_header_line_index(lines)
    if header_idx == -1:
        raise ValueError("Não encontrei a linha de cabeçalho (colunas).")

    csv_body = "\n".join(lines[header_idx:]).strip()

    df = pd.read_csv(
        io.StringIO(csv_body),
        sep=";",
        engine="python",
        dtype=str,
        skip_blank_lines=True,
    )

    df.columns = [canonicalize_header(str(c)) for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not re.fullmatch(r"\s*", str(c))]]

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["nan", "None", ""]), col] = None

    rename_map: dict[str, str] = {}
    for col in df.columns:
        normalized = str(col).strip().lower()

        if ("im" in normalized) and (
            "mov" in normalized
            or "mv" in normalized
            or "movel" in normalized
            or "mvel" in normalized
            or "imvel" in normalized
            or "imovel" in normalized
        ):
            if (
                normalized.startswith("n")
                or "n " in normalized
                or "n°" in normalized
                or "nº" in normalized
                or "no" in normalized
            ):
                rename_map[col] = "Nº do imóvel"
        elif normalized in ("preo", "preço") or ("pre" in normalized and "co" in normalized):
            rename_map[col] = "Preço"
        elif "valor" in normalized and "avalia" in normalized:
            rename_map[col] = "Valor de avaliação"
        elif "endere" in normalized:
            rename_map[col] = "Endereço"
        elif "descri" in normalized:
            rename_map[col] = "Descrição"
        elif "modalidade" in normalized and "venda" in normalized:
            rename_map[col] = "Modalidade de venda"
        elif "desconto" in normalized:
            rename_map[col] = "Desconto"
        elif normalized == "uf":
            rename_map[col] = "UF"
        elif "cidade" in normalized:
            rename_map[col] = "Cidade"
        elif "bairro" in normalized:
            rename_map[col] = "Bairro"
        elif "link" in normalized:
            rename_map[col] = "Link de acesso"

    if rename_map:
        df = df.rename(columns=rename_map)

    if "UF" in df.columns:
        df["UF"] = df["UF"].str.upper().str.strip()

    return df


def fingerprint_row(row: pd.Series) -> str:
    parts = []
    for col in FIELDS_FOR_HASH:
        value = row.get(col, "")
        parts.append("" if value is None else str(value).strip())
    raw = "||".join(parts).encode("utf-8", errors="ignore")
    return hashlib.md5(raw).hexdigest()


def add_fingerprint(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[KEY] = df[KEY].astype(str).str.replace(r"\s+", "", regex=True)
    df["_fp"] = df.apply(fingerprint_row, axis=1)
    return df


def compute_changed_fields(before: dict, after: dict) -> list[str]:
    changed = []
    for col in FIELDS_FOR_HASH:
        if str(before.get(col, "")).strip() != str(after.get(col, "")).strip():
            changed.append(col)
    return changed


def clean_money(value) -> Decimal | None:
    if value is None or pd.isna(value):
        return None

    raw = str(value).replace("R$", "").replace("%", "").strip()
    if not raw:
        return None

    if "." in raw and "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        raw = raw.replace(",", ".")

    normalized = re.sub(r"[^\d.\-]", "", raw)
    if normalized in {"", ".", "-", "-."}:
        return None

    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def build_index_columns(row: pd.Series) -> dict:
    preco = clean_money(row.get("Preço"))
    valor_avaliacao = clean_money(row.get("Valor de avaliação"))
    desconto = clean_money(row.get("Desconto"))

    if preco is not None and valor_avaliacao and valor_avaliacao > 0:
        desconto = ((valor_avaliacao - preco) / valor_avaliacao) * Decimal("100")
    if desconto is not None:
        desconto = desconto.quantize(Decimal("0.01"))

    return {
        "cidade": row.get("Cidade"),
        "bairro": row.get("Bairro"),
        "endereco": row.get("Endereço"),
        "preco": preco,
        "valor_avaliacao": valor_avaliacao,
        "desconto": desconto,
        "descricao": row.get("Descrição"),
        "modalidade": row.get("Modalidade de venda"),
        "link": row.get("Link de acesso"),
    }


def list_today_csvs(dt: str) -> list[Path]:
    day_dir = BASE_DIR / f"dt={dt}"
    if not day_dir.exists():
        return []
    return sorted(day_dir.glob("UF=*/Lista_imoveis_*.csv"))


def uf_from_path(csv_path: Path) -> str:
    match = re.search(r"UF=([A-Z]{2}|geral)", str(csv_path))
    if match:
        return match.group(1)
    fallback = re.search(r"Lista_imoveis_([A-Za-z]{2,5})\.csv", csv_path.name)
    return (fallback.group(1) if fallback else "NA").upper()


def df_from_csv_file(csv_path: Path) -> pd.DataFrame:
    text = decode_bytes(csv_path.read_bytes())
    df = parse_caixa_csv_text(text)

    if "UF" not in df.columns or df["UF"].isna().all():
        df["UF"] = uf_from_path(csv_path)

    df["source_file"] = csv_path.as_posix()
    return df


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in PREFERRED_COLS if c in df.columns]
    df = df[keep + [c for c in df.columns if c not in keep]].copy()

    if KEY not in df.columns and "N° do imóvel" in df.columns:
        df = df.rename(columns={"N° do imóvel": KEY})

    if KEY not in df.columns:
        raise ValueError(
            f"CSV sem coluna chave: {KEY}. Colunas recebidas: {list(df.columns)}"
        )

    df[KEY] = df[KEY].astype(str).str.replace(r"\s+", "", regex=True)
    df = df[df[KEY].notna() & (df[KEY].astype(str).str.len() > 0)].copy()
    df = df.drop_duplicates(subset=["UF", KEY], keep="first").copy()
    return df


def validate_expected_csvs(csvs: list[Path]) -> None:
    found_ufs = {uf_from_path(path) for path in csvs if uf_from_path(path) != "GERAL"}
    missing = sorted(EXPECTED_UFS - found_ufs)
    if missing:
        raise ValueError(
            "Ingest abortado: faltam CSVs de UF para atualizar com seguranca: "
            + ", ".join(missing)
        )


def cleanup_csv_snapshot(dt: str, logger: logging.Logger) -> dict:
    day_dir = snapshot_dir(dt)
    if not day_dir.exists():
        logger.info("Nenhum diretorio de CSV encontrado para remover: %s", day_dir)
        return {"csv_deleted": False, "csv_deleted_path": str(day_dir)}

    shutil.rmtree(day_dir)
    logger.info("Arquivos CSV removidos apos ingestao: %s", day_dir)
    return {"csv_deleted": True, "csv_deleted_path": str(day_dir)}
