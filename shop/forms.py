from django import forms
from django.forms import inlineformset_factory
from .models import (
    Product, ProductColor, ProductVariant,
    Category, Brand, Gender
)

class ProductForm(forms.ModelForm):
    # НЕ модельные поля, принимают и id, и текст
    category = forms.CharField(required=False)
    brand = forms.CharField(required=False)

    class Meta:
        model = Product
        # ВАЖНО: category/brand тут НЕТ
        fields = ["name", "gender", "description", "country", "material"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название товара"}),
            "gender": forms.Select(attrs={"class": "select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Напишите описание товара..."
            }),
            "country": forms.TextInput(attrs={"class": "form-control", "placeholder": "Напр. Казахстан"}),
            "material": forms.TextInput(attrs={"class": "form-control", "placeholder": "Напр. хлопок"}),
        }

    def __init__(self, *args, store=None, **kwargs):
        super().__init__(*args, **kwargs)

        # для select2
        self.fields["category"].widget.attrs.update({"class": "select2-enable"})
        self.fields["brand"].widget.attrs.update({"class": "select2-enable"})

        self.fields["gender"].queryset = Gender.objects.all()

        # queryset'ы для шаблона (список опций)
        self.category_qs = Category.objects.filter(store=store, is_active=True) if store else Category.objects.none()
        self.brand_qs = Brand.objects.filter(store=store, is_active=True) if store else Brand.objects.none()


# =========================
# VARIANTS
# =========================

class VariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["color", "size", "price", "sku"]
        widgets = {
            "color": forms.Select(attrs={"class": "select"}),
            "size": forms.TextInput(attrs={"class": "form-control", "placeholder": "Напр. XL / 42"}),
            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Цена",
                "min": "0",
                "oninput": "this.value = this.value.replace(/[^0-9]/g, '');"
            }),
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "Артикул (авто)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["color"].queryset = ProductColor.objects.all()
        self.fields["color"].empty_label = "Выберите цвет"


VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=VariantForm,
    extra=1,
    can_delete=True
)