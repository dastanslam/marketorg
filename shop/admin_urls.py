from django.urls import path
from . import admin_views

urlpatterns = [

    path('', admin_views.dashboard, name='dashboard'),
    path('settings/', admin_views.settings, name='settings'),

    path('products/', admin_views.product_list, name='product_list'),
    path('products/add/', admin_views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', admin_views.product_edit, name='product_edit'),

    path('categories/', admin_views.category_list, name='category_list'),
    path('categories/add/', admin_views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', admin_views.category_edit, name='category_edit'),

    path('orders/', admin_views.order_list, name='order_list'),
    path('orders/<int:pk>/', admin_views.order_detail, name='order_detail'),
    path('orders/<int:pk>/tracking/', admin_views.order_tracking, name='order_tracking'),
    path('help/', admin_views.help_center, name='help_center'),
    path('support/', admin_views.support, name='support'),
    path('policy/', admin_views.policy, name='policy'),

    path('social/facebook/', admin_views.social_facebook, name='social_facebook'),
    path('social/twitter/', admin_views.social_twitter, name='social_twitter'),
    path('social/linkedin/', admin_views.social_linkedin, name='social_linkedin'),
    path('social/instagram/', admin_views.social_instagram, name='social_instagram'),

]