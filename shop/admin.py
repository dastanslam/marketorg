from django.contrib import admin
from .models import *
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError
from django import forms

class ProductColorInlineForm(forms.ModelForm):
    class Meta:
        model = ProductColor
        fields = ("name", "hex")
        widgets = {
            "hex": forms.TextInput(attrs={"type": "color", "style": "width:60px; padding:0;"}),
        }


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "subdomain", "phone", "email", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "subdomain", "phone", "email")
    readonly_fields = ("subdomain", "created_at")  # subdomain авто
    ordering = ("-created_at",)

class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ("color", "size", "sku", "price", "old_price", "stock", "is_active")
    autocomplete_fields = ("color",)
    show_change_link = True


class ProductColorInline(admin.TabularInline):
    model = ProductColor
    form = ProductColorInlineForm
    extra = 1
    fields = ("name", "hex")


class ProductImageInlineFormSet(BaseInlineFormSet):
    """
    1) Не даём поставить больше одной main
    2) Если выбрали одну main — остальные станут не main (сделаем в save_related)
    """
    def clean(self):
        super().clean()
        main_count = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("is_main"):
                main_count += 1
        if main_count > 1:
            raise ValidationError("Можно выбрать только одно главное фото (is_main).")


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ("image", "is_main", "sort")
    formset = ProductImageInlineFormSet
    show_change_link = True


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "store", "is_active", "views", "created_at")
    list_filter = ("is_active", "store")
    search_fields = ("name", "store__name", "store__subdomain")
    ordering = ("-created_at",)

    prepopulated_fields = {"slug": ("name",)}
    list_select_related = ("store",)

    inlines = (ProductColorInline, ProductVariantInline, ProductImageInline)

    def save_related(self, request, form, formsets, change):
        """
        Авто-снятие is_main у остальных фоток, если выбрали одну главную.
        """
        super().save_related(request, form, formsets, change)
        product = form.instance

        main = product.images.filter(is_main=True).order_by("id").first()
        if main:
            product.images.exclude(id=main.id).update(is_main=False)


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ("product", "color", "size", "price", "old_price", "stock", "is_active")
    list_filter = ("is_active", "product__store")
    search_fields = ("product__name", "sku", "size")
    list_select_related = ("product", "color", "product__store")
    ordering = ("-created_at",)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("product", "is_main", "sort")
    list_filter = ("is_main", "product__store")
    search_fields = ("product__name",)
    list_select_related = ("product", "product__store")
    ordering = ("product", "sort", "id")


@admin.register(ProductColor)
class ProductColorAdmin(admin.ModelAdmin):
    list_display = ("product", "name", "hex")
    search_fields = ("product__name", "name", "hex")
    list_select_related = ("product",)

class ProductReviewInline(admin.TabularInline):
    model = ProductReview
    extra = 0
    fields = ("user", "rating", "text", "is_published", "created_at")
    readonly_fields = ("created_at",)

# и в ProductAdmin добавь в inlines:
inlines = (ProductColorInline, ProductVariantInline, ProductImageInline, ProductReviewInline)
