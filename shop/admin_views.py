from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from .models import *
from .forms import *
from django.core.paginator import Paginator
from django.utils.dateparse import parse_datetime
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Min, Max, Q, OuterRef, Subquery
from django.utils.text import slugify

def dashboard(request):
    return render(request, "admin/index.html", {"store": request.store})

def product_list(request):
    store = request.store

    # параметры
    search = (request.GET.get("q") or "").strip()
    per_page = request.GET.get("per_page", "10")
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10
    if per_page not in (10, 20, 30):
        per_page = 10

    qs = (
        Product.objects
        .filter(store=store)
        .annotate(
            variants_count=Count("variants", distinct=True),
            min_p=Min("variants__price"),
            max_p=Max("variants__price"),
        )
    )

    if search:
        if search.isdigit():
            qs = qs.filter(id=int(search))
        else:
            qs = qs.filter(name__icontains=search)

    first_sku_subq = ProductVariant.objects.filter(
        product_id=OuterRef("pk"),
        is_active=True
    ).order_by("id").values("sku")[:1]

    qs = qs.annotate(first_sku=Subquery(first_sku_subq)).order_by("-created_at")

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "admin/product_list.html", {
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "per_page": per_page,
        "q": search,
    })

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
    temp_product = Product(store=request.store)

    if request.method == "POST":
        pform = ProductForm(request.POST, store=request.store)
        variants_fs = VariantFormSet(request.POST, instance=temp_product, prefix="variants")

        # Ваши логи подтвердили, что это True
        if pform.is_valid() and variants_fs.is_valid():
            try:
                with transaction.atomic():
                    # 1. Подготовка товара
                    product = pform.save(commit=False)
                    product.store = request.store

                    # 2. Обработка КАТЕГОРИИ из Select2 (по вашим логам: "дастан тесть")
                    cat_raw = request.POST.get("category")
                    if cat_raw:
                        if cat_raw.isdigit():
                            product.category_id = int(cat_raw)
                        else:
                            cat, _ = Category.objects.get_or_create(
                                store=request.store,
                                name=cat_raw.strip(),
                                defaults={'is_active': True}
                            )
                            product.category = cat

                    # 3. Обработка БРЕНДА из Select2
                    brand_raw = request.POST.get("brand", "").strip()

                    if brand_raw:
                        if brand_raw.isdigit():
                            # Если пришел ID существующего бренда
                            product.brand_id = int(brand_raw)
                        else:
                            # Если пришел текст (новое название)
                            name = brand_raw

                            # ВАЖНО: используйте slugify с поддержкой кириллицы,
                            # иначе для русских названий slug будет пустым!
                            from slugify import slugify
                            slug = slugify(name) or "brand"

                            # Ищем по слагу в рамках текущего магазина
                            brand = Brand.objects.filter(store=request.store, slug=slug).first()

                            if not brand:
                                brand = Brand.objects.create(
                                    store=request.store,
                                    name=name,
                                    is_active=True
                                )
                            product.brand = brand

                    product.is_active = True
                    product.save() # СОХРАНЯЕМ ТОВАР

                    # 4. Сохранение вариантов (размеры, цвета)
                    variants_fs.instance = product
                    variants = variants_fs.save(commit=False)
                    for v in variants:
                        v.product = product
                        v.is_active = True
                        v.save(update_parent=False)

                    # Удаление помеченных
                    for obj in variants_fs.deleted_objects:
                        obj.delete()

                    # 5. Цены и картинки
                    product.update_prices()

                    files = request.FILES.getlist("images")
                    for i, f in enumerate(files):
                        ProductImage.objects.create(
                            product=product,
                            image=f,
                            sort=i,
                            is_main=(i == 0),
                        )

                messages.success(request, f"Товар '{product.name}' успешно добавлен")
                return redirect("product_list")

            except Exception as e:
                # Если упадет здесь (например, на картинках), мы увидим ошибку
                print(f"ОШИБКА СОХРАНЕНИЯ: {e}")
                messages.error(request, f"Ошибка при сохранении в базу: {e}")
        else:
            # На всякий случай выводим ошибки, если валидация вдруг упадет
            print(f"PFORM ERRORS: {pform.errors}")
            print(f"VARIANTS ERRORS: {variants_fs.errors}")
            messages.error(request, "Проверьте поля формы")

    else:
        pform = ProductForm(store=request.store)
        variants_fs = VariantFormSet(instance=temp_product, prefix="variants")

    return render(request, "admin/product_add.html", {
        "store": request.store,
        "pform": pform,
        "variants_fs": variants_fs,
    })


