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


from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib import messages
from .models import Product, Category, Brand, ProductImage
from .forms import ProductForm # Убедитесь, что импорт правильный

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect

from .forms import ProductForm, VariantFormSet
from .models import Product, Brand, Category, ProductImage


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
                    brand_raw = (pform.cleaned_data.get("brand") or "").strip()
                    if brand_raw:
                        if brand_raw.isdigit():
                            product.brand_id = int(brand_raw)
                        else:
                            name = brand_raw
                            slug = slugify(name) or "brand"

                            # если такой slug уже есть в этом store — берём существующий бренд
                            brand = Brand.objects.filter(store=request.store, slug=slug).first()
                            if not brand:
                                brand = Brand.objects.create(store=request.store, name=name, is_active=True)
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
    product = get_object_or_404(Product, pk=pk, store=request.store)

    # choices для вариантов:
    # POST -> из введённых цветов (чтобы сразу обновлялось)
    # GET  -> из текущих цветов товара
    if request.method == "POST":
        color_choices = _extract_color_choices(request.POST)
    else:
        color_choices = [(c.hex, c.name) for c in product.colors.all()]

    if request.method == "POST":
        pform = ProductForm(request.POST, instance=product, store=request.store)
        colors_fs = ColorFormSet(request.POST, instance=product, prefix="colors")
        variants_fs = VariantFormSet(
            request.POST,
            instance=product,
            prefix="variants",
            form_kwargs={"color_choices": color_choices},
        )

        if pform.is_valid() and colors_fs.is_valid() and variants_fs.is_valid():
            with transaction.atomic():
                # -------- PRODUCT --------
                product = pform.save(commit=False)
                product.store = request.store

                # новый бренд (если ввели)
                new_brand = (pform.cleaned_data.get("new_brand") or "").strip()
                if new_brand:
                    brand, _ = Brand.objects.get_or_create(
                        store=request.store,
                        name=new_brand,
                        defaults={"is_active": True},
                    )
                    product.brand = brand

                product.save()

                # -------- COLORS --------
                colors_fs.save()
                color_map = {c.hex: c for c in product.colors.all()}

                # -------- VARIANTS --------
                for form in variants_fs.forms:
                    if not form.cleaned_data:
                        continue

                    # удаление существующего варианта
                    if form.cleaned_data.get("DELETE") and form.instance.pk:
                        form.instance.delete()
                        continue

                    v = form.save(commit=False)
                    hexv = (form.cleaned_data.get("color_hex") or "").strip()

                    v.product = product
                    v.is_active = True
                    v.color = color_map.get(hexv) if hexv else None
                    v.save(update_parent=False)

                # пересчёт цен один раз
                product.update_prices()

                # -------- IMAGES: delete + set main + add new --------
                delete_ids = request.POST.getlist("delete_images")  # checkbox
                main_id = request.POST.get("main_image")            # radio

                # 1) удалить выбранные
                if delete_ids:
                    product.images.filter(id__in=delete_ids).delete()

                # 2) добавить новые
                files = request.FILES.getlist("images")
                if files:
                    start_sort = (product.images.aggregate(m=Max("sort")).get("m") or 0) + 1
                    for i, f in enumerate(files):
                        ProductImage.objects.create(
                            product=product,
                            image=f,
                            sort=start_sort + i,
                            is_main=False,
                        )

                # 3) назначить главную (если выбрали и её не удалили)
                if main_id and not (delete_ids and str(main_id) in delete_ids):
                    product.images.update(is_main=False)
                    product.images.filter(id=main_id).update(is_main=True)

                # 4) если главной нет — поставить первую
                if not product.images.filter(is_main=True).exists():
                    first_img = product.images.order_by("sort", "id").first()
                    if first_img:
                        first_img.is_main = True
                        first_img.save(update_fields=["is_main"])

            messages.success(request, "Товар обновлён")
            return redirect("product_list")

        messages.error(request, "Проверь поля — есть ошибки")

    else:
        pform = ProductForm(instance=product, store=request.store)
        colors_fs = ColorFormSet(instance=product, prefix="colors")
        variants_fs = VariantFormSet(
            instance=product,
            prefix="variants",
            form_kwargs={"color_choices": color_choices},
        )

    return render(request, "admin/product_edit.html", {
        "store": request.store,
        "product": product,
        "pform": pform,
        "colors_fs": colors_fs,
        "variants_fs": variants_fs,
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