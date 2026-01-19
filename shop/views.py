from django.http import HttpResponse
from django.shortcuts import render

def index(request):
    return render(request, "index.html")

def shop(request):
    return render(request, "shop.html")

def product(request):
    return render(request, "product.html")

