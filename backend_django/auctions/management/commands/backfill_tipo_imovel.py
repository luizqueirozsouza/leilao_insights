import sys
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pipeline.utils import classify_tipo

from backend_django.auctions.models import Auction


class Command(BaseCommand):
    help = "Preenche tipo_imovel dos imoveis existentes usando a regra deterministica."

    def handle(self, *args, **options):
        total = 0
        atualizados = 0
        batch = []
        batch_size = 1000

        with transaction.atomic():
            for auction in Auction.objects.all().iterator(chunk_size=2000):
                total += 1
                tipo = classify_tipo(auction.descricao, auction.endereco)
                if auction.tipo_imovel != tipo:
                    auction.tipo_imovel = tipo
                    batch.append(auction)
                if len(batch) >= batch_size:
                    Auction.objects.bulk_update(batch, ['tipo_imovel'])
                    atualizados += len(batch)
                    batch = []

            if batch:
                Auction.objects.bulk_update(batch, ['tipo_imovel'])
                atualizados += len(batch)

        self.stdout.write(self.style.SUCCESS(
            f"Backfill concluido: {atualizados} de {total} imoveis atualizados."
        ))
