from django.shortcuts import render

def dashboard(request):
    return render(request, "admin/index.html", {"store": request.store})

def settings(request):
    return render(request, "admin/settings.html", {"store": request.store})