def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        pform = ProductForm(request.POST, instance=product, store=request.store)
        variants_fs = VariantFormSet(request.POST, instance=product)

        if pform.is_valid() and variants_fs.is_valid():
            product = pform.save(commit=False)

            # ===== category =====
            cat_raw = (pform.cleaned_data.get("category") or "").strip()
            if cat_raw:
                if cat_raw.isdigit():
                    product.category_id = int(cat_raw)
                else:
                    # если вводишь текстом через select2 tag
                    name = cat_raw
                    slug = slugify(name) or "category"
                    cat = Category.objects.filter(store=request.store, slug=slug).first()
                    if not cat:
                        cat = Category.objects.create(store=request.store, name=name, slug=slug, is_active=True)
                    product.category = cat

            # ===== brand =====
            brand_raw = (pform.cleaned_data.get("brand") or "").strip()
            if brand_raw:
                if brand_raw.isdigit():
                    product.brand_id = int(brand_raw)
                else:
                    name = brand_raw
                    slug = slugify(name) or "brand"
                    br = Brand.objects.filter(store=request.store, slug=slug).first()
                    if not br:
                        br = Brand.objects.create(store=request.store, name=name, slug=slug, is_active=True)
                    product.brand = br

            product.save()
            variants_fs.save()

            # удалить старые фото (только этого товара!)
            delete_ids = request.POST.getlist("delete_images")
            if delete_ids:
                ProductImage.objects.filter(product=product, id__in=delete_ids).delete()

            # добавить новые
            for f in request.FILES.getlist("images"):
                ProductImage.objects.create(product=product, image=f)

            return redirect("product_list")
    else:
        pform = ProductForm(instance=product, store=request.store, initial={
            "category": str(product.category_id) if product.category_id else "",
            "brand": str(product.brand_id) if product.brand_id else "",
        })
        variants_fs = VariantFormSet(instance=product)

    images = ProductImage.objects.filter(product=product).order_by("id")

    return render(request, "admin/product_edit.html", {
        "pform": pform,
        "variants_fs": variants_fs,
        "product": product,
        "images": images,
    })


@require_POST  # Удаление должно быть только через POST/DELETE для безопасности
def product_delete_api(request, pk):
    # Ищем товар, который принадлежит именно текущему магазину из request
    product = get_object_or_404(Product, pk=pk, store=request.store)

    product_name = product.name
    try:
        product.delete()
        return JsonResponse({
            "status": "success",
            "message": f"Товар '{product_name}' успешно удален"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Не удалось удалить товар: {str(e)}"
        }, status=400)


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

        Category.objects.create(
            store=request.store,  # как у тебя уже используется
            name=name,
        )

        return redirect("category_list")  # куда нужно после сохранения

    return render(request, "admin/category_add.html", {"store": request.store})


def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk, store=request.store)

    if request.method == "POST":
        category.name = request.POST.get("name")

        if request.FILES.get("image"):
            category.image = request.FILES["image"]

        category.is_active = bool(request.POST.get("is_active"))

        category.discount_percent = int(request.POST.get("discount_percent") or 0)
        category.discount_active = bool(request.POST.get("discount_active"))

        category.discount_start = parse_datetime(request.POST.get("discount_start")) \
            if request.POST.get("discount_start") else None
        category.discount_end = parse_datetime(request.POST.get("discount_end")) \
            if request.POST.get("discount_end") else None

        category.save()
        return redirect("category_list")

    return render(request, "admin/category_edit.html", {"category": category})


def category_show(request, pk):
    category = get_object_or_404(Category, pk=pk, store=request.store)

    # параметры
    search = (request.GET.get("q") or "").strip()         # поиск (name или sku)
    per_page = request.GET.get("per_page", "10")
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10
    if per_page not in (10, 20, 30):
        per_page = 10

    # базовый queryset
    qs = (
        category.products
        .filter(store=request.store)
        .annotate(
            variants_count=Count("variants", distinct=True),
            min_p=Min("variants__price"),
            max_p=Max("variants__price"),
        )
    )

    # поиск по названию ИЛИ по sku вариантов
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(variants__sku__icontains=search)
        ).distinct()

    # показать sku первого активного варианта (чтобы в шаблоне было быстро)
    first_sku_subq = ProductVariant.objects.filter(
        product_id=OuterRef("pk"),
        is_active=True
    ).order_by("id").values("sku")[:1]

    qs = qs.annotate(first_sku=Subquery(first_sku_subq)).order_by("-created_at")

    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "admin/category_show.html", {
        "category": category,
        "products": page_obj.object_list,
        "page_obj": page_obj,
        "per_page": per_page,
        "q": search,
    })

@require_POST
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, store=request.store)

    try:
        with transaction.atomic():
            # сколько товаров было
            cnt = category.products.count()
            print("PRODUCTS COUNT BEFORE:", cnt)

            # удаляем товары
            deleted_products = category.products.all().delete()
            print("PRODUCTS DELETE RESULT:", deleted_products)

            # удаляем категорию
            category.delete()
            print("CATEGORY DELETE DONE")

        # проверка: осталась ли категория в базе
        still_exists = Category.objects.filter(pk=pk).exists()
        print("CATEGORY STILL EXISTS IN DB:", still_exists)

    except Exception as e:
        print("DELETE ERROR:", repr(e))
        raise

    messages.success(request, "Категория удалена.")
    return redirect("category_list")

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