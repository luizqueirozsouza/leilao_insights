import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET, require_POST

from backend_django.auctions.access import usuario_tem_assinatura_ativa
from backend_django.auctions.models import Assinatura, PreferenciaAlerta


def _json_body(request):
    try:
        return json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return {}


def _serializar_assinatura(user):
    assinatura = getattr(user, 'assinatura', None)
    if not assinatura:
        return None
    return {
        'ativa': assinatura.esta_ativa,
        'data_inicio': assinatura.data_inicio.isoformat() if assinatura.data_inicio else None,
        'data_fim': assinatura.data_fim.isoformat() if assinatura.data_fim else None,
    }


def _serializar_preferencia(pref):
    return {
        'id': pref.id,
        'uf': pref.uf,
        'cidades': pref.cidades or [],
        'bairros': pref.bairros or [],
        'modalidades': pref.modalidades or [],
        'tipos': pref.tipos or [],
        'canal_email': pref.canal_email,
        'canal_whatsapp': pref.canal_whatsapp,
        'contato_whatsapp': pref.contato_whatsapp,
    }


def api_registro(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    body = _json_body(request)
    email = (body.get('email') or '').strip().lower()
    senha = body.get('senha') or body.get('password') or ''
    nome = (body.get('nome') or '').strip()

    if not email or not senha:
        return JsonResponse({'error': 'Email e senha são obrigatórios'}, status=400)
    if len(senha) < 8:
        return JsonResponse({'error': 'A senha deve ter pelo menos 8 caracteres'}, status=400)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'Email já cadastrado'}, status=400)

    username = email
    if User.objects.filter(username=username).exists():
        username = f"{email.split('@')[0]}_{email.split('@')[1].split('.')[0]}"
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Email já cadastrado'}, status=400)

    try:
        user = User.objects.create_user(username=username, email=email, password=senha)
        if nome:
            user.first_name = nome
            user.save()
    except IntegrityError:
        return JsonResponse({'error': 'Email já cadastrado'}, status=400)

    login(request, user)
    return JsonResponse({
        'ok': True,
        'email': user.email,
        'assinatura': _serializar_assinatura(user),
    }, status=201)


def api_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método não permitido'}, status=405)
    body = _json_body(request)
    identifier = (body.get('email') or body.get('username') or '').strip().lower()
    senha = body.get('senha') or body.get('password') or ''

    user = authenticate(request, username=identifier, password=senha)
    if user is None:
        # Também permite entrar usando o e-mail de uma conta cujo username é diferente.
        match = User.objects.filter(email=identifier).first()
        if match:
            user = authenticate(request, username=match.username, password=senha)
    if user is None:
        return JsonResponse({'error': 'Credenciais inválidas'}, status=400)

    login(request, user)
    return JsonResponse({
        'ok': True,
        'email': user.email,
        'nome': user.first_name,
        'assinatura': _serializar_assinatura(user),
    })


@require_POST
def api_logout(request):
    logout(request)
    return JsonResponse({'ok': True})


def api_me(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'autenticado': False, 'administrador': False, 'assinatura': None, 'preferencias': []})
    preferencias = [
        _serializar_preferencia(p)
        for p in user.preferencias_alertas.all().order_by('-id')
    ]
    return JsonResponse({
        'autenticado': True,
        'administrador': bool(user.is_staff),
        'email': user.email,
        'nome': user.first_name,
        'assinatura': _serializar_assinatura(user),
        'preferencias': preferencias,
    })


