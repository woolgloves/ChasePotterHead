
from django.urls import path
from . import views

urlpatterns = [  
    path('shop/', views.shop_view, name='shop'),
    path('battle/<int:opponent_id>/', views.battle_view, name='battle'),
    path('battle/result/<int:opponent_id>/<int:winner_id>/', views.battle_result_view, name='battle_result'),
]



