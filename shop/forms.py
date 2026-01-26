# forms.py
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError

from .models import Product, ProductVariant, ProductColor, ProductImage, ProductReview


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "description",
            "country", "material",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class ProductColorForm(forms.ModelForm):
    class Meta:
        model = ProductColor
        fields = ["name", "hex"]

    def clean_hex(self):
        hx = (self.cleaned_data.get("hex") or "").strip()
        return hx.upper()  # чтоб #ff00aa и #FF00AA не считались разными


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["color", "size", "sku", "price", "old_price", "stock", "is_active"]

    def clean(self):
        cleaned = super().clean()
        price = cleaned.get("price")
        old_price = cleaned.get("old_price")
        if price is not None and old_price is not None and old_price < price:
            raise ValidationError({"old_price": "Старая цена должна быть больше или равна текущей цене."})
        return cleaned


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "is_main", "sort"]


# --- Formsets (встраиваемые формы) ---

ProductColorFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductColor,
    form=ProductColorForm,
    fields=["name", "hex"],
    extra=1,
    can_delete=True,
)

ProductVariantFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductVariant,
    form=ProductVariantForm,
    fields=["color", "size", "sku", "price", "old_price", "stock", "is_active"],
    extra=1,
    can_delete=True,
)

ProductImageFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductImage,
    form=ProductImageForm,
    fields=["image", "is_main", "sort"],
    extra=1,
    can_delete=True,
)


# Если хочешь добавлять отзывы вручную (обычно не надо для продавца)
ProductReviewFormSet = inlineformset_factory(
    parent_model=Product,
    model=ProductReview,
    fields=["user", "rating", "text", "is_published"],
    extra=0,
    can_delete=True,
)
