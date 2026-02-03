from django import forms
from django.forms import inlineformset_factory

from .models import (
    Product, ProductColor, ProductVariant,
    Category, Brand, Gender
)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "category", "gender", "brand", "description", "country", "material"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, store=None, **kwargs):
        super().__init__(*args, **kwargs)

        if store is not None:
            self.fields["category"].queryset = Category.objects.filter(store=store, is_active=True)
            self.fields["brand"].queryset = Brand.objects.filter(store=store, is_active=True)

        self.fields["gender"].queryset = Gender.objects.all()


class ColorForm(forms.ModelForm):
    class Meta:
        model = ProductColor
        fields = ["name", "hex"]
        widgets = {
            "hex": forms.HiddenInput(),  # HEX приходит из color-picker
        }


class VariantForm(forms.ModelForm):
    """
    ВАЖНО:
    Мы НЕ используем FK `color` в форме при создании товара,
    потому что цветов ещё нет в БД.
    Вместо этого выбираем `color_hex` (ChoiceField),
    а во view после сохранения цветов — ставим FK color.
    """
    color_hex = forms.ChoiceField(required=False)

    class Meta:
        model = ProductVariant
        fields = ["color_hex", "size", "price"]
        widgets = {
            "size": forms.TextInput(attrs={"placeholder": "Напр. XL / 42 / 128GB"}),
        }

    def __init__(self, *args, color_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["color_hex"].choices = [("", "---------")] + (color_choices or [])


ColorFormSet = inlineformset_factory(
    Product, ProductColor,
    form=ColorForm,
    extra=1,
    can_delete=True
)

VariantFormSet = inlineformset_factory(
    Product, ProductVariant,
    form=VariantForm,
    extra=1,
    can_delete=True
)
