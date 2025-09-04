
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='wizardquest-index'),  # root of wizardquest/
]



