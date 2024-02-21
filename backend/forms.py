from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Shop, User


class ShopForm(forms.ModelForm):
    shop = forms.ModelChoiceField(queryset=Shop.objects.all(), empty_label=None)
    class Meta:
        model = Shop
        fields = ['name']

class ProductSearchForm(forms.Form):
    search_query = forms.CharField(max_length=100, required=False, label='Поиск продуктов')

class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = User
        fields = ['username', 'password1', 'password2']