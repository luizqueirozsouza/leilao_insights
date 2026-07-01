from django.db import models


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
        ]

    def __str__(self):
        return f"{self.numero_imovel} - {self.cidade}/{self.uf}"
