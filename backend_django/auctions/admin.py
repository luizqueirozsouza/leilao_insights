from django.contrib import admin
from .models import Auction

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ('numero_imovel', 'cidade', 'uf', 'preco', 'desconto', 'last_seen')
    list_filter = ('uf', 'modalidade', 'last_seen')
    search_fields = ('numero_imovel', 'cidade', 'bairro', 'endereco')
    readonly_fields = ('fingerprint', 'last_seen', 'payload_json')
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('numero_imovel', 'uf', 'cidade', 'bairro', 'endereco')
        }),
        ('Valores', {
            'fields': ('preco', 'valor_avaliacao', 'desconto', 'modalidade')
        }),
        ('Links e Descrição', {
            'fields': ('link', 'descricao')
        }),
        ('Metadados (Sistema)', {
            'classes': ('collapse',),
            'fields': ('fingerprint', 'last_seen', 'source_file', 'payload_json')
        }),
    )
