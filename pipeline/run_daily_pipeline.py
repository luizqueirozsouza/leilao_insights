from __future__ import annotations

import argparse
import html
import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from extrai import UFS, configure_logging as configure_extract_logging
from pipeline.ingest_dlt import ingest_day_dlt
from pipeline.notify_telegram import send_telegram_message

load_dotenv()


def _resolve_run_date(explicit_date: str | None) -> str:
    if explicit_date:
        return explicit_date
    tz_name = os.getenv("PIPELINE_TZ", "America/Sao_Paulo")
    return datetime.now(ZoneInfo(tz_name)).date().isoformat()


def _extract_for_date(dt: str, delay: float, timeout: int) -> dict:
    from extrai import create_session, download_csv

    logger = logging.getLogger("pipeline.extract")
    root = Path("data") / "caixa" / f"dt={dt}"
    ok: list[str] = []
    fail: list[tuple[str, str]] = []
    session = create_session(timeout, logger)

    try:
        try:
            download_csv("geral", root / "UF=geral", timeout, logger, session=session)
        except Exception as exc:
            logger.warning("Falha ao baixar CSV geral: %s", exc)

        for uf in UFS:
            try:
                download_csv(uf, root / f"UF={uf}", timeout, logger, session=session)
                ok.append(uf)
                if delay > 0:
                    time.sleep(delay)
            except Exception as exc:
                logger.exception("Falha ao baixar UF=%s", uf)
                fail.append((uf, str(exc)))
    finally:
        session.close()

    if fail:
        raise RuntimeError(f"Extracao com falhas em {len(fail)} UFs: {fail}")

    return {"ufs_ok": len(ok)}


def _format_success_message(dt: str, elapsed: float, summary: dict) -> str:
    return (
        "<b>Pipeline Leilao: sucesso</b>\n"
        f"Data: <code>{dt}</code>\n"
        f"Duracao: <code>{elapsed:.2f}s</code>\n"
        f"Rows: <code>{summary.get('rows_processed', 0)}</code>\n"
        f"ENTER: <code>{summary.get('enter_count', 0)}</code> | "
        f"EXIT: <code>{summary.get('exit_count', 0)}</code> | "
        f"UPDATE: <code>{summary.get('update_count', 0)}</code>"
    )


def _format_error_message(dt: str, stage: str, exc: Exception) -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    safe_error = html.escape(str(exc)[:1200])
    return (
        "<b>Pipeline Leilao: falha</b>\n"
        f"Data: <code>{dt}</code>\n"
        f"Etapa: <code>{stage}</code>\n"
        f"Horario: <code>{now}</code>\n"
        f"Erro: <code>{safe_error}</code>"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orquestrador diario: extrai + ingestao DLT + Telegram."
    )
    parser.add_argument("--date", type=str, help="Data no formato YYYY-MM-DD.")
    parser.add_argument("--verbose", action="store_true", help="Logs detalhados.")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay entre UFs.")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout HTTP.")
    parser.add_argument(
        "--keep-csv",
        action="store_true",
        help="Mantem CSVs apos ingestao concluida.",
    )
    parser.add_argument(
        "--skip-telegram",
        action="store_true",
        help="Nao envia notificacoes Telegram.",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Pula a etapa de download/extracao dos CSVs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logger = configure_extract_logging(args.verbose)
    started_at = time.perf_counter()
    dt = _resolve_run_date(args.date)

    logger.info("Iniciando pipeline diario para %s", dt)
    logger.info("Timezone configurada: %s", os.getenv("PIPELINE_TZ", "America/Sao_Paulo"))

    try:
        if not args.skip_extract:
            _extract_for_date(dt, args.delay, args.timeout)
            logger.info("Extracao concluida com sucesso")
        else:
            logger.info("Etapa de extracao pulada devido a flag --skip-extract")

        summary = ingest_day_dlt(dt, logger, delete_csv=not args.keep_csv)
        logger.info("Ingestao DLT concluida: %s", json.dumps(summary, ensure_ascii=False))

        elapsed = time.perf_counter() - started_at
        if not args.skip_telegram:
            send_telegram_message(
                _format_success_message(dt, elapsed, summary),
                logger,
                disable_notification=True,
            )
        return 0
    except Exception as exc:
        logger.exception("Pipeline diario falhou")
        if not args.skip_telegram:
            try:
                send_telegram_message(_format_error_message(dt, "pipeline", exc), logger)
            except Exception:
                logger.exception("Falha ao enviar alerta Telegram")
        return 1


if __name__ == "__main__":
    sys.exit(main())
