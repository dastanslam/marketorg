from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('shop/', views.shop, name='shop'),
    path('product/<slug:slug>/', views.product, name='product'),
    path('cart/', views.cart, name='cart'),
    path('whislist/', views.whislist, name='whislist'),
    path('contact/', views.contact, name='contact'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.register, name='signup'),
    path('about/', views.about, name='about'),

]