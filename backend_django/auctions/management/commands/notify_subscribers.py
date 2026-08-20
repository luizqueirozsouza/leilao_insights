from __future__ import annotations

import json
import logging
from datetime import date

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from backend_django.auctions.models import (
    Auction,
    NotificacaoEnviada,
    PreferenciaAlerta,
)
from backend_django.auctions.notifiers import EmailNotifier, WhatsAppNotifier

logger = logging.getLogger("auctions.notify")


def _pref_casa(pref: PreferenciaAlerta, imovel: Auction) -> bool:
    if pref.uf and pref.uf.upper() != (imovel.uf or "").upper():
        return False
    if pref.cidades and (imovel.cidade or "").strip() not in pref.cidades:
        return False
    if pref.bairros and (imovel.bairro or "").strip() not in pref.bairros:
        return False
    if pref.modalidades and (imovel.modalidade or "").strip() not in pref.modalidades:
        return False
    return True


def _descrever_evento(tipo_evento: str) -> str:
    return {
        "ENTER": "Novo imóvel adicionado",
        "EXIT": "Imóvel removido",
        "UPDATE": "Imóvel atualizado",
    }.get(tipo_evento, tipo_evento)


def _montar_mensagem(evento: dict, imovel: Auction | None) -> str:
    base = _descrever_evento(evento["tipo_evento"])
    linhas = [f"🔔 {base}"]
    linhas.append(f"Imóvel: {evento['numero_imovel']} ({evento['uf']})")
    if imovel:
        if imovel.cidade:
            linhas.append(f"Cidade: {imovel.cidade}")
        if imovel.bairro:
            linhas.append(f"Bairro: {imovel.bairro}")
        if imovel.modalidade:
            linhas.append(f"Modalidade: {imovel.modalidade}")
        if imovel.tipo_imovel:
            linhas.append(f"Tipo: {imovel.tipo_imovel}")
        if imovel.preco is not None:
            linhas.append(f"Preço: R$ {imovel.preco}")
        if imovel.link:
            linhas.append(f"Detalhes: {imovel.link}")
    return "\n".join(linhas)


def _preferencias_ativas() -> list[PreferenciaAlerta]:
    from django.db.models import Q

    qs = PreferenciaAlerta.objects.filter(usuario__assinatura__ativa=True).select_related("usuario")
    agora = date.today()
    qs = qs.filter(
        Q(usuario__assinatura__data_fim__isnull=True)
        | Q(usuario__assinatura__data_fim__gte=agora)
    )
    return list(qs)


class Command(BaseCommand):
    help = "Dispara notificacoes de alerta para assinantes com base nos eventos de mudanca do dia."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="Data em YYYY-MM-DD. Padrao: hoje.")
        parser.add_argument("--dry-run", action="store_true", help="Nao envia, apenas lista o que seria enviado.")

    def handle(self, *args, **options):
        dt = options.get("date") or date.today().isoformat()
        dry_run = options.get("dry_run", False)

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT uf, numero_imovel, tipo_evento, after_json
                FROM changes
                WHERE dt = %s
                """,
                (dt,),
            )
            eventos = [
                {"uf": r[0], "numero_imovel": r[1], "tipo_evento": r[2], "after_json": r[3]}
                for r in cur.fetchall()
            ]

        if not eventos:
            self.stdout.write(f"Nenhum evento em changes para {dt}.")
            return

        numeros = {(e["uf"], e["numero_imovel"]) for e in eventos}
        imoveis = {}
        for a in Auction.objects.filter(
            uf__in=[n[0] for n in numeros], numero_imovel__in=[n[1] for n in numeros]
        ):
            imoveis[(a.uf, a.numero_imovel)] = a

        preferencias = _preferencias_ativas()
        notifiers = [EmailNotifier(), WhatsAppNotifier()]
        whatsup = notifiers[1]

        enviados = 0
        sem_match = 0

        for evento in eventos:
            chave = (evento["uf"], evento["numero_imovel"])
            imovel = imoveis.get(chave)

            for pref in preferencias:
                if imovel:
                    if not _pref_casa(pref, imovel):
                        continue
                else:
                    # Imovel nao esta mais em current_imoveis (ex. EXIT);
                    # casa apenas pela UF quando a preferencia nao restringe outros campos.
                    if pref.uf and pref.uf.upper() != evento["uf"].upper():
                        continue
                    if pref.cidades or pref.bairros or pref.modalidades:
                        continue

                ja_enviado = NotificacaoEnviada.objects.filter(
                    preferencia=pref,
                    numero_imovel=evento["numero_imovel"],
                    uf=evento["uf"],
                    tipo_evento=evento["tipo_evento"],
                    dt=dt,
                ).exists()
                if ja_enviado:
                    continue

                mensagem = _montar_mensagem(evento, imovel)
                canais_ok = []
                if pref.canal_email and pref.usuario.email:
                    canais_ok.append("email")
                    if not dry_run:
                        EmailNotifier().enviar(
                            pref.usuario.email,
                            f"Alerta de leilão — {_descrever_evento(evento['tipo_evento'])}",
                            mensagem,
                        )
                if pref.canal_whatsapp and pref.contato_whatsapp:
                    canais_ok.append("whatsapp")
                    if not dry_run:
                        whatsup.enviar(pref.contato_whatsapp, "", mensagem)

                if not dry_run and canais_ok:
                    with transaction.atomic():
                        NotificacaoEnviada.objects.create(
                            preferencia=pref,
                            tipo_evento=evento["tipo_evento"],
                            numero_imovel=evento["numero_imovel"],
                            uf=evento["uf"],
                            dt=dt,
                            canais=canais_ok,
                        )
                enviados += 1
                self.stdout.write(
                    f"[{'DRY' if dry_run else 'ENV'}][{evento['tipo_evento']}] "
                    f"{evento['uf']}/{evento['numero_imovel']} -> {pref.usuario.email} ({','.join(canais_ok)})"
                )

        self.stdout.write(
            self.style.SUCCESS(f"Concluido: {enviados} notificacoes ({'dry-run' if dry_run else 'enviadas'}).")
        )
