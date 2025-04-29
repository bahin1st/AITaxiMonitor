from django import forms

from .models import Customer

class DriverSearchForm(forms.Form):
    full_name = forms.CharField(max_length=100, label="Driver's Full Name")
    
    
    

class RegistrationForm(forms.Form):
    ROLE_CHOICES = (
        ('driver', 'Driver'),
        ('customer', 'Customer'),
    )

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border rounded-md focus:ring focus:ring-indigo-200'
        })
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border rounded-md focus:ring focus:ring-indigo-200'
        })
    )
    telegram_chat_id = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border rounded-md focus:ring focus:ring-indigo-200'
        })
    )
    license_number = forms.CharField(max_length=20, required=False,
         widget=forms.TextInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border rounded-md focus:ring focus:ring-indigo-200'
        })                             
    )
    new_taxi_lat = forms.FloatField(max_value=180, min_value=-180, required=False,
         widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border rounded-md focus:ring focus:ring-indigo-200'
        })
    )
    new_taxi_lon = forms.FloatField(max_value=90, min_value=-90, required=False,
         widget=forms.NumberInput(attrs={
            'class': 'mt-1 block w-full px-4 py-2 border rounded-md focus:ring focus:ring-indigo-200'
        })
    )
    
    
    role = forms.ChoiceField(choices=ROLE_CHOICES)




class CustomerForm(forms.Form):
    customer = forms.ModelChoiceField(queryset=Customer.objects.all(), initial=1)