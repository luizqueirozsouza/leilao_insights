from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.utils import validate_caixa_csv_bytes

BASE = "https://venda-imoveis.caixa.gov.br"
UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,application/octet-stream,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": f"{BASE}/",
    "Origin": BASE,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


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


def create_session(timeout: int, logger: logging.Logger) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(BROWSER_HEADERS)

    warmup_urls = [
        f"{BASE}/",
        f"{BASE}/sistema/detalhe-imovel.asp",
    ]
    for warmup_url in warmup_urls:
        try:
            response = session.get(warmup_url, timeout=timeout, allow_redirects=True)
            logger.debug(
                "Warm-up da sessao concluido | url=%s | status=%s",
                warmup_url,
                response.status_code,
            )
        except Exception:
            logger.debug("Warm-up falhou para %s", warmup_url, exc_info=True)

    return session


def download_csv(
    uf: str,
    out_dir: Path,
    timeout: int,
    logger: logging.Logger,
    session: requests.Session | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    cache_buster = int(time.time())
    url = f"{BASE}/listaweb/Lista_imoveis_{uf}.csv?{cache_buster}"
    file_path = out_dir / f"Lista_imoveis_{uf}.csv"

    logger.info("Baixando CSV da UF=%s", uf)
    logger.debug("URL de download: %s", url)

    started_at = time.perf_counter()
    owns_session = session is None
    active_session = session or create_session(timeout, logger)

    try:
        response = active_session.get(
            url,
            timeout=timeout,
            allow_redirects=True,
        )
        if response.status_code == 403:
            logger.warning(
                "Recebido 403 para UF=%s; renovando sessao e tentando novamente",
                uf,
            )
            if owns_session:
                active_session.close()
            active_session = create_session(timeout, logger)
            response = active_session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
            )

        response.raise_for_status()
        validate_caixa_csv_bytes(response.content)
        file_path.write_bytes(response.content)
    finally:
        if owns_session:
            active_session.close()

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
    session = create_session(args.timeout, logger)

    try:
        download_csv("geral", root / "UF=geral", args.timeout, logger, session=session)
    except Exception as exc:
        logger.warning("Falha ao baixar CSV geral: %s", exc)

    try:
        for index, uf in enumerate(UFS, start=1):
            logger.info("Processando UF %s/%s: %s", index, len(UFS), uf)
            try:
                path = download_csv(
                    uf,
                    root / f"UF={uf}",
                    args.timeout,
                    logger,
                    session=session,
                )
                ok.append((uf, path))
                if index < len(UFS) and args.delay > 0:
                    logger.debug("Aguardando %.2fs antes do proximo download", args.delay)
                    time.sleep(args.delay)
            except Exception as exc:
                logger.exception("Falha ao baixar UF=%s", uf)
                fail.append((uf, str(exc)))
    finally:
        session.close()

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
