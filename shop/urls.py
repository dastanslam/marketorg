from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('shop/', views.shop, name='shop'),
    path('product/<slug:slug>/', views.product, name='product'),
    path('cart/', views.cart, name='cart'),
    path('wishlist/', views.whislist, name='wishlist'),
    path('contact/', views.contact, name='contact'),
    path('signin/', views.login_view, name='signin'),
    path('signup/', views.register, name='signup'),
    path('logout/', views.user_out, name='logout'),
    path('about/', views.about, name='about'),
    path('profile/', views.edit_profile, name='profile'),
    path('order/', views.order, name='order'),
    path('favorite/toggle/', views.toggle_favorite, name='toggle_favorite'),
    path('favorite-count/', views.favorite_count, name='favorite_count'),

]