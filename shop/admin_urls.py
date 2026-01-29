from django.urls import path
from . import admin_views

urlpatterns = [

    path('', admin_views.dashboard, name='dashboard'),
    path('settings/', admin_views.settings, name='settings'),

]