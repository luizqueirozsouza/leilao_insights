from django.conf import settings


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('Origin')
        response = self.get_response(request)
        allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
        if origin and (origin in allowed_origins or '*' in allowed_origins):
            response['Access-Control-Allow-Origin'] = origin
            response['Vary'] = 'Origin'
        response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        if request.method == 'OPTIONS':
            response.status_code = 200
        return response
