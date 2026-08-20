from django.contrib import admin
from django.utils import timezone
from .models import Auction, Assinatura, PreferenciaAlerta, NotificacaoEnviada, TipoImovel

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('numero_imovel', 'cidade', 'uf', 'tipo_imovel', 'preco', 'desconto', 'last_seen')
    list_filter = ('uf', 'modalidade', 'tipo_imovel', 'last_seen')
    search_fields = ('numero_imovel', 'cidade', 'bairro', 'endereco')
    readonly_fields = ('fingerprint', 'last_seen', 'payload_json', 'dados_enriquecidos', 'dados_enriquecidos_at')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('numero_imovel', 'uf', 'cidade', 'bairro', 'endereco', 'tipo_imovel')
        }),
        ('Valores', {
            'fields': ('preco', 'valor_avaliacao', 'desconto', 'modalidade')
        }),
        ('Links e Descrição', {
            'fields': ('link', 'descricao')
        }),
        ('Metadados (Sistema)', {
            'classes': ('collapse',),
            'fields': ('fingerprint', 'last_seen', 'source_file', 'payload_json', 'dados_enriquecidos', 'dados_enriquecidos_at')
        }),
    )


@admin.register(Assinatura)
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'ativa', 'data_inicio', 'data_fim', 'status_display')
    list_filter = ('ativa',)
    search_fields = ('usuario__email',)

    @admin.display(description='Status')
    def status_display(self, obj):
        return "Ativa" if obj.esta_ativa else "Inativa"


@admin.register(PreferenciaAlerta)
class PreferenciaAlertaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'uf', 'canal_email', 'canal_whatsapp', 'criada_em')
    list_filter = ('uf', 'canal_email', 'canal_whatsapp')
    search_fields = ('usuario__email',)


@admin.register(NotificacaoEnviada)
class NotificacaoEnviadaAdmin(admin.ModelAdmin):
    list_display = ('tipo_evento', 'numero_imovel', 'uf', 'dt', 'preferencia', 'enviada_em')
    list_filter = ('tipo_evento', 'uf', 'dt')
    search_fields = ('numero_imovel', 'preferencia__usuario__email')
    readonly_fields = ('enviada_em',)
