import json
from datetime import date

import duckdb
import pandas as pd
import streamlit as st

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Imóveis Caixa - Viewer", layout="wide")
st.title("🏠 Imóveis Caixa — Viewer (DuckDB / current_imoveis)")

DB_PATH = "data/caixa.duckdb"

FIELDS_NUMERIC = {
    "Preço": "Preço_num",
    "Valor de avaliação": "Avaliação_num",
    "Desconto": "Desconto_num",  # mantemos parsing (útil na tabela), mas sem filtro
}

# =============================
# HELPERS
# =============================
def to_number_ptbr(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str)
    s = s.str.replace(".", "", regex=False)
    s = s.str.replace(",", ".", regex=False)
    s = s.str.replace(r"[^\d\.\-]", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


def safe_json_load(x):
    if x is None:
        return {}
    if isinstance(x, dict):
        return x
    try:
        return json.loads(x)
    except Exception:
        return {}


def normalize_key_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "UF" in df.columns:
        df["UF"] = df["UF"].astype(str).str.upper().str.strip()
    if "Cidade" in df.columns:
        df["Cidade"] = df["Cidade"].astype(str).str.strip()
    if "Bairro" in df.columns:
        df["Bairro"] = df["Bairro"].astype(str).str.strip()
    if "Nº do imóvel" in df.columns:
        df["Nº do imóvel"] = (
            df["Nº do imóvel"]
            .astype(str)
            .str.replace(r"\s+", "", regex=True)
            .str.strip()
        )
    return df


def apply_filters(
    df_in: pd.DataFrame,
    mod_sel: list[str],
    uf_sel: list[str],
    cidade_sel: list[str],
    bairro_sel: list[str],
    preco_min,
    preco_max,
) -> pd.DataFrame:
    f = df_in.copy()

    if mod_sel and "Modalidade de venda" in f.columns:
        f = f[f["Modalidade de venda"].isin(mod_sel)]

    if uf_sel and "UF" in f.columns:
        f = f[f["UF"].isin(uf_sel)]

    if cidade_sel and "Cidade" in f.columns:
        f = f[f["Cidade"].isin(cidade_sel)]

    if bairro_sel and "Bairro" in f.columns:
        f = f[f["Bairro"].isin(bairro_sel)]

    if preco_min is not None and "Preço_num" in f.columns:
        f = f[(f["Preço_num"] >= preco_min) & (f["Preço_num"] <= preco_max)]

    return f


# =============================
# LOAD FROM DUCKDB
# =============================
@st.cache_data(show_spinner=False)
def load_current_from_duckdb(db_path: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)

    base = con.execute("""
        SELECT
            uf,
            numero_imovel,
            payload_json,
            fp,
            last_seen,
            source_file
        FROM current_imoveis
    """).fetchdf()

    con.close()

    payload_dicts = base["payload_json"].apply(safe_json_load).tolist()
    payload_df = pd.json_normalize(payload_dicts)

    if "UF" not in payload_df.columns:
        payload_df["UF"] = base["uf"]

    if "Nº do imóvel" not in payload_df.columns:
        payload_df["Nº do imóvel"] = base["numero_imovel"]

    payload_df["fp"] = base["fp"]
    payload_df["last_seen"] = base["last_seen"]
    payload_df["source_file"] = base["source_file"]

    payload_df = normalize_key_cols(payload_df)

    for col, out_col in FIELDS_NUMERIC.items():
        if col in payload_df.columns:
            payload_df[out_col] = to_number_ptbr(payload_df[col])

    payload_df = payload_df.drop_duplicates(
        subset=["UF", "Nº do imóvel"], keep="first"
    ).copy()

    return payload_df


@st.cache_data(show_spinner=False)
def load_changes_by_day(db_path: str, dt: str) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    chg = con.execute("""
        SELECT
            dt,
            uf,
            tipo_evento,
            numero_imovel,
            changed_fields,
            before_json,
            after_json
        FROM changes
        WHERE dt = ?
    """, [dt]).fetchdf()
    con.close()
    return chg


def extract_payload_cols(chg_df: pd.DataFrame, which: str) -> pd.DataFrame:
    """
    which: 'before' ou 'after'
    """
    col = "before_json" if which == "before" else "after_json"
    base = chg_df.copy()
    payload_dicts = base[col].apply(safe_json_load).tolist()
    payload_df = pd.json_normalize(payload_dicts)

    if "UF" not in payload_df.columns and "uf" in base.columns:
        payload_df["UF"] = base["uf"]
    if "Nº do imóvel" not in payload_df.columns and "numero_imovel" in base.columns:
        payload_df["Nº do imóvel"] = base["numero_imovel"]

    payload_df = normalize_key_cols(payload_df)
    payload_df["tipo_evento"] = base.get("tipo_evento")
    payload_df["dt"] = base.get("dt")
    payload_df["changed_fields"] = base.get("changed_fields")

    for col_name, out_col in FIELDS_NUMERIC.items():
        if col_name in payload_df.columns:
            payload_df[out_col] = to_number_ptbr(payload_df[col_name])

    payload_df = payload_df.drop_duplicates(
        subset=["UF", "Nº do imóvel"], keep="first"
    ).copy()

    return payload_df


# =============================
# UI: LOAD
# =============================
try:
    df_current = load_current_from_duckdb(DB_PATH)
except Exception as e:
    st.error(f"Erro ao abrir DuckDB ({DB_PATH}): {e}")
    st.stop()

if df_current.empty:
    st.warning("Tabela current_imoveis está vazia. Rode o ingest primeiro.")
    st.stop()

st.success(f"Carregado do DuckDB: {len(df_current):,} imóveis".replace(",", "."))

hoje_str = date.today().isoformat()

# =============================
# SIDEBAR
# =============================
st.sidebar.header("Filtros")

# ✅ STATUS DO DIA (MULTI) — SUBIU
status_options = [
    "Todos (current)",
    "Adicionados hoje (ENTER)",
    "Removidos hoje (EXIT)",
    "Alterados hoje (UPDATE)",
]
status_sel = st.sidebar.multiselect(
    "Status do dia",
    status_options,
    default=["Todos (current)"],
)

# Modalidade (MULTI)
if "Modalidade de venda" in df_current.columns:
    modalidades = sorted([x for x in df_current["Modalidade de venda"].dropna().unique().tolist() if str(x).strip()])
    mod_sel = st.sidebar.multiselect("Modalidade de venda", modalidades, default=modalidades)
else:
    mod_sel = []

# UF (MULTI)
if "UF" in df_current.columns:
    ufs = sorted([x for x in df_current["UF"].dropna().unique().tolist() if str(x).strip()])
    uf_sel = st.sidebar.multiselect("UF", ufs, default=ufs)
else:
    uf_sel = []

# Cidade (MULTI) — base para bairro
if "Cidade" in df_current.columns:
    cidades_all = sorted([x for x in df_current["Cidade"].dropna().unique().tolist() if str(x).strip()])
    cidade_sel = st.sidebar.multiselect("Cidade", cidades_all, default=[])
else:
    cidade_sel = []

# Bairro (MULTI) — dependente da(s) cidade(s)
if "Bairro" in df_current.columns:
    if cidade_sel:
        bairros_pool = df_current[df_current["Cidade"].isin(cidade_sel)]["Bairro"]
    else:
        bairros_pool = df_current["Bairro"]
    bairros_all = sorted([x for x in bairros_pool.dropna().unique().tolist() if str(x).strip()])
    bairro_sel = st.sidebar.multiselect("Bairro", bairros_all, default=[])
else:
    bairro_sel = []

# Preço (slider)
preco_min = preco_max = None
if "Preço_num" in df_current.columns and df_current["Preço_num"].notna().any():
    pmin, pmax = float(df_current["Preço_num"].min()), float(df_current["Preço_num"].max())
    preco_min, preco_max = st.sidebar.slider("Preço (R$)", 0.0, pmax, (pmin, pmax))

# =============================
# DATASETS POR STATUS (E APLICA FILTROS)
# =============================
# Colunas base de exibição
cols_base = [
    "Nº do imóvel", "UF", "Cidade", "Bairro", "Endereço",
    "Preço", "Valor de avaliação", "Desconto",
    "Modalidade de venda", "Link de acesso",
]
cols_current_extra = ["last_seen", "source_file"]
cols_changes_extra = ["dt", "tipo_evento", "changed_fields"]

column_config = {}
if "Link de acesso" in df_current.columns:
    column_config["Link de acesso"] = st.column_config.LinkColumn("Link")

views = []  # lista de (titulo, df)

# Se o usuário não selecionar nada, cai num default seguro
if not status_sel:
    status_sel = ["Todos (current)"]

# 1) TODOS (current)
if "Todos (current)" in status_sel:
    cur_f = apply_filters(df_current, mod_sel, uf_sel, cidade_sel, bairro_sel, preco_min, preco_max)
    views.append(("📋 Todos (current_imoveis) — filtros aplicados", cur_f, "current"))

# Para os outros status, precisa carregar changes
need_changes = any(x in status_sel for x in ["Adicionados hoje (ENTER)", "Removidos hoje (EXIT)", "Alterados hoje (UPDATE)"])
chg = pd.DataFrame()
if need_changes:
    chg = load_changes_by_day(DB_PATH, hoje_str)

# 2) ENTER
if "Adicionados hoje (ENTER)" in status_sel:
    if chg.empty:
        ent_f = pd.DataFrame()
    else:
        ent = chg[chg["tipo_evento"] == "ENTER"].copy()
        ent_df = extract_payload_cols(ent, which="after") if not ent.empty else pd.DataFrame()
        ent_f = apply_filters(ent_df, mod_sel, uf_sel, cidade_sel, bairro_sel, preco_min, preco_max) if not ent_df.empty else pd.DataFrame()
    views.append(("🟢 Adicionados hoje (ENTER) — filtros aplicados", ent_f, "changes"))

# 3) EXIT
if "Removidos hoje (EXIT)" in status_sel:
    if chg.empty:
        ex_f = pd.DataFrame()
    else:
        ex = chg[chg["tipo_evento"] == "EXIT"].copy()
        ex_df = extract_payload_cols(ex, which="before") if not ex.empty else pd.DataFrame()
        ex_f = apply_filters(ex_df, mod_sel, uf_sel, cidade_sel, bairro_sel, preco_min, preco_max) if not ex_df.empty else pd.DataFrame()
    views.append(("🔴 Removidos hoje (EXIT) — filtros aplicados", ex_f, "changes"))

# 4) UPDATE
if "Alterados hoje (UPDATE)" in status_sel:
    if chg.empty:
        up_f = pd.DataFrame()
    else:
        up = chg[chg["tipo_evento"] == "UPDATE"].copy()
        up_df = extract_payload_cols(up, which="after") if not up.empty else pd.DataFrame()
        up_f = apply_filters(up_df, mod_sel, uf_sel, cidade_sel, bairro_sel, preco_min, preco_max) if not up_df.empty else pd.DataFrame()
    views.append(("🛠️ Alterados hoje (UPDATE) — filtros aplicados", up_f, "changes"))

# =============================
# RENDER
# =============================
# Contador geral (somatório do que está sendo mostrado)
total_rows = int(sum(len(v[1]) for v in views if v[1] is not None))
st.metric("Imóveis na lista", f"{total_rows:,}".replace(",", "."))

for title, dfx, kind in views:
    st.subheader(title)

    if dfx is None or dfx.empty:
        st.info("Nenhum registro para este status com os filtros atuais.")
        continue

    if kind == "current":
        cols_show = [c for c in (cols_base + cols_current_extra) if c in dfx.columns]
    else:
        cols_show = [c for c in (cols_base + cols_changes_extra) if c in dfx.columns]

    st.dataframe(
        dfx[cols_show],
        width='stretch',
        column_config=column_config,
    )