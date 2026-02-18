from __future__ import annotations

import hashlib
import io
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# Carregar variáveis de ambiente
load_dotenv()

# =============================
# CONFIG
# =============================
BASE_DIR = Path("data") / "caixa"

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


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("host"),
        port=os.getenv("port"),
        user=os.getenv("user", "").replace('"', ""),
        password=os.getenv("password", "").replace('"', ""),
        database=os.getenv("database", "db_leiloes").replace('"', ""),
        sslmode=os.getenv("sslmode", "disable"),
    )


# =============================
# CSV PARSER
# =============================
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


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin1", errors="replace")


def find_header_line_index(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        score = 0
        low = line.lower()
        for m in HEADER_MARKERS:
            if m.lower() in low:
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

    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, [c for c in df.columns if c and not re.fullmatch(r"\s*", str(c))]]

    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        df.loc[df[c].isin(["nan", "None", ""]), c] = None

    # normaliza nomes (cobre Nº/N°/N etc)
    rename_map: dict[str, str] = {}
    for c in df.columns:
        cl = str(c).strip().lower()

        # chave
        if ("im" in cl) and (
            "mov" in cl
            or "mv" in cl
            or "movel" in cl
            or "mvel" in cl
            or "imvel" in cl
            or "imovel" in cl
        ):
            if (
                cl.startswith("n")
                or "n " in cl
                or "n°" in cl
                or "nº" in cl
                or "no" in cl
            ):
                rename_map[c] = "Nº do imóvel"

        # outros
        elif cl in ("preo", "preço") or ("pre" in cl and "co" in cl):
            rename_map[c] = "Preço"
        elif "valor" in cl and "avalia" in cl:
            rename_map[c] = "Valor de avaliação"
        elif "endere" in cl:
            rename_map[c] = "Endereço"
        elif "descri" in cl:
            rename_map[c] = "Descrição"
        elif "modalidade" in cl and "venda" in cl:
            rename_map[c] = "Modalidade de venda"
        elif "desconto" in cl:
            rename_map[c] = "Desconto"
        elif cl == "uf":
            rename_map[c] = "UF"
        elif "cidade" in cl:
            rename_map[c] = "Cidade"
        elif "bairro" in cl:
            rename_map[c] = "Bairro"
        elif "link" in cl:
            rename_map[c] = "Link de acesso"

    if rename_map:
        df = df.rename(columns=rename_map)

    if "UF" in df.columns:
        df["UF"] = df["UF"].str.upper().str.strip()

    return df


# =============================
# FINGERPRINT
# =============================
def fingerprint_row(row: pd.Series) -> str:
    parts = []
    for col in FIELDS_FOR_HASH:
        v = row.get(col, "")
        parts.append("" if v is None else str(v).strip())
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


# =============================
# IO
# =============================
def list_today_csvs(dt: str) -> list[Path]:
    day_dir = BASE_DIR / f"dt={dt}"
    if not day_dir.exists():
        return []
    return sorted(day_dir.glob("UF=*/Lista_imoveis_*.csv"))


def uf_from_path(p: Path) -> str:
    m = re.search(r"UF=([A-Z]{2}|geral)", str(p))
    if m:
        return m.group(1)
    m2 = re.search(r"Lista_imoveis_([A-Za-z]{2,5})\.csv", p.name)
    return (m2.group(1) if m2 else "NA").upper()


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


