from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Exists, OuterRef
from .models import *
from django.db.models import Prefetch

def index(request):
    return render(request, "index.html", {"store": request.store})

def shop(request):
    store = request.store

    # выбранные фильтры
    cat_ids    = request.GET.getlist("category")
    brand_ids  = request.GET.getlist("brand")
    gender_ids = request.GET.getlist("gender")
    color_ids  = request.GET.getlist("color")
    sizes      = request.GET.getlist("size")

    # ---- товары (база) ----
    products = Product.objects.filter(store=store, is_active=True)

    if cat_ids:
        products = products.filter(category_id__in=cat_ids)
    if brand_ids:
        products = products.filter(brand_id__in=brand_ids)
    if gender_ids:
        products = products.filter(gender_id__in=gender_ids)

    # ---- СТРОГО: color+size в одном варианте ----
    vq = ProductVariant.objects.filter(product=OuterRef("pk"), is_active=True)
    if color_ids:
        vq = vq.filter(color_id__in=color_ids)
    if sizes:
        vq = vq.filter(size__in=sizes)

    products = products.annotate(has_variant=Exists(vq)).filter(has_variant=True).distinct()

    # ---- сортировка ----
    sort = request.GET.get("sort", "")

    if sort == "old":
        products = products.order_by("created_at")
    elif sort == "reviews":
        products = products.order_by("-rating_count")
    elif sort == "price_asc":
        products = products.order_by("min_price")
    elif sort == "price_desc":
        products = products.order_by("-min_price")
    else:
        products = products.order_by("-created_at")  # по умолчанию

    # ---- списки фильтров + счетчики ----
    categories = (
        Category.objects.filter(store=store, is_active=True)
        .annotate(cnt=Count("products", filter=Q(products__is_active=True, products__variants__is_active=True), distinct=True))
    )

    brands = (
        Brand.objects.filter(store=store, is_active=True)
        .annotate(cnt=Count("products", filter=Q(products__store=store, products__is_active=True, products__variants__is_active=True), distinct=True))
    )

    genders = (
        Gender.objects.annotate(cnt=Count("products", filter=Q(products__store=store, products__is_active=True, products__variants__is_active=True), distinct=True))
        .order_by("id")
    )

    colors = (
        ProductColor.objects
        .filter(variants__product__store=store, variants__is_active=True)
        .annotate(cnt=Count("variants__product", distinct=True))
        .order_by("name", "hex")
        .distinct()
    )

    sizes_qs = (
        ProductVariant.objects
        .filter(product__store=store, is_active=True)
        .exclude(size__isnull=True).exclude(size__exact="")
        .values_list("size", flat=True)
        .distinct()
        .order_by("size")
    )

    products = products.prefetch_related(
        Prefetch(
            "variants",
            queryset=ProductVariant.objects.filter(is_active=True)
            .select_related("color")
            .order_by("price"),
            to_attr="active_variants"
        )
    ).select_related("category", "brand", "gender")

    return render(request, "shop.html", {
        "store": store,
        "products": products,

        "categories": categories,
        "brands": brands,
        "genders": genders,
        "colors": colors,
        "sizes": sizes_qs,

        "sort": sort,  # <-- важно для активного пункта в dropdown

        "selected": {
            "category": set(map(str, cat_ids)),
            "brand": set(map(str, brand_ids)),
            "gender": set(map(str, gender_ids)),
            "color": set(map(str, color_ids)),
            "size": set(map(str, sizes)),
        }
    })

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

