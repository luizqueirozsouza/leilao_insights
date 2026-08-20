from __future__ import annotations

import argparse
import concurrent.futures
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from pipeline.utils import configure_logging, list_today_csvs, df_from_csv_file, uf_from_path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BASE = "https://venda-imoveis.caixa.gov.br"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": f"{BASE}/",
    "Origin": BASE,
}

# Reusa o parser do backend (evita duplicacao de logica).
sys.path.insert(0, str(ROOT_DIR / "backend_django"))
from backend_django.auctions.caixa_detail import parse_detalhe_html  # noqa: E402


def criar_sessao(timeout: int, logger: logging.Logger) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(BROWSER_HEADERS)
    return session


def coletar_imoveis(dt: str, logger: logging.Logger) -> list[tuple[str, str]]:
    csvs = list_today_csvs(dt)
    imoveis: dict[str, str] = {}
    for csv_path in csvs:
        try:
            df = df_from_csv_file(csv_path)
        except Exception as exc:
            logger.warning("Falha ao ler %s: %s", csv_path, exc)
            continue
        uf = uf_from_path(csv_path)
        for _, row in df.iterrows():
            numero = str(row.get("Nº do imóvel") or "").strip()
            if not numero:
                continue
            imoveis[numero] = uf
    logger.info("Total de imoveis unicos no snapshot: %s", len(imoveis))
    return list(imoveis.items())


def enriquecer_um(item: tuple[str, str], session: requests.Session, timeout: int) -> tuple[str, dict | str]:
    numero, uf = item
    url = f"{BASE}/sistema/detalhe-imovel.asp?hdnimovel={numero}"
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        dados = parse_detalhe_html(response.text)
        dados["_uf"] = uf
        return numero, dados
    except Exception as exc:
        return numero, f"ERRO:{exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Enriquece imoveis do snapshot baixando a pagina de detalhe da Caixa.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Data do snapshot em YYYY-MM-DD.")
    parser.add_argument("--limit", type=int, default=5000, help="Maximo de imoveis a enriquecer nesta execucao.")
    parser.add_argument("--workers", type=int, default=8, help="Threads de download em paralelo.")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout HTTP por requisicao.")
    parser.add_argument("--rate", type=float, default=0.0, help="Delay extra (s) entre requisicoes, para nao ser bloqueado.")
    parser.add_argument("--verbose", action="store_true", help="Logs detalhados.")
    args = parser.parse_args()

    logger = configure_logging(args.verbose)

    imoveis = coletar_imoveis(args.date, logger)
    if args.limit > 0:
        imoveis = imoveis[: args.limit]
    logger.info("Enriquecendo %s imoveis (workers=%s)...", len(imoveis), args.workers)

    session = criar_sessao(args.timeout, logger)
    resultado: dict[str, dict | str] = {}
    sucesso = 0
    erro = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(enriquecer_um, item, session, args.timeout): item
            for item in imoveis
        }
        for future in concurrent.futures.as_completed(futures):
            numero, dados = future.result()
            if isinstance(dados, dict):
                sucesso += 1
            else:
                erro += 1
            resultado[numero] = dados
            if args.rate > 0:
                time.sleep(args.rate)
            if (sucesso + erro) % 250 == 0:
                logger.info("Progresso: %s ok / %s erro / total %s", sucesso, erro, sucesso + erro)

    out_dir = ROOT_DIR / "data" / "enriquecidos" / f"dt={args.date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "enriquecidos.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False)

    logger.info("Concluido: %s ok, %s erro. Arquivo: %s", sucesso, erro, out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
