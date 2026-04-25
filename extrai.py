from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

BASE = "https://venda-imoveis.caixa.gov.br"
UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]


def configure_logging(verbose: bool = False) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    return logging.getLogger("extrai")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Baixa os CSVs de leiloes da Caixa para uma data de snapshot."
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Data do snapshot no formato YYYY-MM-DD. Padrao: hoje.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Intervalo entre downloads por UF em segundos. Padrao: 0.3.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Timeout por requisicao em segundos. Padrao: 60.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Habilita logs mais detalhados.",
    )
    return parser.parse_args()


def download_csv(
    uf: str,
    out_dir: Path,
    timeout: int,
    logger: logging.Logger,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    cache_buster = int(time.time())
    url = f"{BASE}/listaweb/Lista_imoveis_{uf}.csv?{cache_buster}"
    file_path = out_dir / f"Lista_imoveis_{uf}.csv"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CaixaCSVBot/1.0)",
        "Accept": "text/csv,text/plain,*/*",
        "Referer": f"{BASE}/",
    }

    logger.info("Baixando CSV da UF=%s", uf)
    logger.debug("URL de download: %s", url)

    started_at = time.perf_counter()
    with requests.Session() as session:
        response = session.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )
        response.raise_for_status()
        file_path.write_bytes(response.content)

    elapsed = time.perf_counter() - started_at
    size_kb = len(response.content) / 1024
    logger.info(
        "Download concluido para UF=%s | arquivo=%s | tamanho=%.1f KB | tempo=%.2fs",
        uf,
        file_path,
        size_kb,
        elapsed,
    )
    return file_path


def main() -> int:
    args = parse_args()
    logger = configure_logging(args.verbose)

    root = Path("data") / "caixa" / f"dt={args.date}"
    logger.info("Iniciando extracao de CSVs para a data %s", args.date)
    logger.info("Diretorio de destino: %s", root)

    started_at = time.perf_counter()
    ok: list[tuple[str, Path]] = []
    fail: list[tuple[str, str]] = []

    try:
        download_csv("geral", root / "UF=geral", args.timeout, logger)
    except Exception as exc:
        logger.warning("Falha ao baixar CSV geral: %s", exc)

    for index, uf in enumerate(UFS, start=1):
        logger.info("Processando UF %s/%s: %s", index, len(UFS), uf)
        try:
            path = download_csv(uf, root / f"UF={uf}", args.timeout, logger)
            ok.append((uf, path))
            if index < len(UFS) and args.delay > 0:
                logger.debug("Aguardando %.2fs antes do proximo download", args.delay)
                time.sleep(args.delay)
        except Exception as exc:
            logger.exception("Falha ao baixar UF=%s", uf)
            fail.append((uf, str(exc)))

    elapsed = time.perf_counter() - started_at
    logger.info(
        "Extracao finalizada | sucesso=%s | falhas=%s | tempo_total=%.2fs",
        len(ok),
        len(fail),
        elapsed,
    )

    if fail:
        for uf, err in fail:
            logger.error("UF com falha: %s | erro=%s", uf, err)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
