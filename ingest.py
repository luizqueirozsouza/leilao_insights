from __future__ import annotations

import argparse
import hashlib
import io
import json
import logging
import os
import re
import shutil
import sys
import time
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

load_dotenv()

BASE_DIR = Path("data") / "caixa"
EXPECTED_UFS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}


def snapshot_dir(dt: str) -> Path:
    return BASE_DIR / f"dt={dt}"

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


def configure_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("ingest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consolida os CSVs da Caixa e sincroniza o banco PostgreSQL."
    )
    parser.add_argument(
        "--date",
        default=datetime.now().date().isoformat(),
        help="Data do snapshot em YYYY-MM-DD. Padrao: hoje.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Habilita logs mais detalhados.",
    )
    parser.add_argument(
        "--delete-csv",
        action="store_true",
        help="Remove os CSVs do snapshot apos uma ingestao bem-sucedida.",
    )
    return parser.parse_args()


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


def ingest_day(dt: str, logger: logging.Logger, delete_csv: bool = False) -> dict:
    csvs = list_today_csvs(dt)
    if not csvs:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {BASE_DIR}/dt={dt}/UF=*/")

    logger.info("Iniciando ingestao para a data %s", dt)
    logger.info("Arquivos encontrados para ingestao: %s", len(csvs))
    validate_expected_csvs(csvs)
    logger.info("Validacao de cobertura por UF concluida com sucesso")

    dataframes = []
    total_rows_read = 0
    for csv_path in csvs:
        logger.info("Lendo arquivo %s", csv_path)
        frame = df_from_csv_file(csv_path)
        original_rows = len(frame)
        frame = normalize_df(frame)
        normalized_rows = len(frame)
        total_rows_read += normalized_rows
        logger.info(
            "Arquivo processado | uf=%s | linhas_lidas=%s | linhas_validas=%s",
            uf_from_path(csv_path),
            original_rows,
            normalized_rows,
        )
        dataframes.append(frame)

    today = pd.concat(dataframes, ignore_index=True)
    logger.info("Total consolidado antes do fingerprint: %s registros", len(today))
    today = add_fingerprint(today)

    def row_payload_dict(row: pd.Series) -> dict:
        return {
            col: (None if pd.isna(row.get(col)) else row.get(col))
            for col in PREFERRED_COLS
            if col in today.columns
        }

    today_payload = today.copy()
    today_payload["payload_json"] = today_payload.apply(
        lambda row: json.dumps(row_payload_dict(row), ensure_ascii=False),
        axis=1,
    )
    today_payload["numero_imovel"] = today_payload[KEY]
    today_payload["uf"] = today_payload["UF"]
    today_payload["dt"] = dt
    today_payload["fp"] = today_payload["_fp"]
    today_payload["source_file"] = today_payload.get("source_file", None)
    index_columns = today_payload.apply(build_index_columns, axis=1, result_type="expand")
    today_payload = pd.concat([today_payload, index_columns], axis=1)
    today_payload = today_payload.drop_duplicates(
        subset=["uf", "numero_imovel"], keep="first"
    ).copy()

    logger.info(
        "Payload final preparado | registros_unicos=%s | linhas_processadas=%s",
        len(today_payload),
        total_rows_read,
    )

    conn = get_db_connection()
    cur = conn.cursor()
    started_at = time.perf_counter()

    try:
        logger.info("Conexao com banco estabelecida")

        logger.info("Limpando snapshot e changes da data %s para garantir idempotencia", dt)
        cur.execute("DELETE FROM snapshot_imoveis WHERE dt = %s", (dt,))
        cur.execute("DELETE FROM changes WHERE dt = %s", (dt,))

        snapshot_rows = today_payload[
            ["dt", "uf", "numero_imovel", "payload_json", "fp", "source_file"]
        ].values.tolist()

        logger.info("Gravando snapshot do dia com %s registros", len(snapshot_rows))
        execute_values(
            cur,
            """
            INSERT INTO snapshot_imoveis (dt, uf, numero_imovel, payload_json, fp, source_file)
            VALUES %s
            """,
            snapshot_rows,
            page_size=1000,
        )

        logger.info("Registrando entradas (ENTER)")
        cur.execute(
            """
            INSERT INTO changes (dt, uf, tipo_evento, numero_imovel)
            SELECT %s, s.uf, 'ENTER', s.numero_imovel
            FROM snapshot_imoveis s
            LEFT JOIN current_imoveis c ON s.uf = c.uf AND s.numero_imovel = c.numero_imovel
            WHERE s.dt = %s AND c.numero_imovel IS NULL
            """,
            (dt, dt),
        )
        enter_count = cur.rowcount
        logger.info("Entradas registradas: %s", enter_count)

        logger.info("Registrando saidas (EXIT)")
        cur.execute(
            """
            INSERT INTO changes (dt, uf, tipo_evento, numero_imovel, before_json)
            SELECT %s, c.uf, 'EXIT', c.numero_imovel, c.payload_json
            FROM current_imoveis c
            LEFT JOIN snapshot_imoveis s ON c.uf = s.uf AND c.numero_imovel = s.numero_imovel AND s.dt = %s
            WHERE s.numero_imovel IS NULL
            """,
            (dt, dt),
        )
        exit_count = cur.rowcount
        logger.info("Saidas registradas: %s", exit_count)

        logger.info("Calculando atualizacoes (UPDATE)")
        cur.execute(
            """
            SELECT s.uf, s.numero_imovel, c.payload_json as before, s.payload_json as after
            FROM snapshot_imoveis s
            JOIN current_imoveis c ON s.uf = c.uf AND s.numero_imovel = c.numero_imovel
            WHERE s.dt = %s AND s.fp != c.fp
            """,
            (dt,),
        )
        updates = cur.fetchall()
        logger.info("Registros candidatos a UPDATE: %s", len(updates))

        changes_rows = []
        for uf, num, before, after in updates:
            changed_fields = compute_changed_fields(before, after)
            if not changed_fields:
                continue

            delta = {
                field: {"old": before.get(field), "new": after.get(field)}
                for field in changed_fields
            }
            changes_rows.append(
                (
                    dt,
                    uf,
                    "UPDATE",
                    num,
                    ",".join(changed_fields),
                    json.dumps(delta, ensure_ascii=False),
                )
            )

        if changes_rows:
            execute_values(
                cur,
                """
                INSERT INTO changes (
                    dt, uf, tipo_evento, numero_imovel, changed_fields, after_json
                ) VALUES %s
                """,
                changes_rows,
                page_size=1000,
            )
        logger.info("Updates efetivamente registrados: %s", len(changes_rows))

        logger.info("Sincronizando current_imoveis via UPSERT")
        current_rows = today_payload[
            [
                "uf",
                "numero_imovel",
                "payload_json",
                "fp",
                "dt",
                "source_file",
                "cidade",
                "bairro",
                "endereco",
                "preco",
                "valor_avaliacao",
                "desconto",
                "descricao",
                "modalidade",
                "link",
            ]
        ].values.tolist()
        execute_values(
            cur,
            """
            INSERT INTO current_imoveis (
                uf, numero_imovel, payload_json, fp, last_seen, source_file,
                cidade, bairro, endereco, preco, valor_avaliacao, desconto,
                descricao, modalidade, link
            )
            VALUES %s
            ON CONFLICT (uf, numero_imovel)
            DO UPDATE SET
                payload_json = EXCLUDED.payload_json,
                fp = EXCLUDED.fp,
                last_seen = EXCLUDED.last_seen,
                source_file = EXCLUDED.source_file,
                cidade = EXCLUDED.cidade,
                bairro = EXCLUDED.bairro,
                endereco = EXCLUDED.endereco,
                preco = EXCLUDED.preco,
                valor_avaliacao = EXCLUDED.valor_avaliacao,
                desconto = EXCLUDED.desconto,
                descricao = EXCLUDED.descricao,
                modalidade = EXCLUDED.modalidade,
                link = EXCLUDED.link
            """,
            current_rows,
            template=(
                "(%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            ),
            page_size=1000,
        )
        upsert_count = len(current_rows)
        logger.info("Registros afetados no UPSERT: %s", upsert_count)

        logger.info("Removendo registros orfaos ausentes no snapshot atual")
        cur.execute(
            """
            DELETE FROM current_imoveis
            WHERE (uf, numero_imovel) NOT IN (
                SELECT uf, numero_imovel FROM snapshot_imoveis WHERE dt = %s
            )
            """,
            (dt,),
        )
        deleted_count = cur.rowcount
        logger.info("Registros removidos de current_imoveis: %s", deleted_count)

        conn.commit()
        elapsed = time.perf_counter() - started_at
        logger.info("Ingestao concluida com sucesso em %.2fs", elapsed)

        cleanup_summary = {"csv_deleted": False, "csv_deleted_path": None}
        if delete_csv:
            try:
                cleanup_summary = cleanup_csv_snapshot(dt, logger)
            except Exception as exc:
                logger.warning(
                    "Ingestao concluida, mas a remocao dos CSVs falhou: %s",
                    exc,
                    exc_info=True,
                )
                cleanup_summary = {
                    "csv_deleted": False,
                    "csv_deleted_path": str(snapshot_dir(dt)),
                    "csv_cleanup_error": str(exc),
                }

        return {
            "dt": dt,
            "status": "success",
            "rows_processed": len(snapshot_rows),
            "enter_count": enter_count,
            "exit_count": exit_count,
            "update_count": len(changes_rows),
            "upsert_count": upsert_count,
            "deleted_count": deleted_count,
            "elapsed_seconds": round(elapsed, 2),
            **cleanup_summary,
        }
    except Exception:
        logger.exception("Falha durante a ingestao da data %s", dt)
        try:
            conn.rollback()
        except Exception:
            logger.exception("Falha ao executar rollback")
        raise
    finally:
        try:
            cur.close()
        except Exception:
            logger.debug("Cursor ja estava fechado", exc_info=True)
        try:
            conn.close()
        except Exception:
            logger.debug("Conexao ja estava fechada", exc_info=True)


def main() -> int:
    args = parse_args()
    logger = configure_logging(args.verbose)

    try:
        summary = ingest_day(args.date, logger, delete_csv=args.delete_csv)
        logger.info("Resumo final: %s", json.dumps(summary, ensure_ascii=False))
        return 0
    except Exception as exc:
        logger.error("Erro final da ingestao: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
