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
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Напишите описание товара..."}),
            "country": forms.TextInput(attrs={"placeholder": "Напр. Казахстан / Россия"}),
            "material": forms.TextInput(attrs={"placeholder": "Напр. хлопок / кожа / пластик"}),
            "name": forms.TextInput(attrs={"placeholder": "Название товара"}),
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

        # ✅ кастомные подписи вместо "---------"
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
# COLORS
# =========================

class ColorForm(forms.ModelForm):
    class Meta:
        model = ProductColor
        fields = ["name", "hex"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Напр. серый / белый"}),
            "hex": forms.HiddenInput(),
        }


# =========================
# VARIANTS
# =========================

class VariantForm(forms.ModelForm):
    """
    Выбираем color_hex (не FK),
    потом во view связываем с ProductColor
    """
    color_hex = forms.ChoiceField(required=False)

    class Meta:
        model = ProductVariant
        fields = ["color_hex", "size", "price"]
        widgets = {
            "size": forms.TextInput(attrs={"placeholder": "Напр. XL / 42 / 128GB"}),
            "price": forms.NumberInput(attrs={"placeholder": "Напр. 10000"}),
        }

    def __init__(self, *args, color_choices=None, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ кастомная пустая опция
        self.fields["color_hex"].choices = (
            [("", "Выберите цвет")] + list(color_choices or [])
        )


# =========================
# FORMSETS
# =========================

ColorFormSet = inlineformset_factory(
    Product,
    ProductColor,
    form=ColorForm,
    extra=1,
    can_delete=True
)

VariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=VariantForm,
    extra=1,
    can_delete=True
)
