from django.db import models
from django.contrib.auth.models import User

import random

import json


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    telegram_chat_id = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.user.username
class Taxi(models.Model):
    current_metrics = models.JSONField(default=dict)  # Dictionary to store metrics like speed, acceleration, etc.
    current_ride_name = models.CharField(default="unknown", max_length=300)
    plate_number = models.CharField(max_length=15, unique=True)
    model = models.CharField(max_length=50, default="Toyota Prius")
    current_lat = models.FloatField(default=43.239819)
    current_lon = models.FloatField(default=76.903932)
    heading = models.FloatField(default=0.0)
    is_active = models.BooleanField(default=False)
    on_trip_status= models.CharField(max_length=50, default="not on trip")
    current_passenger = models.OneToOneField(Customer, on_delete=models.CASCADE, blank=True, null=True)
    passenger_in_danger = models.BooleanField(default=False)
    route = models.JSONField(default=list, blank=True)  # List of (lat, lon) points

    def __str__(self):
        return self.plate_number

    def set_route_from_geojson(self, geojson_data):
        """Extracts and sets the route from the provided GeoJSON data"""
        if geojson_data.get('geometry', {}).get('type') == 'LineString':
            coordinates = geojson_data['geometry']['coordinates']
            # Reverse the coordinates from [lon, lat] to [lat, lon]
            self.route = [[lon, lat] for lon, lat in coordinates]
        else:
            raise ValueError("Invalid GeoJSON format: Expected LineString geometry")




class Dispatcher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    profil_picture = models.ImageField(upload_to='static/profile_pictures/', null=True, blank=True, default='static/profile_pictures/profile.png')
    
    telegram_chat_id = models.CharField(max_length=50, null=True, blank=True)
    

    def __str__(self):
        return self.user.username

class Driver(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profil_picture = models.ImageField(upload_to='static/profile_pictures/', null=True, blank=True, default='static/profile_pictures/profile.png')
    license_number = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15)
    assigned_taxi = models.OneToOneField(Taxi, on_delete=models.CASCADE, null=True, blank=True)
    telegram_chat_id = models.CharField(max_length=50, null=True, blank=True)
    
    new_taxi_lat = models.FloatField(default=0.0)
    new_taxi_lon = models.FloatField(default=0.0)
    

    def save(self, *args, **kwargs):
        
        if not self.assigned_taxi:
            # Create a taxi when a driver is registered
            taxi = Taxi.objects.create(
                plate_number=f"TAXI-{random.randint(1000, 9999)}",
                current_lat=self.new_taxi_lat,  # Random location (adjust as needed)
                current_lon=self.new_taxi_lon
            )
            self.assigned_taxi = taxi
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username



class Anomaly(models.Model):
    metrics = models.JSONField(default=dict)
    ride_name = models.CharField(max_length=300, default="unknown")
    lat = models.FloatField(default=43.239819)
    long = models.FloatField(default=76.903932)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.type} - {self.driver.user.username} - {self.timestamp}"
    
class DailyAnomaly(models.Model):
    metrics = models.JSONField(default=dict)
    ride_name = models.CharField(max_length=300, default="unknown")
    lat = models.FloatField(default=43.239819)
    long = models.FloatField(default=76.903932)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=50)  # e.g., "Harsh Braking", "Overspeeding"

    def __str__(self):
        return f"{self.type} - {self.driver.user.username} - {self.timestamp}"

class WeeklyAnomaly(models.Model):
    metrics = models.JSONField(default=dict)
    ride_name = models.CharField(max_length=300, default="unknown")
    lat = models.FloatField(default=43.239819)
    long = models.FloatField(default=76.903932)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=50)  # e.g., "Harsh Braking", "Overspeeding"

    def __str__(self):
        return f"{self.type} - {self.driver.user.username} - {self.timestamp}"
    
    
class Trip(models.Model):
    trip_name = models.CharField(max_length=300, default="unknown")#
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)#
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)#
    taxi = models.ForeignKey(Taxi, on_delete=models.CASCADE)#
    start_time = models.DateTimeField(null=True, blank=True)#
    finish_time = models.DateTimeField(null=True, blank=True)#
    distance = models.FloatField(default=0.0)
    duration = models.FloatField(default=0.0)#
    start_finish_lat_lon = models.JSONField(default=list, blank=True)#
    rating = models.FloatField(default=0.0)

    
    def __str__(self):
        return f"Trip by {self.driver.assigned_taxi} from {self.trip_name}"

    
class EndangeredPassengerCase(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE)
    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    investigator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Case: {self.trip_name} by {self.driver.user.username}"

    
