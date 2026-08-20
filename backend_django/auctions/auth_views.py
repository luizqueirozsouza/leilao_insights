import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from backend_django.auctions.access import usuario_tem_assinatura_ativa
from backend_django.auctions.models import PreferenciaAlerta


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
    email = (body.get('email') or '').strip().lower()
    senha = body.get('senha') or body.get('password') or ''

    user = authenticate(request, username=email, password=senha)
    if user is None:
        # tenta login por username que foi criado a partir do email
        match = User.objects.filter(email=email).first()
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
        return JsonResponse({'autenticado': False, 'assinatura': None, 'preferencias': []})
    preferencias = [
        _serializar_preferencia(p)
        for p in user.preferencias_alertas.all().order_by('-id')
    ]
    return JsonResponse({
        'autenticado': True,
        'email': user.email,
        'nome': user.first_name,
        'assinatura': _serializar_assinatura(user),
        'preferencias': preferencias,
    })


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
        pref.canal_email = bool(body.get('canal_email', pref.canal_email))
        pref.canal_whatsapp = bool(body.get('canal_whatsapp', pref.canal_whatsapp))
        pref.contato_whatsapp = (body.get('contato_whatsapp', pref.contato_whatsapp) or '').strip()
        pref.save()
        return JsonResponse({'preferencia': _serializar_preferencia(pref)})

    return JsonResponse({'error': 'Método não permitido'}, status=405)
