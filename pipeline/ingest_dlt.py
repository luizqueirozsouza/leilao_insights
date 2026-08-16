from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import date
from typing import Any
from urllib.parse import quote_plus

import dlt
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.utils import (
    KEY,
    PREFERRED_COLS,
    add_fingerprint,
    build_index_columns,
    cleanup_csv_snapshot,
    compute_changed_fields,
    configure_logging,
    df_from_csv_file,
    get_db_connection,
    list_today_csvs,
    normalize_df,
    snapshot_dir,
    uf_from_path,
    validate_expected_csvs,
)


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or str(value).strip() == "":
        raise ValueError(f"Variavel de ambiente obrigatoria ausente: {name}")
    return str(value).strip().replace('"', "")


def _postgres_credentials() -> str:
    host = _env("host")
    port = _env("port", "5432")
    user = quote_plus(_env("user"))
    password = quote_plus(_env("password"))
    database = quote_plus(_env("database", "db_leiloes"))
    sslmode = _env("sslmode", "disable")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode={sslmode}"


def _build_today_payload(dt: str, logger: logging.Logger) -> tuple[pd.DataFrame, int]:
    csvs = list_today_csvs(dt)
    if not csvs:
        raise FileNotFoundError(f"Nenhum CSV encontrado em data/caixa/dt={dt}/UF=*/")

    logger.info("Iniciando ingestao DLT para a data %s", dt)
    logger.info("Arquivos encontrados para ingestao: %s", len(csvs))
    validate_expected_csvs(csvs)
    logger.info("Validacao de cobertura por UF concluida com sucesso")

    dataframes: list[pd.DataFrame] = []
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

    def row_payload_dict(row: pd.Series) -> dict[str, Any]:
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

    return today_payload, total_rows_read


def _load_snapshot_with_dlt(today_payload: pd.DataFrame, logger: logging.Logger) -> None:
    snapshot_rows = today_payload[
        ["dt", "uf", "numero_imovel", "payload_json", "fp", "source_file"]
    ].copy()

    records = snapshot_rows.to_dict(orient="records")
    if not records:
        logger.warning("Nenhum registro de snapshot para carregar.")
        return

    postgres_destination = dlt.destinations.postgres(
        credentials=_postgres_credentials()
    )

    pipeline = dlt.pipeline(
        pipeline_name=os.getenv("DLT_PIPELINE_NAME", "leilao_snapshot_daily_job"),
        destination=postgres_destination,
        dataset_name=os.getenv("DLT_DATASET_NAME", "public"),
    )

    info = pipeline.run(
        records,
        table_name="snapshot_imoveis_dlt",
        write_disposition="append",
    )
    logger.info("Carga DLT concluida na staging snapshot_imoveis_dlt: %s", info)


def ingest_day_dlt(dt: str, logger: logging.Logger, delete_csv: bool = False) -> dict[str, Any]:
    started_at = time.perf_counter()
    today_payload, total_rows_read = _build_today_payload(dt, logger)

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        logger.info("Conexao com banco estabelecida")

        logger.info("Limpando snapshot e changes da data %s para garantir idempotencia", dt)
        cur.execute("DELETE FROM snapshot_imoveis WHERE dt = %s", (dt,))
        cur.execute("DELETE FROM changes WHERE dt = %s", (dt,))
        try:
            cur.execute("DELETE FROM snapshot_imoveis_dlt WHERE dt = %s", (dt,))
            logger.info("Staging snapshot_imoveis_dlt limpa para dt=%s", dt)
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            cur = conn.cursor()
            cur.execute("DELETE FROM snapshot_imoveis WHERE dt = %s", (dt,))
            cur.execute("DELETE FROM changes WHERE dt = %s", (dt,))
            logger.info("Tabela snapshot_imoveis_dlt ainda nao existe; seguindo sem limpeza.")
        conn.commit()

        _load_snapshot_with_dlt(today_payload, logger)
        logger.info("Movendo dados da staging DLT para snapshot_imoveis")
        cur.execute(
            """
            INSERT INTO snapshot_imoveis (dt, uf, numero_imovel, payload_json, fp, source_file)
            SELECT src.dt::date, src.uf, src.numero_imovel, src.payload_json::jsonb, src.fp, src.source_file
            FROM (
                SELECT DISTINCT ON (uf, numero_imovel)
                    dt, uf, numero_imovel, payload_json, fp, source_file, _dlt_load_id
                FROM snapshot_imoveis_dlt
                WHERE dt = %s
                  AND payload_json IS NOT NULL
                ORDER BY uf, numero_imovel, _dlt_load_id DESC
            ) AS src
            """,
            (dt,),
        )
        logger.info("Registros inseridos em snapshot_imoveis via staging DLT: %s", cur.rowcount)

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
            template="(%s, %s, %s::jsonb, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
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
        logger.info("Ingestao DLT concluida com sucesso em %.2fs", elapsed)

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
            "rows_processed": len(today_payload),
            "rows_read": total_rows_read,
            "enter_count": enter_count,
            "exit_count": exit_count,
            "update_count": len(changes_rows),
            "upsert_count": upsert_count,
            "deleted_count": deleted_count,
            "elapsed_seconds": round(elapsed, 2),
            **cleanup_summary,
        }
    except Exception:
        logger.exception("Falha durante a ingestao DLT da data %s", dt)
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Ingestao via DLT dos CSVs da Caixa para PostgreSQL."
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
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
    args = parser.parse_args()

    logger = configure_logging(args.verbose)
    try:
        summary = ingest_day_dlt(args.date, logger, delete_csv=args.delete_csv)
        logger.info("Resumo final: %s", json.dumps(summary, ensure_ascii=False))
        return 0
    except Exception as exc:
        logger.error("Erro final da ingestao DLT: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
