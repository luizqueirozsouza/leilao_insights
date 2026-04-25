import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from extrai import configure_logging, download_csv, UFS  # noqa: E402


class Command(BaseCommand):
    help = "Baixa os CSVs de leiloes da Caixa para a data informada."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            required=True,
            type=str,
            help="Data do snapshot no formato YYYY-MM-DD.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=0.3,
            help="Intervalo entre downloads por UF em segundos.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=60,
            help="Timeout por requisicao em segundos.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Habilita logs mais detalhados.",
        )

    def handle(self, *args, **options):
        dt = options["date"]
        delay = options["delay"]
        timeout = options["timeout"]
        verbose = options["verbose"]

        logger = configure_logging(verbose)
        root = ROOT_DIR / "data" / "caixa" / f"dt={dt}"

        logger.info("Executando comando Django extrai_auctions para %s", dt)
        ok = []
        fail = []

        try:
            download_csv("geral", root / "UF=geral", timeout, logger)
        except Exception as exc:
            logger.warning("Falha ao baixar CSV geral: %s", exc)

        for index, uf in enumerate(UFS, start=1):
            logger.info("Processando UF %s/%s: %s", index, len(UFS), uf)
            try:
                path = download_csv(uf, root / f"UF={uf}", timeout, logger)
                ok.append((uf, path))
                if index < len(UFS) and delay > 0:
                    import time

                    time.sleep(delay)
            except Exception as exc:
                logger.exception("Falha ao baixar UF=%s", uf)
                fail.append((uf, str(exc)))

        if fail:
            for uf, err in fail:
                logger.error("UF com falha: %s | erro=%s", uf, err)
            raise CommandError(f"Extracao finalizada com falhas em {len(fail)} UFs.")

        self.stdout.write(
            self.style.SUCCESS(f"Extracao concluida com sucesso para {len(ok)} UFs.")
        )
