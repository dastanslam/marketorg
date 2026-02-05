import re
import secrets
from django.utils import timezone
from django.db import models, transaction, IntegrityError
from django.db.models import Avg, Count, Q, F, Min, Max
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal, ROUND_HALF_UP

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

hex_validator = RegexValidator(
    regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$',
    message='Введите корректный HEX-код (например, #FFFFFF)'
)


def _norm(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", (s or "").strip()).strip("-").lower()


class Category(models.Model):
    store = models.ForeignKey("Store", related_name="categories", on_delete=models.CASCADE)
    name = models.CharField("Название", max_length=100)
    image = models.ImageField("Фото категории", upload_to="categories/", blank=True, null=True)
    slug = models.SlugField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)
    discount_percent = models.PositiveSmallIntegerField("Скидка (%)", default=0)
    discount_active = models.BooleanField(default=False)
    discount_start = models.DateTimeField(null=True, blank=True)
    discount_end = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="uniq_category_slug_per_store")
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "category"
            slug = base
            i = 2
            # проверяем уникальность slug в рамках store
            while Category.objects.filter(store=self.store, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def discount_is_active_now(self):
        if not self.discount_active or not self.discount_percent:
            return False
        now = timezone.now()
        if self.discount_start and now < self.discount_start:
            return False
        if self.discount_end and now > self.discount_end:
            return False
        return True


class Brand(models.Model):
    store = models.ForeignKey("Store", related_name="brands", on_delete=models.CASCADE)
    name = models.CharField("Название", max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Бренд"
        verbose_name_plural = "Бренды"
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="uniq_brand_slug_per_store")
        ]
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or "brand"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Gender(models.Model):
    name = models.CharField("Название", max_length=50, unique=True)

    class Meta:
        verbose_name = "Пол"
        verbose_name_plural = "Полы"
        ordering = ["id"]

    def __str__(self):
        return self.name


