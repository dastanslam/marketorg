from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q, Exists, OuterRef
from .models import *
from django.db.models import Prefetch
from django.core.paginator import Paginator
import json
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from .forms import *

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
        products = products.order_by("-created_at")

    # ---- оптимизация ----
    products = products.select_related(
        "category", "brand", "gender"
    ).prefetch_related(
        Prefetch(
            "variants",
            queryset=ProductVariant.objects.filter(is_active=True)
            .select_related("color")
            .order_by("price"),
            to_attr="active_variants"
        ),
        Prefetch(
            "images",
            queryset=ProductImage.objects.order_by("-is_main", "sort"),
            to_attr="product_images"
        )
    )

    # ---- пагинация ----
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

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
        .exclude(size__isnull=True)
        .exclude(size__exact="")
        .values_list("size", flat=True)
        .distinct()
        .order_by("size")
    )

    return render(request, "shop.html", {
        "store": store,
        "products": page_obj.object_list,
        "page_obj": page_obj,

        "categories": categories,
        "brands": brands,
        "genders": genders,
        "colors": colors,
        "sizes": sizes_qs,

        "sort": sort,

        "selected": {
            "category": set(map(str, cat_ids)),
            "brand": set(map(str, brand_ids)),
            "gender": set(map(str, gender_ids)),
            "color": set(map(str, color_ids)),
            "size": set(map(str, sizes)),
        }
    })

def product(request, slug):
    product = get_object_or_404(
        Product.objects
        .select_related("category", "brand", "gender")
        .prefetch_related("images", "variants__color"),
        slug=slug,
        store=request.store,
        is_active=True
    )

    variants = list(
        product.variants.filter(is_active=True).select_related("color")
    )

    current_variant = sorted(variants, key=lambda v: v.price)[0] if variants else None

    variants_data = [
        {
            "id": v.id,
            "color_id": v.color.id if v.color else None,
            "color_name": v.color.name if v.color else "",
            "color_hex": v.color.hex if v.color else "",
            "size": v.size or "",
            "sku": v.sku or "",
            "price": str(v.price_final),
            "old_price": str(v.old_price_effective) if v.old_price_effective else "",
        }
        for v in variants
    ]

    return render(request, "product.html", {
        "product": product,
        "images": product.images.all(),
        "variants": variants,
        "current_variant": current_variant,
        "variants_json": json.dumps(variants_data, ensure_ascii=False),
        "store": request.store,
    })

def cart(request):
    return render(request, "cart.html", {"store": request.store})

def whislist(request):
    return render(request, "whislist.html", {"store": request.store})

def contact(request):
    return render(request, "contact.html", {"store": request.store})

def signin(request):
    return render(request, "login/auth-login.html", {"store": request.store})

def register(request):

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.password = make_password(form.cleaned_data["password"])
            user.save()

            login(request, user)

            return redirect("index")  # поменяй на свою страницу

    else:
        form = RegisterForm()

    return render(request, "login/auth-register.html", {"form": form})

def about(request):
    return render(request, "about.html", {"store": request.store})

