import re
import json

from django.shortcuts import render
from django.http import JsonResponse
from django.db import models, connection
from django.core.paginator import Paginator
from django.core.cache import cache
from django.utils import timezone
from .models import Auction
from .access import aplicar_modo_demo, ver_amostra, usuario_tem_assinatura_ativa
from .caixa_detail import buscar_detalhe


def _clean_list(values):
    cleaned = []
    for value in values:
        item = (value or '').strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return cleaned


def _get_filters(request):
    uf = request.GET.get('uf', '').strip()
    cidade = _clean_list(request.GET.getlist('cidade'))
    bairro = _clean_list(request.GET.getlist('bairro'))
    modalidade = _clean_list(request.GET.getlist('modalidade'))
    tipo = _clean_list(request.GET.getlist('tipo'))
    sort = request.GET.get('sort', 'price_asc').strip()
    page = request.GET.get('page', 1)
    return uf, cidade, bairro, modalidade, tipo, sort, page


def _build_queryset(uf, cidade, bairro, modalidade, tipo=None):
    qs = Auction.objects.all()

    if uf:
        qs = qs.filter(uf=uf)
    if cidade:
        qs = qs.filter(cidade__in=cidade)
    if bairro:
        qs = qs.filter(bairro__in=bairro)
    if modalidade:
        qs = qs.filter(modalidade__in=modalidade)
    if tipo:
        qs = qs.filter(tipo_imovel__in=tipo)

    return qs


def _count_options(qs, field_name):
    return [
        {
            'value': item[field_name],
            'label': item[field_name],
            'count': item['total'],
        }
        for item in (
            qs.exclude(**{f'{field_name}__isnull': True})
            .exclude(**{field_name: ''})
            .values(field_name)
            .annotate(total=models.Count('id'))
            .order_by(field_name)
        )
        if item[field_name]
    ]


def _cached_count_options(cache_key, qs, field_name, timeout=300):
    options = cache.get(cache_key)
    if options is None:
        options = _count_options(qs, field_name)
        cache.set(cache_key, options, timeout)
    return options


def _cache_part(values):
    return ','.join(sorted(values or [])) or 'all'


def _get_filter_options(uf='', cidade=None, bairro=None, modalidade=None, request=None):
    cidade = cidade or []
    bairro = bairro or []
    modalidade = modalidade or []
    access_scope = 'demo' if request is not None and ver_amostra(request) else 'full'

    base_qs = Auction.objects.all()
    if request is not None:
        base_qs, _ = aplicar_modo_demo(base_qs, request)

    ufs = _cached_count_options(
        f"filter_ufs:{access_scope}",
        base_qs,
        'uf',
        600,
    )

    cities_qs = base_qs
    if uf:
        cities_qs = cities_qs.filter(uf=uf)
    if modalidade:
        cities_qs = cities_qs.filter(modalidade__in=modalidade)
    cities = _cached_count_options(
        f"filter_cities:{access_scope}:{uf or 'all'}:{_cache_part(modalidade)}",
        cities_qs,
        'cidade',
    )

    neighborhoods_qs = base_qs
    if uf:
        neighborhoods_qs = neighborhoods_qs.filter(uf=uf)
    if cidade:
        neighborhoods_qs = neighborhoods_qs.filter(cidade__in=cidade)
    if modalidade:
        neighborhoods_qs = neighborhoods_qs.filter(modalidade__in=modalidade)
    neighborhoods = _cached_count_options(
        f"filter_neighborhoods:{access_scope}:{uf or 'all'}:{_cache_part(cidade)}:{_cache_part(modalidade)}",
        neighborhoods_qs,
        'bairro',
    )

    modalidades_qs = base_qs
    if uf:
        modalidades_qs = modalidades_qs.filter(uf=uf)
    if cidade:
        modalidades_qs = modalidades_qs.filter(cidade__in=cidade)
    if bairro:
        modalidades_qs = modalidades_qs.filter(bairro__in=bairro)
    modalidades = _cached_count_options(
        f"filter_modalidades:{access_scope}:{uf or 'all'}:{_cache_part(cidade)}:{_cache_part(bairro)}",
        modalidades_qs,
        'modalidade',
    )

    tipos_qs = base_qs
    if uf:
        tipos_qs = tipos_qs.filter(uf=uf)
    if cidade:
        tipos_qs = tipos_qs.filter(cidade__in=cidade)
    if bairro:
        tipos_qs = tipos_qs.filter(bairro__in=bairro)
    if modalidade:
        tipos_qs = tipos_qs.filter(modalidade__in=modalidade)
    tipos = _cached_count_options(
        f"filter_tipos:{access_scope}:{uf or 'all'}:{_cache_part(cidade)}:{_cache_part(bairro)}:{_cache_part(modalidade)}",
        tipos_qs,
        'tipo_imovel',
    )

    return ufs, cities, neighborhoods, modalidades, tipos


