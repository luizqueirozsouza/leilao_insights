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
    return False


def _amostra_queryset():
    return []


def aplicar_modo_demo(qs, request):
    """Acesso liberado para todos (sem modo demo). Retorna (queryset, em_demo)."""
    return qs, False
