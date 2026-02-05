from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import *
from .forms import *
from django.core.paginator import Paginator

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

def _extract_color_choices(post):
    """
    Достаём цвета из colors formset прямо из POST,
    чтобы заполнить select вариантов ДО сохранения товара.

    Возвращает list[(hex, title), ...]
    где title = name (если есть) иначе hex
    """
    total = int(post.get("colors-TOTAL_FORMS", 0))
    out = []
    seen = set()

    for i in range(total):
        hexv = (post.get(f"colors-{i}-hex") or "").strip()
        name = (post.get(f"colors-{i}-name") or "").strip()
        delete = post.get(f"colors-{i}-DELETE")

        if delete:
            continue
        if not hexv:
            continue
        if hexv in seen:
            continue

        seen.add(hexv)
        out.append((hexv, name or hexv))

    return out


@transaction.atomic
def product_add(request):
    temp_product = Product(store=request.store)

    # ВАЖНО: при POST строим choices для вариантов из введенных цветов
    color_choices = _extract_color_choices(request.POST) if request.method == "POST" else []

    if request.method == "POST":
        pform = ProductForm(request.POST, store=request.store)
        colors_fs = ColorFormSet(request.POST, instance=temp_product, prefix="colors")
        variants_fs = VariantFormSet(
            request.POST,
            instance=temp_product,
            prefix="variants",
            form_kwargs={"color_choices": color_choices},
        )

        if pform.is_valid() and colors_fs.is_valid() and variants_fs.is_valid():
            product = pform.save(commit=False)
            product.store = request.store
            product.is_active = True
            product.save()

            # 1) сохраняем цвета
            colors_fs.instance = product
            colors_fs.save()

            # 2) создаём map hex -> ProductColor
            color_map = {c.hex: c for c in product.colors.all()}

            # 3) сохраняем варианты: берем color_hex и ставим FK color
            variants_fs.instance = product

            for form in variants_fs.forms:
                if not form.cleaned_data:
                    continue
                if form.cleaned_data.get("DELETE"):
                    continue

                v = form.save(commit=False)
                hexv = (form.cleaned_data.get("color_hex") or "").strip()

                v.product = product
                v.is_active = True
                v.color = color_map.get(hexv) if hexv else None

                v.save(update_parent=False)

            # удаление (если редактирование будет)
            for obj in variants_fs.deleted_objects:
                obj.delete()

            # пересчет цен один раз
            product.update_prices()

            # картинки multiple
            files = request.FILES.getlist("images")
            main_set = False
            for i, f in enumerate(files):
                ProductImage.objects.create(
                    product=product,
                    image=f,
                    sort=i,
                    is_main=(not main_set),
                )
                main_set = True

            messages.success(request, "Товар добавлен")
            return redirect("product_list")

        messages.error(request, "Проверь поля — есть ошибки")

    else:
        pform = ProductForm(store=request.store)
        colors_fs = ColorFormSet(instance=temp_product, prefix="colors")
        variants_fs = VariantFormSet(
            instance=temp_product,
            prefix="variants",
            form_kwargs={"color_choices": []},
        )

    return render(request, "admin/product_add.html", {
        "store": request.store,
        "pform": pform,
        "colors_fs": colors_fs,
        "variants_fs": variants_fs,
    })


def product_edit(request, pk):
    return render(request, "admin/product_edit.html", {
        "store": request.store,
        "pk": pk
    })


# ===== CATEGORIES =====
def category_list(request):
    q = (request.GET.get("name") or "").strip()
    per_page = request.GET.get("per_page") or "10"

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10
    per_page = per_page if per_page in (10, 20, 30, 50, 100) else 10

    categories_qs = (
        Category.objects
        .filter(store=request.store)
        .annotate(
            products_count=Count(
                "products",
                filter=Q(products__is_active=True),
                distinct=True
            )
        )
    )

    if q:
        categories_qs = categories_qs.filter(name__icontains=q)

    categories_qs = categories_qs.order_by("name")

    paginator = Paginator(categories_qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "admin/category_list.html", {
        "store": request.store,
        "page_obj": page_obj,
        "q": q,
        "per_page": per_page,
    })


def category_add(request):
    if request.method == "POST":
        name = request.POST.get("name")
        image = request.FILES.get("image")

        Category.objects.create(
            store=request.store,  # как у тебя уже используется
            name=name,
            image=image
        )

        return redirect("category_list")  # куда нужно после сохранения

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