from django.contrib import admin
from .models import Driver, Taxi, Anomaly, Customer,Dispatcher


from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import Taxi
import json

# Define a custom form for uploading GeoJSON files
class TaxiAdminForm(forms.ModelForm):
    geojson_file = forms.FileField(required=False)  # File field for GeoJSON file upload

    class Meta:
        model = Taxi
        fields = '__all__'

    def clean_geojson_file(self):
        geojson_file = self.cleaned_data.get('geojson_file')
        if geojson_file:
            try:
                # Read the GeoJSON file and return as a JSON object
                file_content = geojson_file.read().decode('utf-8')
                geojson_data = json.loads(file_content)
                return geojson_data
            except json.JSONDecodeError:
                raise ValidationError("Invalid GeoJSON file format")
        return None

    def save(self, commit=True):
        taxi = super().save(commit=False)
        geojson_data = self.cleaned_data.get('geojson_file')

        if geojson_data:
            taxi.set_route_from_geojson(geojson_data)  # Set route from GeoJSON
        if commit:
            taxi.save()
        return taxi

# Register the model and form in the Django admin
class TaxiAdmin(admin.ModelAdmin):
    form = TaxiAdminForm
    list_display = ['plate_number', 'model', 'is_active', 'current_lat', 'current_lon']

admin.site.register(Taxi, TaxiAdmin)



admin.site.register(Driver)
admin.site.register(Anomaly)



class CustomerAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'telegram_chat_id']

admin.site.register(Customer, CustomerAdmin)



class DispatcherAdmin(admin.ModelAdmin):
    list_display = ['user', 'fullname', 'phone_number', 'telegram_chat_id']

admin.site.register(Dispatcher, DispatcherAdmin)    