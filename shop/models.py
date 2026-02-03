from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings

hex_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{6})$",
    message="HEX должен быть в формате #RRGGBB, например #FFAA00",
)


class Store(models.Model):
    subdomain = models.SlugField(max_length=63, unique=True, blank=True, db_index=True)

    name = models.CharField(max_length=120)
    slogan = models.CharField(max_length=200, blank=True)

    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.subdomain:
            base = slugify(self.name) or "store"
            sub = base
            i = 2
            while Store.objects.filter(subdomain=sub).exists():
                sub = f"{base}-{i}"
                i += 1
            self.subdomain = sub
        super().save(*args, **kwargs)

class Category(models.Model):
    store = models.ForeignKey(
        "Store",
        related_name="categories",
        on_delete=models.CASCADE
    )

    name = models.CharField("Название", max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("store", "slug")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "category"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    store = models.ForeignKey(
        "Store",
        related_name="brands",
        on_delete=models.CASCADE
    )

    name = models.CharField("Название", max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("store", "slug")
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "brand"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Gender(models.Model):
    """
    Не привязываем к store — значения глобальные
    """
    name = models.CharField("Название", max_length=50)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

class Product(models.Model):
    store = models.ForeignKey(Store, related_name="products", on_delete=models.CASCADE)

    category = models.ForeignKey(
        Category,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    brand = models.ForeignKey(
        Brand,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    gender = models.ForeignKey(
        Gender,
        related_name="products",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField("Название", max_length=255)
    slug = models.SlugField(max_length=255, blank=True, db_index=True)

    description = models.TextField("Описание", blank=True)

    country = models.CharField("Страна производитель", max_length=100, blank=True)
    material = models.CharField("Тип материала", max_length=100, blank=True)

    views = models.PositiveIntegerField("Просмотры", default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    rating_avg = models.DecimalField("Средний рейтинг", max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField("Кол-во отзывов", default=0)

    class Meta:
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["store", "slug"]),
        ]
        constraints = [
            # чтобы в одном магазине не было 2 товаров с одинаковым slug
            models.UniqueConstraint(fields=["store", "slug"], name="uniq_product_slug_per_store"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "product"
            slug = base
            i = 2
            while Product.objects.filter(store=self.store, slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.store.name})"

class ProductColor(models.Model):
    product = models.ForeignKey(
        "Product",
        related_name="colors",
        on_delete=models.CASCADE
    )

    name = models.CharField("Название цвета", max_length=50, blank=True)
    hex = models.CharField("HEX", max_length=7, validators=[hex_validator])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "hex"], name="uniq_hex_per_product"),
        ]

    def __str__(self):
        n = f"{self.name} " if self.name else ""
        return f"{n}{self.hex}"


class ProductVariant(models.Model):
    """
    Реальная сущность продажи: конкретный вариант товара.
    Тут лежит цена, старая цена и остаток.
    """
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)

    # если цвет не нужен (например, товар без цветов) — можно null
    color = models.ForeignKey(ProductColor, related_name="variants",
                              on_delete=models.SET_NULL, null=True, blank=True)

    # без choices: любые размеры (XS, 40, 40x60, 128GB...)
    size = models.CharField("Размер", max_length=20, blank=True)

    sku = models.CharField("SKU / Артикул", max_length=64, blank=True)

    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    old_price = models.DecimalField("Старая цена", max_digits=10, decimal_places=2, null=True, blank=True)

    stock = models.PositiveIntegerField("Остаток", default=0)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["product", "is_active"]),
            models.Index(fields=["product", "stock"]),
        ]
        constraints = [
            # уникальность комбинации (product + color + size)
            models.UniqueConstraint(fields=["product", "color", "size"], name="uniq_variant_per_product"),
            # если есть old_price, то она должна быть >= price (логика скидки)
            models.CheckConstraint(
                condition=Q(old_price__isnull=True) | Q(old_price__gte=models.F("price")),
                name="old_price_gte_price_or_null",
            ),
        ]

    def __str__(self):
        parts = [self.product.name]
        if self.color_id:
            parts.append(str(self.color))
        if self.size:
            parts.append(self.size)
        return " / ".join(parts)


class ProductImage(models.Model):
    """
    Фотки товара (не привязаны к цвету).
    Можно выбрать "главную" — для каталога.
    """
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField("Фото", upload_to="products/")
    is_main = models.BooleanField("Главное фото", default=False)
    sort = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["sort", "id"]
        indexes = [models.Index(fields=["product", "is_main"])]

    def __str__(self):
        return f"Image for {self.product.name}"

class ProductReview(models.Model):
    product = models.ForeignKey(
        Product,
        related_name="reviews",
        on_delete=models.CASCADE
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    rating = models.PositiveSmallIntegerField(
        "Оценка (1-5)",
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )

    text = models.TextField("Отзыв", blank=True)

    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["product", "is_published"]),
            models.Index(fields=["product", "created_at"]),
        ]
        ordering = ["-created_at"]

        # если хочешь: 1 отзыв на 1 товар от 1 пользователя
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                condition=models.Q(user__isnull=False),
                name="uniq_review_per_user_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.rating}"

class StoreSocial(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name='socials'
    )

    name = models.CharField(max_length=50)      # Instagram, Telegram, WhatsApp
    link = models.URLField(max_length=255)

    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.store.name} — {self.name}"

