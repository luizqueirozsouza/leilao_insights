from __future__ import annotations

from pathlib import Path
from datetime import datetime
import time
import requests

BASE = "https://venda-imoveis.caixa.gov.br"
UFS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
    "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"
]


def download_csv(uf: str, out_dir: Path, timeout: int = 60) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    # cache buster (timestamp)
    cb = int(time.time())
    url = f"{BASE}/listaweb/Lista_imoveis_{uf}.csv?{cb}"

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; CaixaCSVBot/1.0)",
        "Accept": "text/csv,text/plain,*/*",
        "Referer": f"{BASE}/",
    }

    with requests.Session() as s:
        r = s.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        r.raise_for_status()

        # alguns servidores mandam CSV como text/plain; ok
        file_path = out_dir / f"Lista_imoveis_{uf}.csv"
        file_path.write_bytes(r.content)
        return file_path

def main():
    dt = datetime.now().strftime("%Y-%m-%d")
    root = Path("data") / "caixa" / f"dt={dt}"

    # baixa geral (opcional)
    download_csv("geral", root / "UF=geral")

    # baixa por UF
    ok, fail = [], []
    for uf in UFS:
        try:
            path = download_csv(uf, root / f"UF={uf}")
            ok.append((uf, path))
            time.sleep(0.3)  # gentileza com o servidor
        except Exception as e:
            fail.append((uf, str(e)))

    print(f"OK: {len(ok)} | FAIL: {len(fail)}")
    if fail:
        for uf, err in fail:
            print("FAIL", uf, err)

if __name__ == "__main__":
    main()