# =============================
# MAIN
# =============================
def ingest_day(dt: str) -> dict:
    csvs = list_today_csvs(dt)
    if not csvs:
        raise FileNotFoundError(f"Nenhum CSV encontrado em {BASE_DIR}/dt={dt}/UF=*/")

    dfs = []
    for p in csvs:
        d = df_from_csv_file(p)
        d = normalize_df(d)
        dfs.append(d)

    today = pd.concat(dfs, ignore_index=True)
    today = add_fingerprint(today)

    def row_payload_dict(row: pd.Series) -> dict:
        return {
            c: (None if pd.isna(row.get(c)) else row.get(c))
            for c in PREFERRED_COLS
            if c in today.columns
        }

    today_payload = today.copy()
    today_payload["payload_json"] = today_payload.apply(
        lambda r: json.dumps(row_payload_dict(r), ensure_ascii=False), axis=1
    )
    today_payload["numero_imovel"] = today_payload[KEY]
    today_payload["uf"] = today_payload["UF"]
    today_payload["dt"] = dt
    today_payload["fp"] = today_payload["_fp"]
    today_payload["source_file"] = today_payload.get("source_file", None)

    # ====== DEDUP FINAL ======
    today_payload = today_payload.drop_duplicates(
        subset=["uf", "numero_imovel"], keep="first"
    ).copy()

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Idempotência (limpar dados do dia anterior ao inserir de novo)
        cur.execute("DELETE FROM snapshot_imoveis WHERE dt = %s", (dt,))
        cur.execute("DELETE FROM changes WHERE dt = %s", (dt,))

        # 1. Inserir em snapshot_imoveis
        snapshot_rows = today_payload[
            ["dt", "uf", "numero_imovel", "payload_json", "fp", "source_file"]
        ].values.tolist()
        execute_values(
            cur,
            """
            INSERT INTO snapshot_imoveis (dt, uf, numero_imovel, payload_json, fp, source_file)
            VALUES %s
        """,
            snapshot_rows,
        )

        ydt = (datetime.fromisoformat(dt) - timedelta(days=1)).date().isoformat()

        # 2. Carregar ontem e hoje para comparação
        cur.execute(
            "SELECT uf, numero_imovel, payload_json, fp FROM snapshot_imoveis WHERE dt = %s",
            (ydt,),
        )
        y_rows = cur.fetchall()
        y = (
            pd.DataFrame(y_rows, columns=["uf", "numero_imovel", "payload_json", "fp"])
            if y_rows
            else pd.DataFrame(columns=["uf", "numero_imovel", "payload_json", "fp"])
        )

        cur.execute(
            "SELECT uf, numero_imovel, payload_json, fp FROM snapshot_imoveis WHERE dt = %s",
            (dt,),
        )
        t_rows = cur.fetchall()
        t = pd.DataFrame(t_rows, columns=["uf", "numero_imovel", "payload_json", "fp"])

        changes_rows = []

        if y.empty:
            entered = t.copy()
            exited = pd.DataFrame(columns=t.columns)
            updated = pd.DataFrame(
                columns=[
                    "uf",
                    "numero_imovel",
                    "fp_y",
                    "fp_t",
                    "before_json",
                    "after_json",
                ]
            )
        else:
            y["k"] = y["uf"].astype(str) + "::" + y["numero_imovel"].astype(str)
            t["k"] = t["uf"].astype(str) + "::" + t["numero_imovel"].astype(str)

            y_keys = set(y["k"])
            t_keys = set(t["k"])

            entered = t[t["k"].isin(t_keys - y_keys)].copy()
            exited = y[y["k"].isin(y_keys - t_keys)].copy()

            common = t_keys & y_keys
            y_common = y[y["k"].isin(common)][["k", "fp", "payload_json"]].rename(
                columns={"fp": "fp_y", "payload_json": "before_json"}
            )
            t_common = t[t["k"].isin(common)][
                ["k", "uf", "numero_imovel", "fp", "payload_json"]
            ].rename(columns={"fp": "fp_t", "payload_json": "after_json"})
            merged = t_common.merge(y_common, on="k", how="inner")
            updated = merged[merged["fp_y"] != merged["fp_t"]].copy()

        for _, r in entered.iterrows():
            changes_rows.append(
                (
                    dt,
                    r["uf"],
                    "ENTER",
                    r["numero_imovel"],
                    None,
                    None,
                    json.dumps(
                        r["payload_json"]
                        if isinstance(r["payload_json"], dict)
                        else json.loads(r["payload_json"]),
                        ensure_ascii=False,
                    ),
                )
            )

        for _, r in exited.iterrows():
            changes_rows.append(
                (
                    dt,
                    r["uf"],
                    "EXIT",
                    r["numero_imovel"],
                    None,
                    json.dumps(
                        r["payload_json"]
                        if isinstance(r["payload_json"], dict)
                        else json.loads(r["payload_json"]),
                        ensure_ascii=False,
                    ),
                    None,
                )
            )

        for _, r in updated.iterrows():
            before = (
                r["before_json"]
                if isinstance(r["before_json"], dict)
                else json.loads(r["before_json"])
            )
            after = (
                r["after_json"]
                if isinstance(r["after_json"], dict)
                else json.loads(r["after_json"])
            )
            changed_fields = compute_changed_fields(before, after)
            changes_rows.append(
                (
                    dt,
                    r["uf"],
                    "UPDATE",
                    r["numero_imovel"],
                    ",".join(changed_fields) if changed_fields else None,
                    json.dumps(before, ensure_ascii=False),
                    json.dumps(after, ensure_ascii=False),
                )
            )

        if changes_rows:
            execute_values(
                cur,
                """
                INSERT INTO changes (dt, uf, tipo_evento, numero_imovel, changed_fields, before_json, after_json)
                VALUES %s
            """,
                changes_rows,
            )

        # 3. Atualizar current_imoveis
        cur.execute(
            """
            DELETE FROM current_imoveis
            WHERE (uf, numero_imovel) IN (
                SELECT uf, numero_imovel FROM snapshot_imoveis WHERE dt = %s
            )
        """,
            (dt,),
        )

        current_rows = today_payload[
            ["uf", "numero_imovel", "payload_json", "fp", "dt", "source_file"]
        ].values.tolist()
        execute_values(
            cur,
            """
            INSERT INTO current_imoveis (uf, numero_imovel, payload_json, fp, last_seen, source_file)
            VALUES %s
        """,
            current_rows,
        )

        conn.commit()

        summary = {
            "dt": dt,
            "yesterday": ydt,
            "rows_today": int(len(t)),
            "entered": int(len(entered)),
            "exited": int(len(exited)),
            "updated": int(len(updated)),
            "status": "success",
        }
        return summary

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


def main():
    dt = datetime.now().date().isoformat()
    try:
        summary = ingest_day(dt)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
