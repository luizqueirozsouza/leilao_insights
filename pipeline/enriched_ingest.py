from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from psycopg2.extras import execute_values

from pipeline.utils import get_db_connection

ROOT_DIR = Path(__file__).resolve().parents[1]


def _refinar_tipo(tipo_texto: str | None) -> str | None:
    if not tipo_texto:
        return None
    t = str(tipo_texto).lower()
    if "apart" in t or "apto" in t or "flat" in t or "cobertura" in t or "kitnet" in t:
        return "apartamento"
    if "terreno" in t or "lote" in t or "gleba" in t or "chácara" in t or "sítio" in t or "rural" in t:
        return "terreno"
    if "casa" in t or "sobrado" in t or "vivenda" in t:
        return "casa"
    return None


def _carregar_enriquecidos(dt: str) -> dict[str, dict[str, Any]]:
    caminho = ROOT_DIR / "data" / "enriquecidos" / f"dt={dt}" / "enriquecidos.json"
    if not caminho.exists():
        return {}
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    return {k: v for k, v in dados.items() if isinstance(v, dict)}


def ingest_enriched(dt: str, logger: logging.Logger) -> dict[str, Any]:
    enriquecidos = _carregar_enriquecidos(dt)
    if not enriquecidos:
        logger.info("Nenhum dado enriquecido para %s.", dt)
        return {"dt": dt, "status": "no_data", "count": 0}

    conn = get_db_connection()
    cur = conn.cursor()
    agora = datetime.now()
    atualizados = 0
    try:
        rows = []
        for numero, dados in enriquecidos.items():
            dados_clean = {k: v for k, v in dados.items() if k != "_uf"}
            tipo_refinado = _refinar_tipo(dados.get("tipo_imovel"))
            rows.append((json.dumps(dados_clean, ensure_ascii=False), agora, tipo_refinado, numero))

        execute_values(
            cur,
            """
            UPDATE current_imoveis AS c SET
                dados_enriquecidos = v.dados::jsonb,
                dados_enriquecidos_at = v.agora,
                tipo_imovel = COALESCE(NULLIF(v.tipo, ''), c.tipo_imovel)
            FROM (VALUES %s) AS v(dados, agora, tipo, numero_imovel)
            WHERE c.numero_imovel = v.numero_imovel
            """,
            rows,
            template="(%s::jsonb, %s, %s, %s)",
            page_size=1000,
        )
        atualizados = cur.rowcount
        conn.commit()
        logger.info("Dados enriquecidos aplicados em %s imoveis.", atualizados)
        return {"dt": dt, "status": "success", "count": atualizados}
    except Exception:
        conn.rollback()
        logger.exception("Falha ao aplicar dados enriquecidos.")
        raise
    finally:
        cur.close()
        conn.close()
