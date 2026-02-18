from django import forms
from django.forms import inlineformset_factory
from .models import (
    Product, ProductColor, ProductVariant,
    Category, Brand, Gender
)

# =========================
# PRODUCT
# =========================

class ProductForm(forms.ModelForm):
    new_brand = forms.CharField(
        required=False,
        label="Новый бренд",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Если нет в списке — напишите новый бренд"
        })
    )

    class Meta:
        model = Product
        fields = [
            "name", "category", "gender", "brand",
            "new_brand", "description", "country", "material"
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название товара"}),
            "category": forms.Select(attrs={"class": "select"}),
            "gender": forms.Select(attrs={"class": "select"}),
            "brand": forms.Select(attrs={"class": "select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Напишите описание товара..."}),
            "country": forms.TextInput(attrs={"class": "form-control", "placeholder": "Напр. Казахстан"}),
            "material": forms.TextInput(attrs={"class": "form-control", "placeholder": "Напр. хлопок"}),
        }

    def __init__(self, *args, store=None, **kwargs):
        self.store = store
        super().__init__(*args, **kwargs)

        if store is not None:
            self.fields["category"].queryset = Category.objects.filter(
                store=store, is_active=True
            )
            self.fields["brand"].queryset = Brand.objects.filter(
                store=store, is_active=True
            )

        self.fields["gender"].queryset = Gender.objects.all()

        # Кастомные подписи
        self.fields["category"].empty_label = "Выберите категорию"
        self.fields["gender"].empty_label = "Выберите пол"
        self.fields["brand"].empty_label = "Выберите бренд"

    def clean(self):
        cleaned = super().clean()
        brand = cleaned.get("brand")
        new_brand = (cleaned.get("new_brand") or "").strip()

        if not brand and not new_brand:
            raise forms.ValidationError(
                "Выберите бренд из списка или введите новый."
            )
        return cleaned


# =========================
# VARIANTS
# =========================

class VariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        # Теперь выбираем 'color' (это ForeignKey к ProductColor)
        fields = ["color", "size", "price", "sku"]
        widgets = {
            "color": forms.Select(attrs={"class": "select"}),
            "size": forms.TextInput(attrs={"class": "form-control", "placeholder": "Напр. XL / 42"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Цена"}),
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "Артикул (авто)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Загружаем все цвета, которые вы создали сами
        self.fields["color"].queryset = ProductColor.objects.all()
        self.fields["color"].empty_label = "Выберите цвет"


# =========================
# FORMSETS
# =========================

# ColorFormSet УДАЛЕН, так как ProductColor больше не связан с Product напрямую.

VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=VariantForm,
    extra=1,
    can_delete=True
)