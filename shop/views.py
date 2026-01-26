from django.shortcuts import render, redirect, get_object_or_404

from .models import *

def index(request):
    return render(request, "index.html", {"store": request.store})

def shop(request):
    return render(request, "shop.html")

def product(request):
    return render(request, "product.html")

def cart(request):
    return render(request, "cart.html")

def whislist(request):
    return render(request, "whislist.html")

def contact(request):
    return render(request, "contact.html")

def signin(request):
    return render(request, "signin.html")

def signup(request):
    return render(request, "signup.html")

