from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.signup_view, name='player_signup'),
    path('login/', views.login_view, name='player_login'),
]