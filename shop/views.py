from django.shortcuts import render, redirect, get_object_or_404

from .models import *

def index(request):
    return render(request, "index.html", {"store": request.store})

def shop(request):
    return render(request, "shop.html", {"store": request.store})

def product(request):
    return render(request, "product.html", {"store": request.store})

def cart(request):
    return render(request, "cart.html", {"store": request.store})

def whislist(request):
    return render(request, "whislist.html", {"store": request.store})

def contact(request):
    return render(request, "contact.html", {"store": request.store})

def signin(request):
    return render(request, "signin.html", {"store": request.store})

def signup(request):
    return render(request, "signup.html", {"store": request.store})

def about(request):
    return render(request, "about.html", {"store": request.store})