class Product(models.Model):
    store = models.ForeignKey("Store", related_name="products", on_delete=models.CASCADE)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    brand = models.ForeignKey(Brand, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)
    gender = models.ForeignKey(Gender, related_name="products", on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField("Название", max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField("Описание", blank=True)

    country = models.CharField("Страна производитель", max_length=100, blank=True)
    material = models.CharField("Тип материала", max_length=100, blank=True)

    # Статистика
    views = models.PositiveIntegerField("Просмотры", default=0)
    rating_avg = models.DecimalField("Средний рейтинг", max_digits=3, decimal_places=2, default=0)
    rating_count = models.PositiveIntegerField("Кол-во отзывов", default=0)

    # Денормализация цен
    min_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)
    max_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [
            models.Index(fields=["store", "is_active"]),
            models.Index(fields=["min_price", "max_price"]),
            models.Index(fields=["created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="uniq_product_slug_per_store"),
        ]

    def update_rating(self):
        stats = self.reviews.filter(is_published=True).aggregate(
            avg=Avg("rating"),
            count=Count("id")
        )
        avg = stats["avg"] or 0
        count = stats["count"] or 0
        Product.objects.filter(pk=self.pk).update(rating_avg=avg, rating_count=count)
        self.rating_avg = avg
        self.rating_count = count

    def update_prices(self):
        stats = self.variants.filter(is_active=True).aggregate(
            min_p=Min("price"),
            max_p=Max("price")
        )
        min_p = stats["min_p"] or 0
        max_p = stats["max_p"] or 0
        Product.objects.filter(pk=self.pk).update(min_price=min_p, max_price=max_p)
        self.min_price = min_p
        self.max_price = max_p

    def save(self, *args, **kwargs):
        # Slug: optimistic + IntegrityError retry (anti-race)
        if self.slug:
            return super().save(*args, **kwargs)

        base = slugify(self.name) or "product"
        slug = base

        for _ in range(8):
            self.slug = slug
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                suffix = secrets.token_hex(2)  # 4 hex
                slug = f"{base}-{suffix}"

        self.slug = f"{base}-{secrets.token_hex(4)}"
        with transaction.atomic():
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.store.name})"


class ProductColor(models.Model):
    product = models.ForeignKey(Product, related_name="colors", on_delete=models.CASCADE)
    name = models.CharField("Название цвета", max_length=50, blank=True)
    hex = models.CharField("HEX", max_length=7, validators=[hex_validator])

    class Meta:
        verbose_name = "Цвет товара"
        verbose_name_plural = "Цвета товаров"
        constraints = [
            models.UniqueConstraint(fields=["product", "hex"], name="uniq_hex_per_product"),
        ]

    def __str__(self):
        return self.name or self.hex


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, related_name="variants", on_delete=models.CASCADE)
    color = models.ForeignKey(ProductColor, related_name="variants", on_delete=models.SET_NULL, null=True, blank=True)

    size = models.CharField("Размер", max_length=20, blank=True)
    sku = models.CharField("SKU / Артикул", max_length=64, blank=True, db_index=True)

    price = models.DecimalField("Цена", max_digits=10, decimal_places=2)
    old_price = models.DecimalField("Старая цена", max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField("Остаток", default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Вариант товара"
        verbose_name_plural = "Варианты товаров"
        constraints = [
            models.UniqueConstraint(fields=["product", "color", "size"], name="uniq_variant_per_product"),
            models.CheckConstraint(
                condition=Q(old_price__isnull=True) | Q(old_price__gte=F("price")),
                name="old_price_gte_price",
            ),
        ]

    def save(self, *args, update_parent: bool = True, **kwargs):
        # SKU auto (если не задан)
        if not self.sku and self.product_id:
            color_part = "nocolor"
            if self.color_id and self.color and self.color.hex:
                color_part = self.color.hex.replace("#", "").lower()
            size_part = _norm(self.size) or "nosize"
            self.sku = f"{self.product.slug}-{color_part}-{size_part}"[:64]

        # change detection (чтобы не дёргать Product.update_prices без нужды)
        need_parent_update = False
        if self.pk:
            old = ProductVariant.objects.filter(pk=self.pk).values("price", "is_active").first()
            if old and (old["price"] != self.price or old["is_active"] != self.is_active):
                need_parent_update = True
        else:
            need_parent_update = True

        super().save(*args, **kwargs)

        if update_parent and need_parent_update:
            self.product.update_prices()

    def __str__(self):
        return f"{self.product.name} | {self.color} | {self.size}"

    @property
    def price_final(self):
        cat = self.product.category
        if not cat or not cat.discount_is_active_now():
            return self.price
        d = Decimal(cat.discount_percent) / Decimal("100")
        res = self.price * (Decimal("1") - d)
        return res.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def old_price_effective(self):
        # чтобы на витрине показать "старая цена"
        if self.product.category and self.product.category.discount_is_active_now():
            return self.price
        return self.old_price


class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    color = models.ForeignKey(ProductColor, related_name="images", on_delete=models.SET_NULL, null=True, blank=True)

    image = models.ImageField("Фото", upload_to="products/%Y/%m/")
    is_main = models.BooleanField("Главное фото", default=False)
    sort = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        verbose_name = "Изображение"
        verbose_name_plural = "Изображения"
        ordering = ["sort", "id"]

    def __str__(self):
        return f"Image for {self.product.name}"


class ProductReview(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    rating = models.PositiveSmallIntegerField(
        "Оценка (1-5)",
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    text = models.TextField("Отзыв", blank=True)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                condition=Q(user__isnull=False),
                name="uniq_review_per_user_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} - {self.rating}"


# --- СИГНАЛЫ ---
@receiver([post_save, post_delete], sender=ProductReview)
def handle_review_change(sender, instance, **kwargs):
    instance.product.update_rating()


@receiver(post_delete, sender=ProductVariant)
def handle_variant_delete(sender, instance, **kwargs):
    # при одиночном delete ок
    instance.product.update_prices()

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

