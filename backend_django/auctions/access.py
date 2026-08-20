from backend_django.auctions.models import Assinatura, Auction


UFS_DEMO = ['SP', 'RJ', 'MG', 'RS', 'BA']
LIMITE_DEMO = 30
POR_UF_DEMO = LIMITE_DEMO // len(UFS_DEMO)


def usuario_tem_assinatura_ativa(user) -> bool:
    if user is None or not user.is_authenticated:
        return False
    assinatura = getattr(user, 'assinatura', None)
    return bool(assinatura and assinatura.esta_ativa)


def ver_amostra(request) -> bool:
    user = getattr(request, 'user', None)
    return not usuario_tem_assinatura_ativa(user)


def _amostra_queryset():
    ids = []
    for uf in UFS_DEMO:
        sub = list(
            Auction.objects.filter(uf=uf)
            .order_by('cidade', 'preco', 'numero_imovel')
            .values_list('id', flat=True)[:POR_UF_DEMO]
        )
        ids.extend(sub)
    return ids


def aplicar_modo_demo(qs, request):
    """Restringe o queryset a uma amostra deterministica quando o usuario
    nao possui assinatura ativa. Retorna (queryset, em_modo_demo)."""
    if not ver_amostra(request):
        return qs, False
    ids = _amostra_queryset()
    if ids:
        qs = qs.filter(id__in=ids)
    return qs, True
