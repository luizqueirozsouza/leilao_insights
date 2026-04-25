from django.urls import path
from .views import (
    auction_list, api_cidades, api_bairros,
    api_stats, api_filters, api_stats_filtered, api_properties,
)

urlpatterns = [
    path('', auction_list, name='auction_list'),
    path('api/cidades/', api_cidades, name='api_cidades'),
    path('api/bairros/', api_bairros, name='api_bairros'),
    path('api/stats', api_stats, name='api_stats'),
    path('api/filters', api_filters, name='api_filters'),
    path('api/stats/filtered', api_stats_filtered, name='api_stats_filtered'),
    path('api/properties', api_properties, name='api_properties'),
]
