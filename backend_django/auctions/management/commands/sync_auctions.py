import sys
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class Command(BaseCommand):
    help = "Executa extracao e ingestao em sequencia para atualizar a base."

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
        parser.add_argument(
            "--keep-csv",
            action="store_true",
            help="Mantem os CSVs no disco apos uma ingestao bem-sucedida.",
        )

    def handle(self, *args, **options):
        dt = options["date"]
        verbose = options["verbose"]

        self.stdout.write(self.style.WARNING(f"Iniciando sincronizacao para {dt}"))
        call_command(
            "extrai_auctions",
            date=dt,
            delay=options["delay"],
            timeout=options["timeout"],
            verbose=verbose,
        )
        call_command(
            "ingest_auctions",
            date=dt,
            verbose=verbose,
            keep_csv=options["keep_csv"],
        )
        self.stdout.write(self.style.SUCCESS("Sincronizacao concluida com sucesso."))
