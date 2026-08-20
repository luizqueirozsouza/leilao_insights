from __future__ import annotations

import logging
import re
from typing import Any

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("auctions.caixa_detail")

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


def _limpar(texto: str | None) -> str:
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto).strip()


def _campo_por_label(soup: BeautifulSoup, label: str) -> str:
    for span in soup.find_all("span"):
        txt = _limpar(span.get_text())
        if txt.startswith(label):
            strong = span.find("strong")
            if strong:
                return _limpar(strong.get_text())
    return ""


def _campo_area(soup: BeautifulSoup, label: str) -> str:
    for span in soup.find_all("span"):
        txt = _limpar(span.get_text())
        if txt.startswith(label) and "=" in txt:
            return _limpar(txt.split("=", 1)[1])
    return ""


def _extrair_regras(soup: BeautifulSoup) -> dict[str, Any]:
    regras = {"formas_pagamento": [], "regras_despesas": []}
    body = soup.get_text("\n")
    linhas = [l.strip() for l in body.split("\n") if l.strip()]

    em_formas = False
    em_despesas = False
    for linha in linhas:
        if "FORMAS DE PAGAMENTO ACEITAS" in linha.upper():
            em_formas = True
            em_despesas = False
            continue
        if "REGRAS PARA PAGAMENTO DAS DESPESAS" in linha.upper():
            em_formas = False
            em_despesas = True
            continue
        if em_formas:
            if "REGRAS" in linha.upper() or "CONDOMÍNIO" in linha.upper() or "TRIBUTOS" in linha.upper():
                continue
            if linha and not linha.startswith(("Condomínio", "Tributos")):
                regras["formas_pagamento"].append(linha)
        elif em_despesas:
            if linha.startswith(("Condomínio", "Tributos")):
                regras["regras_despesas"].append(linha)
    return regras


def parse_detalhe_html(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")

    dados = {
        "tipo_imovel": _campo_por_label(soup, "Tipo de imóvel") or None,
        "quartos": _campo_por_label(soup, "Quartos") or None,
        "garagem": _campo_por_label(soup, "Garagem") or None,
        "matricula": _campo_por_label(soup, "Matrícula") or None,
        "comarca": _campo_por_label(soup, "Comarca") or None,
        "oficio": _campo_por_label(soup, "Ofício") or None,
        "inscricao_imobiliaria": _campo_por_label(soup, "Inscrição imobiliária") or None,
        "area_privativa": _campo_area(soup, "Área privativa") or None,
        "area_terreno": _campo_area(soup, "Área do terreno") or None,
    }

    # Extras a partir do bloco relacionado
    relacionado = soup.find("div", class_="related-box")
    if relacionado:
        texto_rel = relacionado.get_text("\n")
        m_formas = re.search(r"FORMAS DE PAGAMENTO ACEITAS:(.*?)(REGRAS PARA PAGAMENTO|$)", texto_rel, re.S | re.I)
        if m_formas:
            dados["formas_pagamento"] = _limpar(m_formas.group(1)).strip("·")
        m_regras = re.search(r"REGRAS PARA PAGAMENTO DAS DESPESAS.*?:(.*?)(Corretores|$)", texto_rel, re.S | re.I)
        if m_regras:
            dados["regras_despesas"] = _limpar(m_regras.group(1)).strip("·")

    return dados


def buscar_detalhe(link: str, timeout: int = 30) -> dict[str, Any]:
    """Faz o fetch da pagina de detalhe da Caixa e retorna os dados extraidos."""
    if not link:
        raise ValueError("Imovel sem link de acesso.")

    response = requests.get(link, headers=BROWSER_HEADERS, timeout=timeout)
    response.raise_for_status()
    return parse_detalhe_html(response.text)
