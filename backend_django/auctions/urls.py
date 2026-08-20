from django.urls import path
from .views import (
    auction_list, api_cidades, api_bairros,
    api_stats, api_filters, api_stats_filtered, api_properties, api_property,
)
from .auth_views import (
    api_registro, api_login, api_logout, api_me,
    api_preferencias, api_preferencias_id,
)

urlpatterns = [
    path('', auction_list, name='auction_list'),
    path('api/cidades/', api_cidades, name='api_cidades'),
    path('api/bairros/', api_bairros, name='api_bairros'),
    path('api/stats', api_stats, name='api_stats'),
    path('api/filters', api_filters, name='api_filters'),
    path('api/stats/filtered', api_stats_filtered, name='api_stats_filtered'),
    path('api/properties', api_properties, name='api_properties'),
    path('api/property/<str:numero>', api_property, name='api_property'),
    path('api/registro', api_registro, name='api_registro'),
    path('api/login', api_login, name='api_login'),
    path('api/logout', api_logout, name='api_logout'),
    path('api/me', api_me, name='api_me'),
    path('api/preferencias', api_preferencias, name='api_preferencias'),
    path('api/preferencias/<int:pref_id>', api_preferencias_id, name='api_preferencias_id'),
]