def _admin_forbidden(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Faça login para acessar o painel administrativo'}, status=401)
    if not request.user.is_staff:
        return JsonResponse({'error': 'Acesso restrito a administradores'}, status=403)
    return None


@require_GET
def api_admin_overview(request):
    forbidden = _admin_forbidden(request)
    if forbidden:
        return forbidden

    users = []
    user_queryset = User.objects.all().prefetch_related('preferencias_alertas').select_related('assinatura').order_by('-date_joined')
    for user in user_queryset:
        assinatura = getattr(user, 'assinatura', None)
        users.append({
            'id': user.id,
            'nome': user.first_name,
            'email': user.email,
            'ativo': user.is_active,
            'staff': user.is_staff,
            'criado_em': user.date_joined.isoformat() if user.date_joined else None,
            'assinatura': _serializar_assinatura(user),
            'alertas': user.preferencias_alertas.count(),
        })

    alertas = []
    preferences = PreferenciaAlerta.objects.select_related('usuario').order_by('-id')
    for pref in preferences:
        alertas.append({
            'id': pref.id,
            'usuario': pref.usuario.email,
            'nome': pref.usuario.first_name,
            'uf': pref.uf,
            'cidades': pref.cidades or [],
            'bairros': pref.bairros or [],
            'modalidades': pref.modalidades or [],
            'tipos': pref.tipos or [],
            'canal_email': pref.canal_email,
            'canal_whatsapp': pref.canal_whatsapp,
            'criada_em': pref.criada_em.isoformat() if pref.criada_em else None,
        })

    return JsonResponse({
        'usuarios': users,
        'alertas': alertas,
        'resumo': {
            'usuarios': len(users),
            'assinaturas_ativas': sum(1 for item in users if item['assinatura'] and item['assinatura']['ativa']),
            'alertas': len(alertas),
        },
    })


def api_admin_user(request, user_id):
    forbidden = _admin_forbidden(request)
    if forbidden:
        return forbidden
    if request.method != 'PUT':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
    body = _json_body(request)
    email = (body.get('email', user.email) or '').strip().lower()
    nome = (body.get('nome', user.first_name) or '').strip()
    if not email:
        return JsonResponse({'error': 'E-mail é obrigatório'}, status=400)
    if User.objects.filter(email=email).exclude(id=user.id).exists():
        return JsonResponse({'error': 'E-mail já está em uso'}, status=400)

    user.email = email
    user.first_name = nome
    if 'ativo' in body:
        if user.id == request.user.id and not bool(body['ativo']):
            return JsonResponse({'error': 'Você não pode desativar sua própria conta'}, status=400)
        user.is_active = bool(body['ativo'])
    user.save(update_fields=['email', 'first_name', 'is_active'])
    return JsonResponse({'ok': True})


def api_admin_subscription(request, user_id):
    forbidden = _admin_forbidden(request)
    if forbidden:
        return forbidden
    if request.method != 'PUT':
        return JsonResponse({'error': 'Método não permitido'}, status=405)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return JsonResponse({'error': 'Usuário não encontrado'}, status=404)
    body = _json_body(request)
    data_inicio = body.get('data_inicio') or None
    data_fim = body.get('data_fim') or None
    if data_inicio:
        data_inicio = parse_date(data_inicio)
        if not data_inicio:
            return JsonResponse({'error': 'Data de início inválida'}, status=400)
    if data_fim:
        data_fim = parse_date(data_fim)
        if not data_fim:
            return JsonResponse({'error': 'Data de validade inválida'}, status=400)
    if data_inicio and data_fim and data_fim < data_inicio:
        return JsonResponse({'error': 'A validade não pode ser anterior ao início'}, status=400)

    ativa = bool(body.get('ativa', False))
    if ativa and not data_inicio:
        data_inicio = timezone.localdate()
    assinatura, _ = Assinatura.objects.get_or_create(usuario=user)
    assinatura.ativa = ativa
    assinatura.data_inicio = data_inicio
    assinatura.data_fim = data_fim
    assinatura.save()
    return JsonResponse({'ok': True, 'assinatura': _serializar_assinatura(user)})


def api_preferencias(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'error': 'Faça login para gerenciar alertas'}, status=401)
    if not usuario_tem_assinatura_ativa(user):
        return JsonResponse({'error': 'Alertas exigem assinatura ativa'}, status=403)

    if request.method == 'GET':
        preferencias = [
            _serializar_preferencia(p)
            for p in user.preferencias_alertas.all().order_by('-id')
        ]
        return JsonResponse({'preferencias': preferencias})

    if request.method == 'POST':
        body = _json_body(request)
        pref = PreferenciaAlerta.objects.create(
            usuario=user,
            uf=(body.get('uf') or '').strip().upper(),
            cidades=body.get('cidades') or [],
            bairros=body.get('bairros') or [],
            modalidades=body.get('modalidades') or [],
            tipos=body.get('tipos') or [],
            canal_email=bool(body.get('canal_email', True)),
            canal_whatsapp=bool(body.get('canal_whatsapp', False)),
            contato_whatsapp=(body.get('contato_whatsapp') or '').strip(),
        )
        return JsonResponse({'preferencia': _serializar_preferencia(pref)}, status=201)

    return JsonResponse({'error': 'Método não permitido'}, status=405)


def api_preferencias_id(request, pref_id):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({'error': 'Faça login para gerenciar alertas'}, status=401)
    if not usuario_tem_assinatura_ativa(user):
        return JsonResponse({'error': 'Alertas exigem assinatura ativa'}, status=403)

    pref = user.preferencias_alertas.filter(id=pref_id).first()
    if not pref:
        return JsonResponse({'error': 'Preferência não encontrada'}, status=404)

    if request.method == 'DELETE':
        pref.delete()
        return JsonResponse({'ok': True})

    if request.method == 'PUT':
        body = _json_body(request)
        pref.uf = (body.get('uf', pref.uf) or '').strip().upper()
        pref.cidades = body.get('cidades', pref.cidades) or []
        pref.bairros = body.get('bairros', pref.bairros) or []
        pref.modalidades = body.get('modalidades', pref.modalidades) or []
        pref.tipos = body.get('tipos', pref.tipos) or []
        pref.canal_email = bool(body.get('canal_email', pref.canal_email))
        pref.canal_whatsapp = bool(body.get('canal_whatsapp', pref.canal_whatsapp))
        pref.contato_whatsapp = (body.get('contato_whatsapp', pref.contato_whatsapp) or '').strip()
        pref.save()
        return JsonResponse({'preferencia': _serializar_preferencia(pref)})

    return JsonResponse({'error': 'Método não permitido'}, status=405)
