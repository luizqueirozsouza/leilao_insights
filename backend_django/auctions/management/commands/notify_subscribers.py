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
from backend_django.auctions.notifiers import EmailNotifier, TelegramNotifier

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
    if pref.tipos and (imovel.tipo_imovel or "").strip() not in pref.tipos:
        return False
    return True


def _payload_value(payload: dict, *keys: str):
    for key in keys:
        value = payload.get(key)
        if value is not None and str(value).strip():
            return value
    return ""


def _pref_payload_casa(pref: PreferenciaAlerta, payload: dict, uf: str) -> bool:
    if pref.uf and pref.uf.upper() != (uf or "").upper():
        return False
    if pref.cidades and _payload_value(payload, "Cidade") not in pref.cidades:
        return False
    if pref.bairros and _payload_value(payload, "Bairro") not in pref.bairros:
        return False
    if pref.modalidades and _payload_value(payload, "Modalidade de venda") not in pref.modalidades:
        return False
    if pref.tipos and _payload_value(payload, "tipo_imovel", "Tipo de imóvel", "Tipo de imovel") not in pref.tipos:
        return False
    return True


def _descrever_evento(tipo_evento: str) -> str:
    return {
        "ENTER": "Novo imóvel adicionado",
        "EXIT": "Imóvel removido",
        "UPDATE": "Imóvel atualizado",
    }.get(tipo_evento, tipo_evento)


def _montar_mensagem(evento: dict, imovel: Auction | None, payload: dict | None = None) -> str:
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
    elif payload:
        for label, keys in (
            ("Cidade", ("Cidade",)),
            ("Bairro", ("Bairro",)),
            ("Modalidade", ("Modalidade de venda",)),
            ("Tipo", ("tipo_imovel", "Tipo de imóvel", "Tipo de imovel")),
            ("Preço", ("Preço", "Pre\u00e7o")),
            ("Detalhes", ("Link de acesso",)),
        ):
            value = _payload_value(payload, *keys)
            if value:
                linhas.append(f"{label}: {value}")
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
        parser.add_argument("--show-message", action="store_true", help="Exibe a mensagem completa de cada alerta.")

    def handle(self, *args, **options):
        dt = options.get("date") or date.today().isoformat()
        dry_run = options.get("dry_run", False)
        show_message = options.get("show_message", False)

        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT uf, numero_imovel, tipo_evento, before_json, after_json
                FROM changes
                WHERE dt = %s AND tipo_evento IN ('ENTER', 'EXIT')
                """,
                (dt,),
            )
            eventos = [
                {
                    "uf": r[0],
                    "numero_imovel": r[1],
                    "tipo_evento": r[2],
                    "before_json": r[3] or {},
                    "after_json": r[4] or {},
                }
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
        telegram = TelegramNotifier()

        enviados = 0
        sem_match = 0

        for evento in eventos:
            chave = (evento["uf"], evento["numero_imovel"])
            imovel = imoveis.get(chave)

            for pref in preferencias:
                payload = evento["before_json"] if evento["tipo_evento"] == "EXIT" else evento["after_json"]
                if imovel:
                    if not _pref_casa(pref, imovel):
                        continue
                else:
                    if not _pref_payload_casa(pref, payload, evento["uf"]):
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

                mensagem = _montar_mensagem(evento, imovel, payload)
                if show_message or dry_run:
                    self.stdout.write(f"\n--- Mensagem para {pref.usuario.email} ---\n{mensagem}\n--- Fim da mensagem ---")
                canais_ok = []
                if pref.canal_email and pref.usuario.email:
                    canais_ok.append("email")
                    if not dry_run:
                        EmailNotifier().enviar(
                            pref.usuario.email,
                            f"Alerta de leilão — {_descrever_evento(evento['tipo_evento'])}",
                            mensagem,
                        )
                if pref.canal_telegram and (pref.contato_telegram or telegram.default_chat_id):
                    canais_ok.append("telegram")
                    if not dry_run:
                        telegram.enviar(pref.contato_telegram, "", mensagem)

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