def _get_stats(qs, has_filters):
    if has_filters:
        aggregate = qs.aggregate(
            average=models.Avg('valor_avaliacao'),
            median=models.Avg('preco'),
        )
        return {
            'total': qs.count(),
            'cities': qs.values('cidade', 'uf').distinct().count(),
            'average': float(aggregate['average'] or 0),
            'median': float(aggregate['median'] or 0),
        }

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT (cidade, uf)) as cities,
                AVG(valor_avaliacao) as average,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY valor_avaliacao) as median
            FROM current_imoveis
            WHERE valor_avaliacao IS NOT NULL
        """)
        row = cursor.fetchone()

    stats = {
        'total': row[0] or 0,
        'cities': row[1] or 0,
        'average': float(row[2] or 0),
        'median': float(row[3] or 0),
    }
    return stats


def _parse_desc(desc):
    info = {'rooms': None, 'garage': '0', 'area': None, 'tipo': None, 'fgts': False}
    if not desc:
        return info

    m = re.search(r'(\d+)\s*Quarto', desc, re.I)
    if m:
        info['rooms'] = m.group(1)

    m = re.search(r'(\d+)\s*(Vaga|Garagem)', desc, re.I)
    if m:
        info['garage'] = m.group(1)

    m = re.search(r'(\d+[.,]\d+)\s*de\s*área\s*(privativa|total)', desc, re.I)
    if m:
        info['area'] = m.group(1)

    m = re.search(r'Tipo\s+de\s+im[óo]vel:\s*([^,.\n\r]+)', desc, re.I)
    if m:
        info['tipo'] = m.group(1).strip()
    else:
        first = desc.split(',')[0].strip()
        if first and len(first) < 30:
            info['tipo'] = first

    info['fgts'] = 'FGTS' in desc.upper()
    return info


def auction_list(request):
    uf, cidade, bairro, modalidade, tipo, sort, page = _get_filters(request)

    auctions = _build_queryset(uf, cidade, bairro, modalidade, tipo)
    auctions, em_demo = aplicar_modo_demo(auctions, request)
    auctions = auctions.only(
        'numero_imovel', 'uf', 'cidade', 'bairro', 'endereco',
        'preco', 'valor_avaliacao', 'desconto', 'modalidade', 'link',
        'descricao', 'last_seen', 'tipo_imovel',
    )

    if sort == 'price_desc':
        auctions = auctions.order_by('-preco')
    else:
        auctions = auctions.order_by('preco')

    paginator = Paginator(auctions, 24)
    page_obj = paginator.get_page(page)

    ufs, cidades, bairros, all_modalidades, all_tipos = _get_filter_options(
        uf, cidade, bairro, modalidade, request
    )

    has_filters = bool(uf or cidade or bairro or modalidade or tipo)
    stats = _get_stats(auctions, has_filters)

    parsed_auctions = []
    for a in page_obj.object_list:
        parsed_auctions.append({
            'auction': a,
            'desc_info': _parse_desc(a.descricao),
        })

    context = {
        'page_obj': page_obj,
        'parsed_auctions': parsed_auctions,
        'ufs': ufs,
        'cidades': cidades,
        'bairros': bairros,
        'all_modalidades': all_modalidades,
        'all_tipos': all_tipos,
        'stats': stats,
        'em_demo': em_demo,
        'esta_autenticado': request.user.is_authenticated,
        'tem_assinatura': usuario_tem_assinatura_ativa(request.user),
        'selected': {
            'uf': uf,
            'cidade': cidade,
            'bairro': bairro,
            'modalidade': modalidade,
            'tipo': tipo,
            'sort': sort,
        },
    }
    return render(request, 'auctions/list.html', context)


def api_cidades(request):
    uf = request.GET.get('uf', '').strip()
    modalidade = _clean_list(request.GET.getlist('modalidade'))
    if not uf:
        return JsonResponse([], safe=False)
    qs = Auction.objects.filter(uf=uf)
    qs, _ = aplicar_modo_demo(qs, request)
    if modalidade:
        qs = qs.filter(modalidade__in=modalidade)
    cidades = _count_options(qs, 'cidade')
    return JsonResponse(cidades, safe=False)


def api_bairros(request):
    uf = request.GET.get('uf', '').strip()
    cidade = _clean_list(request.GET.getlist('cidade'))
    modalidade = _clean_list(request.GET.getlist('modalidade'))
    if not uf or not cidade:
        return JsonResponse([], safe=False)
    qs = Auction.objects.filter(uf=uf, cidade__in=cidade)
    qs, _ = aplicar_modo_demo(qs, request)
    if modalidade:
        qs = qs.filter(modalidade__in=modalidade)
    bairros = _count_options(qs, 'bairro')
    return JsonResponse(bairros, safe=False)


def api_stats(request):
    base_qs = Auction.objects.all()
    base_qs, em_demo = aplicar_modo_demo(base_qs, request)

    stats = {
        'total': base_qs.count(),
        'ufs': base_qs.values('uf').distinct().count(),
        'cities': base_qs.values('cidade', 'uf').distinct().count(),
        'last_updated': None,
        'em_demo': em_demo,
    }
    last = base_qs.order_by('-last_seen').values_list('last_seen', flat=True).first()
    if last:
        stats['last_updated'] = last.strftime('%d/%m/%Y')
    return JsonResponse(stats)


def api_filters(request):
    uf = request.GET.get('uf', '').strip()
    city = _clean_list(request.GET.getlist('city'))
    neighborhood = _clean_list(request.GET.getlist('neighborhood'))
    modalidade = _clean_list(request.GET.getlist('modalidade'))

    ufs, cities, neighborhoods, modalidades, tipos = _get_filter_options(
        uf, city, neighborhood, modalidade, request
    )

    return JsonResponse({
        'ufs': ufs,
        'cities': cities,
        'neighborhoods': neighborhoods,
        'modalidades': modalidades,
        'tipos': tipos,
    })


def api_stats_filtered(request):
    uf = request.GET.get('uf', '').strip()
    city = _clean_list(request.GET.getlist('city'))
    neighborhood = _clean_list(request.GET.getlist('neighborhood'))
    modalidade = _clean_list(request.GET.getlist('modalidade'))
    tipo = _clean_list(request.GET.getlist('tipo'))

    qs = _build_queryset(uf, city, neighborhood, modalidade, tipo)
    qs, _ = aplicar_modo_demo(qs, request)

    agg = qs.aggregate(
        average=models.Avg('valor_avaliacao'),
        median=models.Avg('preco'),
    )
    return JsonResponse({
        'average': float(agg['average'] or 0),
        'median': float(agg['median'] or 0),
    })


def api_properties(request):
    uf = request.GET.get('uf', '').strip()
    city = _clean_list(request.GET.getlist('city'))
    neighborhood = _clean_list(request.GET.getlist('neighborhood'))
    modalidade = _clean_list(request.GET.getlist('modalidade'))
    tipo = _clean_list(request.GET.getlist('tipo'))
    sort = request.GET.get('sort', 'price_asc').strip()
    limit = min(int(request.GET.get('limit', 24)), 100)

    qs = _build_queryset(uf, city, neighborhood, modalidade, tipo)
    qs, em_demo = aplicar_modo_demo(qs, request)

    if sort == 'price_desc':
        qs = qs.order_by('-preco')
    else:
        qs = qs.order_by('preco')

    qs = qs.only('uf', 'numero_imovel', 'tipo_imovel', 'payload_json')[:limit]

    results = []
    for a in qs:
        payload = a.payload_json if a.payload_json else {}
        if not isinstance(payload, dict):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {}
        results.append({
            'uf': a.uf,
            'numero_imovel': a.numero_imovel,
            'tipo_imovel': a.tipo_imovel,
            'payload': payload,
        })

    if request.GET.get('_include_demo') == '1':
        return JsonResponse({'em_demo': em_demo, 'items': results}, safe=False)
    return JsonResponse(results, safe=False)


def _refinar_tipo(tipo_texto):
    from .models import TipoImovel
    if not tipo_texto:
        return None
    t = str(tipo_texto).lower()
    if 'apart' in t or 'apto' in t or 'flat' in t or 'cobertura' in t or 'kitnet' in t:
        return TipoImovel.APARTAMENTO
    if 'terreno' in t or 'lote' in t or 'gleba' in t or 'chácara' in t or 'sítio' in t or 'rural' in t:
        return TipoImovel.TERRENO
    if 'casa' in t or 'sobrado' in t or 'vivenda' in t:
        return TipoImovel.CASA
    return None


def api_property(request, numero):
    auction = Auction.objects.filter(numero_imovel=numero).first()
    if not auction:
        return JsonResponse({'error': 'Imóvel não encontrado'}, status=404)

    if auction.dados_enriquecidos:
        return JsonResponse({
            'numero_imovel': auction.numero_imovel,
            'uf': auction.uf,
            'enriquecido': True,
            'dados_enriquecidos': auction.dados_enriquecidos,
            'atualizado_em': auction.dados_enriquecidos_at,
        })

    try:
        dados = buscar_detalhe(auction.link)
    except Exception as exc:
        return JsonResponse({
            'numero_imovel': auction.numero_imovel,
            'uf': auction.uf,
            'enriquecido': False,
            'indisponivel': True,
            'erro': str(exc)[:200],
        }, status=503)

    auction.dados_enriquecidos = dados
    auction.dados_enriquecidos_at = timezone.now()

    tipo_refinado = _refinar_tipo(dados.get('tipo_imovel'))
    if tipo_refinado and auction.tipo_imovel in (None, 'outro'):
        auction.tipo_imovel = tipo_refinado

    auction.save(update_fields=['dados_enriquecidos', 'dados_enriquecidos_at', 'tipo_imovel'])

    return JsonResponse({
        'numero_imovel': auction.numero_imovel,
        'uf': auction.uf,
        'enriquecido': True,
        'dados_enriquecidos': dados,
        'atualizado_em': auction.dados_enriquecidos_at,
    })
