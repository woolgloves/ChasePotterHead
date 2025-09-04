
from django.urls import path
from . import views

urlpatterns = [  
    path('shop/', views.shop_view, name='shop'),
    path('challenge/<int:opponent_id>/', views.challenge_player_view, name='challenge_player'),

    # URL for an opponent to respond to a challenge (e.g., /respond_challenge/123/accept/)
    path('respond_challenge/<int:battle_id>/<str:action>/', views.respond_to_challenge_view, name='respond_to_challenge'),
    path('battle/<int:battle_id>/', views.battle_view, name='battle'),
    path('cancel_challenge/<int:battle_id>/', views.cancel_challenge_view, name='cancel_challenge'),
    path('battle_result/<int:battle_id>/', views.battle_result_view, name='battle_result'),
]



