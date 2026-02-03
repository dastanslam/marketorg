# forms.py
from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError
from .models import Product, ProductVariant, ProductColor, ProductImage, ProductReview


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "gender",
            "brand",
            "description",
            "country",
            "material",
            "is_active",
        ]


class VariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["price", "old_price", "stock", "sku", "size", "is_active"]


ColorFormSet = inlineformset_factory(
    Product, ProductColor,
    fields=("name", "hex"),
    extra=1,
    can_delete=True
)

ImageFormSet = inlineformset_factory(
    Product, ProductImage,
    fields=("image", "is_main", "sort"),
    extra=0,
    can_delete=True
)


