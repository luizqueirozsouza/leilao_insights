import sys
from pathlib import Path

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ingest import configure_logging, ingest_day  # noqa: E402


class Command(BaseCommand):
    help = "Ingere os CSVs ja baixados da Caixa e sincroniza o banco."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Data da ingestao no formato YYYY-MM-DD.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Habilita logs mais detalhados.",
        )
        parser.add_argument(
            "--keep-csv",
            action="store_true",
            help="Mantem os CSVs no disco apos uma ingestao bem-sucedida.",
        )

    def handle(self, *args, **options):
        dt = options["date"]
        verbose = options["verbose"]

        logger = configure_logging(verbose)
        logger.info("Executando comando Django ingest_auctions")

        try:
            summary = ingest_day(dt, logger, delete_csv=not options["keep_csv"])
        except Exception as exc:
            raise CommandError(f"Falha na ingestao: {exc}") from exc

        cache.clear()
        self.stdout.write(self.style.SUCCESS("Ingestao concluida com sucesso."))
        self.stdout.write(str(summary))
