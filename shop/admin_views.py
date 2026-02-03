from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import *
from .forms import *

def dashboard(request):
    return render(request, "admin/index.html", {"store": request.store})

def product_list(request):
    return render(request, "admin/product_list.html", {"store": request.store})

@transaction.atomic
def settings(request):
    store = request.store  # как у тебя

    if request.method == "POST":
        # --- Store ---
        store.name = request.POST.get("name", "").strip()
        store.slogan = request.POST.get("slogan", "").strip()
        store.email = request.POST.get("email", "").strip()
        store.phone = request.POST.get("phone", "").strip()
        store.save()

        # --- Socials ---
        names = request.POST.getlist("social_name[]")
        links = request.POST.getlist("social_link[]")

        # перезаписываем список соцсетей (простая и надежная логика)
        StoreSocial.objects.filter(store=store).delete()

        for i, (n, l) in enumerate(zip(names, links)):
            n = (n or "").strip()
            l = (l or "").strip()
            if n and l:
                StoreSocial.objects.create(
                    store=store,
                    name=n,
                    link=l,
                    order=i
                )

        messages.success(request, "Настройки сохранены")
        return redirect("settings")  # поставь свой name из urls.py

    socials = store.socials.order_by("order")  # related_name='socials'
    return render(request, "admin/settings.html", {"store": store, "socials": socials})

@transaction.atomic
def product_add(request):
    if request.method == "POST":
        pform = ProductForm(request.POST or None)

        pform.fields["category"].queryset = Category.objects.filter(
            store=request.store, is_active=True
        )
        pform.fields["brand"].queryset = Brand.objects.filter(
            store=request.store, is_active=True
        )

        pform = ProductForm(request.POST)
        vform = VariantForm(request.POST)

        # временный инстанс чтобы formset мог валидироваться
        temp_product = Product(store=request.store)
        colors_fs = ColorFormSet(request.POST, instance=temp_product)

        if pform.is_valid() and vform.is_valid() and colors_fs.is_valid():
            product = pform.save(commit=False)
            product.store = request.store
            product.save()

            colors_fs.instance = product
            colors_fs.save()

            variant = vform.save(commit=False)
            variant.product = product
            variant.save()

            # multiple upload (без формы)
            files = request.FILES.getlist("images")
            main_set = False
            for i, f in enumerate(files):
                ProductImage.objects.create(
                    product=product,
                    image=f,
                    sort=i,
                    is_main=(False if main_set else True),
                )
                main_set = True

            messages.success(request, "Товар добавлен")
            return redirect("product_list")

        messages.error(request, "Проверь поля формы — есть ошибки")

    else:
        pform = ProductForm()
        vform = VariantForm()
        colors_fs = ColorFormSet(instance=Product(store=request.store))

    return render(request, "admin/product_add.html", {
        "store": request.store,
        "pform": pform,
        "vform": vform,
        "colors_fs": colors_fs,
    })


def product_edit(request, pk):
    return render(request, "admin/product_edit.html", {
        "store": request.store,
        "pk": pk
    })


# ===== CATEGORIES =====
def category_list(request):
    return render(request, "admin/category_list.html", {"store": request.store})


def category_add(request):
    return render(request, "admin/category_add.html", {"store": request.store})


def category_edit(request, pk):
    return render(request, "admin/category_edit.html", {
        "store": request.store,
        "pk": pk
    })


# ===== ORDERS =====
def order_list(request):
    return render(request, "admin/order_list.html", {"store": request.store})


def order_detail(request, pk):
    return render(request, "admin/order_detail.html", {
        "store": request.store,
        "pk": pk
    })


def order_tracking(request, pk):
    return render(request, "admin/order_tracking.html", {
        "store": request.store,
        "pk": pk
    })

def help_center(request):
    return render(request, "admin/help_center.html", {"store": request.store})


def support(request):
    return render(request, "admin/support.html", {"store": request.store})


def policy(request):
    return render(request, "admin/policy.html", {"store": request.store})


# ===== SOCIAL (редиректы, чтобы не делать отдельные страницы) =====
def social_facebook(request):
    return redirect("https://facebook.com")


def social_twitter(request):
    return redirect("https://twitter.com")


def social_linkedin(request):
    return redirect("https://linkedin.com")


def social_instagram(request):
    return redirect("https://instagram.com")