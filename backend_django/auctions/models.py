from django.db import models
from django.conf import settings


class TipoImovel(models.TextChoices):
    APARTAMENTO = 'apartamento', 'Apartamento'
    CASA = 'casa', 'Casa'
    TERRENO = 'terreno', 'Terreno'
    OUTRO = 'outro', 'Outro'


class Auction(models.Model):
    uf = models.CharField(max_length=2, db_index=True, verbose_name="UF")
    numero_imovel = models.CharField(max_length=50, unique=True, verbose_name="Nº do Imóvel")
    cidade = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    bairro = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    endereco = models.TextField(null=True, blank=True)
    preco = models.DecimalField(max_digits=15, decimal_places=2, db_index=True, null=True, blank=True)
    valor_avaliacao = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    desconto = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, help_text="Percentual ou valor de desconto")
    descricao = models.TextField(null=True, blank=True)
    modalidade = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    link = models.URLField(max_length=1000, null=True, blank=True)
    tipo_imovel = models.CharField(
        max_length=20,
        choices=TipoImovel.choices,
        db_index=True,
        null=True,
        blank=True,
        verbose_name="Tipo de Imóvel",
    )
    dados_enriquecidos = models.JSONField(null=True, blank=True)
    dados_enriquecidos_at = models.DateTimeField(null=True, blank=True)

    payload_json = models.JSONField(null=True, blank=True)
    fingerprint = models.CharField(max_length=32, null=True, blank=True)
    last_seen = models.DateField(auto_now=True, db_index=True)
    source_file = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Leilão"
        verbose_name_plural = "Leilões"
        ordering = ['-last_seen', 'preco']
        db_table = 'current_imoveis'
        indexes = [
            models.Index(fields=['uf', 'cidade'], name='idx_uf_cidade'),
            models.Index(fields=['uf', 'cidade', 'bairro'], name='idx_uf_cidade_bairro'),
            models.Index(fields=['uf', 'modalidade'], name='idx_uf_modalidade'),
            models.Index(fields=['cidade', 'modalidade'], name='idx_cidade_modalidade'),
            models.Index(fields=['preco'], name='idx_preco'),
            models.Index(fields=['valor_avaliacao'], name='idx_valor_avaliacao'),
            models.Index(fields=['tipo_imovel'], name='idx_tipo_imovel'),
        ]

    def __str__(self):
        return f"{self.numero_imovel} - {self.cidade}/{self.uf}"


class Assinatura(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assinatura',
        verbose_name="Usuário",
    )
    ativa = models.BooleanField(default=False, verbose_name="Ativa")
    data_inicio = models.DateField(null=True, blank=True, verbose_name="Início")
    data_fim = models.DateField(null=True, blank=True, verbose_name="Fim (validade)")
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"

    @property
    def esta_ativa(self) -> bool:
        if not self.ativa:
            return False
        if self.data_fim and self.data_fim < self._hoje():
            return False
        return True

    @staticmethod
    def _hoje():
        from django.utils import timezone
        return timezone.localdate()

    def __str__(self):
        estado = "ativa" if self.esta_ativa else "inativa"
        return f"{self.usuario.email} — {estado}"


class PreferenciaAlerta(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='preferencias_alertas',
        verbose_name="Usuário",
    )
    uf = models.CharField(max_length=2, blank=True, default='', verbose_name="UF")
    cidades = models.JSONField(default=list, blank=True, verbose_name="Cidades")
    bairros = models.JSONField(default=list, blank=True, verbose_name="Bairros")
    modalidades = models.JSONField(default=list, blank=True, verbose_name="Modalidades")
    tipos = models.JSONField(default=list, blank=True, verbose_name="Tipos de imóvel")
    canal_email = models.BooleanField(default=True, verbose_name="Notificar por e-mail")
    canal_telegram = models.BooleanField(default=False, verbose_name="Notificar por Telegram")
    contato_telegram = models.CharField(max_length=100, blank=True, default='', verbose_name="Telegram (chat ID)")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Preferência de Alerta"
        verbose_name_plural = "Preferências de Alertas"

    def __str__(self):
        return f"Alerta de {self.usuario.email} (UF={self.uf or 'todas'})"


class NotificacaoEnviada(models.Model):
    class TipoEvento(models.TextChoices):
        ENTER = 'ENTER', 'Adição'
        EXIT = 'EXIT', 'Remoção'
        UPDATE = 'UPDATE', 'Alteração'

    preferencia = models.ForeignKey(
        PreferenciaAlerta,
        on_delete=models.CASCADE,
        related_name='notificacoes',
        verbose_name="Preferência",
    )
    tipo_evento = models.CharField(max_length=10, choices=TipoEvento.choices)
    numero_imovel = models.CharField(max_length=50)
    uf = models.CharField(max_length=2)
    dt = models.DateField()
    canais = models.JSONField(default=list, blank=True)
    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Notificação Enviada"
        verbose_name_plural = "Notificações Enviadas"
        constraints = [
            models.UniqueConstraint(
                fields=['preferencia', 'numero_imovel', 'uf', 'tipo_evento', 'dt'],
                name='uniq_notificacao_envio',
            ),
        ]

    def __str__(self):
        return f"{self.tipo_evento} {self.numero_imovel}/{self.uf} → {self.preferencia.usuario.email}"
