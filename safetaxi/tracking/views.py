
from datetime import datetime, timezone,timedelta
import pandas as pd
from .anomaly_detector import rate_trip_model
from collections import defaultdict
from django.db import models
import traceback
from .models import Taxi, Trip, Driver, Customer
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Count
from datetime import timedelta
from .models import Driver, Trip, Anomaly, WeeklyAnomaly, DailyAnomaly, Taxi, EndangeredPassengerCase
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .form import RegistrationForm, CustomerForm
from django.db.models import Q
import os
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse, Http404
import google.generativeai as genai

from django.shortcuts import get_object_or_404
from .utils import generate_taxi_data_from_geojson
import subprocess
import threading
import random
import time
from django.conf import settings

genai.configure(api_key= settings.geaiKey)  # Hardcoded , I am aware!


def home(request):
    
    
    drivers = Driver.objects.all()
    users = User.objects.all()
    return render(request, 'tracking/home.html', {'users': users, 'drivers': drivers })





def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            phone_number = form.cleaned_data['phone_number']
            telegram_chat_id = form.cleaned_data['telegram_chat_id']
            role = form.cleaned_data['role']
            license_number = form.cleaned_data['license_number']
            new_taxi_lat = form.cleaned_data['new_taxi_lat']
            new_taxi_lon = form.cleaned_data['new_taxi_lon']

            user = User.objects.create(username=username)

            if role == 'driver':
                Driver.objects.create(
                    user=user,
                    phone_number=phone_number,
                    telegram_chat_id=telegram_chat_id,
                    license_number=license_number,
                    new_taxi_lat=new_taxi_lat,
                    new_taxi_lon=new_taxi_lon
                    
                )
            else:
                Customer.objects.create(
                    user=user,
                    phone_number=phone_number,
                    telegram_chat_id=telegram_chat_id
                )
                return redirect('home')

            return redirect('driver_navigation_dashboard', username=username)

              
    else:
        form = RegistrationForm()
    
    return render(request, 'tracking/register.html', {'form': form})





def driver_profile(request, username):
    
    
    from django.utils.timezone import now

    try:
        driver = get_object_or_404(Driver, user__username__iexact=username)
    except Driver.DoesNotExist:
        print(traceback.format_exc())
        
        
        
    all_anomalies = Anomaly.objects.all().values('ride_name')

    trips = Trip.objects.filter(driver=driver).order_by('-start_time')
    anomaly_counts = defaultdict(int)
    for anomaly in all_anomalies:
        anomaly_counts[anomaly['ride_name']] += 1

    for trip in trips:
        trip.anomaly_count = anomaly_counts.get(trip.trip_name, 0)
    
    
    # Calculate total distance and average rating
    stats = trips.aggregate(
        total_distance=Sum('distance'),
        average_rating=Avg('rating')
    )
    total_distance = stats['total_distance'] or 0
    average_rating = round(stats['average_rating'] or 0, 1)
    
    # Get weekly anomalies
    one_week_ago = now() - timedelta(days=7)
    weekly_anomalies = WeeklyAnomaly.objects.filter(
        driver=driver,
        timestamp__gte=one_week_ago
    ).order_by('-timestamp')
    
    # Get yearly anomalies for the chart
    one_year_ago = now() - timedelta(days=365)
    yearly_anomalies = Anomaly.objects.filter(
        driver=driver,
        timestamp__gte=one_year_ago
    )
    
  
    
    
    
    
    one_month_ago = now() - timedelta(days=29)
    monthly_anomalies = Anomaly.objects.filter(
        driver=driver,
        timestamp__gte=one_year_ago
    )
    
    
    anomaly_types = ['sudden_brake', 'sudden_acceleration', 'sudden_stop',
        'sudden_turn', 'tight_turn', 'speeding']
    colors = {
        'speeding': 'rgba(255, 99, 132, 0.5)',
        'sudden_brake': 'rgba(54, 162, 235, 0.5)',
        'sudden_acceleration': 'rgba(255, 205, 86, 0.5)',
        'sudden_stop': 'rgba(75, 192, 192, 0.5)',
        'sudden_turn': 'rgba(255, 99, 132, 0.5)',
        'tight_turn': 'rgba(54, 162, 235, 0.5)',
    }
    # Prepare monthly anomaly data for the chart
    chart_data = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'datasets': []
    }

# Initialize dictionary with 0s for each month and anomaly type
    monthly_anomalies_count = {month: {atype: 0 for atype in anomaly_types} for month in range(1, 13)}

    # Count anomalies by month and type
    for anomaly in yearly_anomalies:
        month = anomaly.timestamp.month
        anomaly_type = anomaly.type
        if anomaly_type in anomaly_types:
            monthly_anomalies_count[month][anomaly_type] += 1

        
    for anomaly_type in anomaly_types:
        dataset = {
            'label': anomaly_type,
            'data': [monthly_anomalies_count[month][anomaly_type] for month in range(1, 13)],
            'backgroundColor': colors[anomaly_type],
            'borderColor': colors[anomaly_type].replace('0.5', '1'),
            'borderWidth': 1
        }
        chart_data['datasets'].append(dataset)

        
        
        
    
    
    
    
    
    
    context = {
        'driver': driver,
        'trips': trips,
        'total_distance': total_distance,
        'average_rating': average_rating,
        'weekly_anomalies': weekly_anomalies,
        'yearly_anomalies_chart_data': chart_data,
    }
    
    return render(request, 'tracking/driver_profile.html', context)

def update_driver_info(request, username):
   
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method is allowed'})
    
    try:
        import json
        data = json.loads(request.body)
        
        driver = Driver.objects.filter(user__username__iexact=username).first()

        
        # Update fields
        if 'license_number' in data:
            driver.license_number = data['license_number']
        
        if 'telegram_chat_id' in data:
            driver.telegram_chat_id = data['telegram_chat_id']
        
        driver.save()
        
        return JsonResponse({'success': True})
    
    except Driver.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Driver not found'})
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def get_anomaly_details(request, anomaly_id):
    
    try:
        anomaly = None
        
        try:
            anomaly = WeeklyAnomaly.objects.get(id=anomaly_id, driver__user=request.user)
        except WeeklyAnomaly.DoesNotExist:
            pass
        
        if not anomaly:
            try:
                anomaly = DailyAnomaly.objects.get(id=anomaly_id, driver__user=request.user)
            except DailyAnomaly.DoesNotExist:
                pass
        
        if not anomaly:
            try:
                anomaly = Anomaly.objects.get(id=anomaly_id, driver__user=request.user)
            except Anomaly.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Anomaly not found'})
        
        return JsonResponse({
            'success': True,
            'anomaly': {
                'id': anomaly.id,
                'type': anomaly.type,
                'timestamp': anomaly.timestamp.strftime('%B %d, %Y %H:%M'),
                'location': f"{anomaly.lat}, {anomaly.long}",
                'ride_name': anomaly.ride_name,
                'metrics': anomaly.metrics
            }
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
    
def get_taxis(request):
    taxis = Taxi.objects.filter(is_active=True).values('plate_number', 'current_lat', 'current_lon')
    return JsonResponse(list(taxis), safe=False)

def taxi_map(request):
    mapboxApiKey = settings.mapboxApiKey
    return render(request, 'tracking/map.html', {"mapboxApiKey": mapboxApiKey})


@csrf_exempt
def driver_details(request, username):
    from django.core.serializers.json import DjangoJSONEncoder
    from datetime import datetime, timedelta
    from django.utils.timezone import now

    # Fetch the driver
    driver = Driver.objects.filter(user__username__iexact=username).first()
    
    if not driver:
        # Handle case when driver is not found
        messages.error(request, f"Driver with username '{username}' not found.")
        return redirect('some_fallback_url')
    
    # Get the driver's taxi information
    taxi = driver.assigned_taxi
    
    # Get trips data
    trips = Trip.objects.filter(driver=driver).order_by('-start_time')
    
    # Calculate trip stats
    total_trips = trips.count()
    total_distance = sum(trip.distance for trip in trips)
    avg_rating = trips.filter(rating__gt=0).aggregate(models.Avg('rating'))['rating__avg'] or 0
    
    # Get anomalies
    driver_anomalies = Anomaly.objects.filter(driver=driver).order_by('-timestamp')
    
    
    one_month_ago = now() - timedelta(days=30)

    month_radar_anomaly_qs = (
        Anomaly.objects
        .filter(driver=driver, timestamp__range=(one_month_ago, now()))
        .values('type')
        .annotate(count=Count('type'))
        .order_by('-count')
    )

    labels = [item['type'] for item in month_radar_anomaly_qs]
    data = [item['count'] for item in month_radar_anomaly_qs]

    
    
    
    
    
    anomalies = Anomaly.objects.filter(driver=driver).order_by('-timestamp')
    
    anomaly_count = driver_anomalies.count()
    
   
    
    return render(request, 'tracking/driver_details.html', {
        "anomaly_labels": labels,
        "anomaly_data": data,
        'driver': driver,
        'taxi': taxi,
        'trips': trips,
        'total_trips': total_trips,
        'total_distance': total_distance,
        'avg_rating': avg_rating,
        'anomalies': anomalies,
        'anomaly_count': anomaly_count,
        
    })





def driver_search(request):
    query = request.GET.get('search', '')
    if query:
        # Fetch the driver by exact match of the username (case-insensitive search)
        driver = Driver.objects.filter(user__username__iexact=query).first()
        
        if driver:
            driver_info = {
                'name': driver.user.username,
                'license_number': driver.license_number,
                'phone_number': driver.phone_number,
                'taxi_plate': driver.assigned_taxi.plate_number,
                'taxi_model': driver.assigned_taxi.model,
                'taxi_route': driver.assigned_taxi.route,
                'current_lat': driver.assigned_taxi.current_lat,
                'current_lon': driver.assigned_taxi.current_lon,
            }
            
            # Fetch anomalies related to this driver (can filter by time if needed)
            anomalies = Anomaly.objects.filter(driver=driver)
            anomaly_data = []
            for anomaly in anomalies:
                anomaly_data.append({
                    'ride_name': anomaly.ride_name,
                    'type': anomaly.type,
                    'timestamp': anomaly.timestamp,
                })
            
            driver_info['anomalies'] = anomaly_data  # Add anomalies to driver info
            
            return JsonResponse(driver_info)
        else:
            return JsonResponse({'error': 'Driver not found'}, status=404)
    else:
        return JsonResponse({'error': 'No search query provided'}, status=400)


@csrf_exempt

def driver_navigation_dashboard(request, username):
    
    mapboxApiKey = settings.mapboxApiKey
    driver = get_object_or_404(Driver, user__username__iexact=username)
    customers = CustomerForm()
    taxi = driver.assigned_taxi
    print(f"taxi:{taxi}")
    
    current_ride = taxi.current_ride_name
    taxi_status=taxi.is_active
    print(f"current ride:{current_ride}")
    print(f"taxi_status:{taxi_status}")

    
    
    allanomalies = Anomaly.objects.filter(driver=driver).order_by('-timestamp')
    dailyanomalies = DailyAnomaly.objects.filter(driver=driver).order_by('-timestamp')
    weeklyanomalies = WeeklyAnomaly.objects.filter(driver=driver).order_by('-timestamp')
    
    if request.method == 'POST':
        current_ride = request.POST.get('current_ride')
        taxi_is_active = request.POST.get('taxi_is_active')
        reset_metrics = request.POST.get('reset_metrics')
        current_route = json.loads(request.POST.get('current_route'))
        passenger_id = request.POST.get('passenger')

        
        try:
            passenger_id = int(passenger_id)
            passenger = Customer.objects.get(id=passenger_id)
        except (ValueError, Customer.DoesNotExist):
            passenger = None
        
        
        taxi.current_passenger = passenger
        taxi.current_ride_name = current_ride
        taxi.is_active = taxi_is_active    
        taxi.route = current_route   
        taxi.save()
        
        return JsonResponse({'message': 'Current ride updated successfully'})
    
    return render(request, "tracking/driver_navigation_dashboard.html", {"driver": driver, "taxi": taxi, "anomalies": allanomalies,"dailyanomalies": dailyanomalies,"weeklyanomalies": weeklyanomalies, "current_ride": current_ride, "customers": customers, "mapboxApiKey": mapboxApiKey})


  
        


    

@csrf_exempt
def generate_dataset_view(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            route_geojson = body.get("route")
            
            anomaly_ratio = body.get("anomaly_ratio", 0.05)
            print(f"Anomaly ratio: {anomaly_ratio}")
            
            if not route_geojson:
                return JsonResponse({"error": "Missing route data."}, status=400)
            
            output_file = body.get("output_file", "new_simulated_data.csv")
            
            # Generate clean dataset using the provided route GeoJSON
            df = generate_taxi_data_from_geojson(route_geojson, anomaly_ratio, output_file)
            anomaly_counts = df[['sudden_brake', 'sudden_acceleration', 'sudden_stop', 
                         'sudden_turn', 'tight_turn', 'speeding']].sum()
            print("\nAnomaly distribution:")
            for anomaly_type, count in anomaly_counts.items():
                print(f"  {anomaly_type}: {count} instances ({count/len(df)*100:.2f}%)")
            
            
            
            return JsonResponse({"message": "Dataset generated successfully", "output_file": output_file})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    else:
        return JsonResponse({"error": "POST required"}, status=405)


@csrf_exempt
def telegram_webhook(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            username = message.get("chat", {}).get("username")

            print(f"Driver {username} has chat ID: {chat_id}")

            
            return JsonResponse({"ok": True})
        except Exception as e:
            print("Error in webhook:", e)
            return JsonResponse({"ok": False, "error": str(e)})
    return JsonResponse({"message": "Method not allowed"}, status=405)



# Keep track of running simulations by plate number
running_processes = {}

@csrf_exempt
def start_simulation(request):
    result=''
    if request.method == "POST":
        plate_number = request.POST.get("plate_number", "232KAZ").strip().upper()
        trip_status = request.POST.get("trip_status", "start")
        data_file = request.POST.get("data_file", "new_simulated_data.csv")
        taxi = Taxi.objects.filter(plate_number=plate_number).first()
        
        

        sim_script_path = os.path.join(settings.BASE_DIR, "sim.py")
        working_dir = settings.BASE_DIR

        if trip_status == "start":
            try:
                taxi.on_trip_status = "on ride"
                taxi.save()
                def run_simulation():
                    time.sleep(2)
                    venv_python = os.path.join(settings.BASE_DIR, '../venv', 'Scripts', 'python.exe')
                    
                    print(f"venv python path:{venv_python}")

                    command = [venv_python, sim_script_path, data_file, plate_number]
                    

                    process = subprocess.Popen(
                        command,
                        cwd=working_dir
                    )

                    running_processes[plate_number] = process

                threading.Thread(target=run_simulation).start()

            except Exception as e:
                return JsonResponse({"error": f"Error starting simulation: {e}"}, status=500)    
            

            return JsonResponse({"message": f"Simulation for {plate_number} will start in 5 seconds."})


        elif trip_status == "end":
            
        
            taxi.on_trip_status = "not on ride"
            taxi.save()

            process = running_processes.get(plate_number)
            
            print("The ride was ended from the driver side.")
            if process:
                process.terminate()
                del running_processes[plate_number]
                
                return JsonResponse({"message": f"Simulation for {plate_number} has been terminated."})
            else:   
                return JsonResponse({"error": f"No running simulation found for {plate_number}."}, status=404)
    
    return JsonResponse({"error": "Invalid method"}, status=400)



from django.http import JsonResponse

from .models import DailyAnomaly, WeeklyAnomaly
@csrf_exempt
def report_endangered_passenger(request):
    
    try:
        data = json.loads(request.body)

        
        driver_name = data.get("driver")
        plate_number = data.get("plate_number")
        
        taxi = Taxi.objects.filter(plate_number=plate_number).first()
        notes = data.get("notes", "")

        driver = Driver.objects.filter(user__username__iexact=driver_name).first()
        trip = Trip.objects.filter(driver=driver).latest('id')
        

        
        
        case = EndangeredPassengerCase.objects.create(
            driver=driver,
            trip=trip,
            
            investigator=request.user,
            notes=notes
        )
        
        print(f"trip_)_)_)_)_)_)_)_)_)_)_)_)_)_)_)_:{trip}")
        print(f"driver:{driver}")
        print(f"notes:{notes}")
        print(f"request.user:{request.user}")
        # print(f"case:{case}")
        taxi.passenger_in_danger = False
        taxi.save()
        return JsonResponse({"status": "success", "message": "Case reported successfully"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)
    

def trip_detail_view(request, tripName):
    trip = Trip.objects.filter(trip_name=tripName).order_by('finish_time').last()

    if not trip:
        return JsonResponse({"error": "Trip not found yet"}, status=404)

    data = {
        "trip_name": trip.trip_name if trip.trip_name else "N/A",
        "start_time": trip.start_time.strftime("%Y-%m-%d %H:%M:%S") if trip.start_time else "N/A",
        "finish_time": trip.finish_time.strftime("%Y-%m-%d %H:%M:%S") if trip.finish_time else "N/A",
        "distance": float(trip.distance) if trip.distance is not None else "N/A",
        "duration": float(trip.duration) if trip.duration is not None else "N/A",
        "rating": float(trip.rating) if trip.rating is not None else "N/A",
    }

    return JsonResponse(data)


def trip_anomalies(request):
    trip_name = request.GET.get("trip_name")
    anomalies = list(
        Anomaly.objects
               .filter(ride_name=trip_name)
               .order_by("-timestamp")
               .values("type", "timestamp", "metrics")
    )
    for a in anomalies:
        a["timestamp"] = a["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
    return JsonResponse({"anomalies": anomalies})


def cleanup_anomalies(request):
    from django.utils.timezone import now

    now = now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = now - timedelta(days=7)

    daily_deleted, _ = DailyAnomaly.objects.filter(timestamp__lt=today_start).delete()

    weekly_deleted, _ = WeeklyAnomaly.objects.filter(timestamp__lt=seven_days_ago).delete()

    return JsonResponse({
        'status': 'cleanup complete',
        'daily_deleted': daily_deleted,
        'weekly_deleted': weekly_deleted,
    })


from django.shortcuts import redirect
from .models import Anomaly, DailyAnomaly, WeeklyAnomaly

# def copy_anomalies_to_daily_weekly(request):
#     anomalies = Anomaly.objects.all()

#     daily_bulk = []
#     weekly_bulk = []

#     for anomaly in anomalies:
#         daily_bulk.append(DailyAnomaly(
#             metrics=anomaly.metrics,
#             ride_name=anomaly.ride_name,
#             lat=anomaly.lat,
#             long=anomaly.long,
#             driver=anomaly.driver,
#             taxi=anomaly.taxi,
#             timestamp=anomaly.timestamp,
#             type=anomaly.type,
#         ))
#         weekly_bulk.append(WeeklyAnomaly(
#             metrics=anomaly.metrics,
#             ride_name=anomaly.ride_name,
#             lat=anomaly.lat,
#             long=anomaly.long,
#             driver=anomaly.driver,
#             taxi=anomaly.taxi,
#             timestamp=anomaly.timestamp,
#             type=anomaly.type,
#         ))

#     DailyAnomaly.objects.bulk_create(daily_bulk)
#     WeeklyAnomaly.objects.bulk_create(weekly_bulk)

#     return redirect('driver_search')  # or return JsonResponse({"status": "done"})





@csrf_exempt
def rate_trip(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST request required."}, status=400)
    
    
    
    
    try:
        data = json.loads(request.body)
        plate_number = data.get("plate_number").strip().upper()
        taxi = Taxi.objects.filter(plate_number=plate_number).first()
        
        taxi.on_trip_status = "not on ride"
        
        taxi.save()
        
        print("changed back to not on ride")
        # Update trip metadata
        driver_name = data.get("driver_name")
        driver = Driver.objects.filter(user__username=driver_name).first()
        trip_name = data.get("trip_name")
        
        start_time = data.get("start_time")
        finish_time = data.get("finish_time")
        customer_id =data.get('customerId',1)
        customer = Customer.objects.get(id=customer_id)
        
        start_time = datetime.fromtimestamp(start_time / 1000.0, tz=timezone.utc)
        finish_time = datetime.fromtimestamp(finish_time / 1000.0, tz=timezone.utc)

        # 
        random_minutes = random.randint(10, 15) # I add a random time between 10 and 15 minutes because in simulation i need to inject data fast so long distance in short time is not logical.
        finish_time += timedelta(minutes=random_minutes)
        duration = finish_time - start_time

        # Get the duration in seconds
        duration_seconds = duration.total_seconds()

        duration_minutes = duration_seconds / 60
        duratio_minutes = duration_minutes + 10
        
        distance = data.get("distance")
        duration = data.get("duration")
        start_loc = data.get("start_loc")
        end_loc = data.get("end_loc")
        
        rating_result = 6.5
        start_finish_lat_lon = [
        [start_loc.get("lat"), start_loc.get("lng")],
        [end_loc.get("lat"), end_loc.get("lng")]
        
        
        ]
        anomalyCounts = data.get("anomalyCounts")
        
        ordered_columns = [
        'sudden_turn',
        'sudden_brake',
        'tight_turn',
        'sudden_acceleration',
        'speeding',
        'sudden_stop',
        'route_deviation'
        ]

        row_data = {col: anomalyCounts.get(col, 0) for col in ordered_columns}
        row_data['trip_length'] = distance
        
        
        aggregated_anomalies = pd.DataFrame([row_data])[['trip_length'] + ordered_columns]
        
        
        rating_result = rate_trip_model(aggregated_anomalies)
        
        rating_result = round(rating_result * 2) / 2

        
        
        
        
        data_dict = {
        "driver_name": driver_name,
        "driver": driver,
        "taxi": taxi,
        "trip_name": trip_name,
        "start_time": start_time,
        "finish_time": finish_time,
        "distance": distance,
        "duration": duration_minutes,
        "start_loc": start_loc,
        "end_loc": end_loc,
        "start_finish_lat_lon": start_finish_lat_lon,
        "rating_result": rating_result,
        "anomalyCounts": anomalyCounts
        
        }

        print(data_dict)
        print("_____")
        print(aggregated_anomalies)
        Trip.objects.create(
            trip_name=trip_name,
            customer=customer,
            driver=driver,
            taxi=taxi,
            start_time=start_time,
            finish_time=finish_time,
            distance=distance,
            duration=duration_minutes,
            start_finish_lat_lon=start_finish_lat_lon,
            rating = rating_result
        )
        
        
        

        return JsonResponse({
            "message": "Trip completed and classified."
            
        })

    except Exception as e:
        print(traceback.format_exc())
            
        
        return JsonResponse({"error": str(e)}, status=500)




# views.py

from django.db.models import Count, Avg, Sum, Q

from .models import Driver, Taxi, Anomaly, DailyAnomaly, WeeklyAnomaly, Trip


def general_monitor(request):
    from django.utils.timezone import now

    # Time frames
    today = now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # Apply filters if provided
    driver_filter = request.GET.get('driver')
    taxi_filter = request.GET.get('taxi')
    anomaly_type_filter = request.GET.get('anomaly_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base querysets
    drivers = Driver.objects.all()
    taxis = Taxi.objects.all()
    today_trips = Trip.objects.filter(start_time__date=today).order_by('-start_time')
    weekly_trips = Trip.objects.filter(start_time__date__range=[week_start, week_end]).order_by('-start_time')
    today_anomalies = DailyAnomaly.objects.filter(timestamp__date=today).order_by('-timestamp')
    weekly_anomalies = WeeklyAnomaly.objects.filter(timestamp__date__range=[week_start, week_end]).order_by('-timestamp')
    
    
    one_month_ago = now() - timedelta(days=30)

    # Query the data
    month_radar_anomaly_qs = (
        Anomaly.objects
        .filter(timestamp__range=(one_month_ago, now()))
        .values('type')
        .annotate(count=Count('type'))
        .order_by('-count')
    )

    # Separate labels and data
    labels = [item['type'] for item in month_radar_anomaly_qs]
    data = [item['count'] for item in month_radar_anomaly_qs]

    
    
    
    # Apply custom filters if provided
    if driver_filter:
        today_trips = today_trips.filter(driver__id=driver_filter)
        weekly_trips = weekly_trips.filter(driver__id=driver_filter)
        today_anomalies = today_anomalies.filter(driver__id=driver_filter)
        weekly_anomalies = weekly_anomalies.filter(driver__id=driver_filter)
    
    if taxi_filter:
        today_trips = today_trips.filter(taxi__id=taxi_filter)
        weekly_trips = weekly_trips.filter(taxi__id=taxi_filter)
        today_anomalies = today_anomalies.filter(taxi__id=taxi_filter)
        weekly_anomalies = weekly_anomalies.filter(taxi__id=taxi_filter)
    
    if anomaly_type_filter:
        today_anomalies = today_anomalies.filter(type=anomaly_type_filter)
        weekly_anomalies = weekly_anomalies.filter(type=anomaly_type_filter)
    
    if date_from and date_to:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            
            today_trips = Trip.objects.filter(start_time__date__range=[from_date, to_date])
            weekly_trips = today_trips  # Use the same filtered trips
            today_anomalies = DailyAnomaly.objects.filter(timestamp__date__range=[from_date, to_date])
            weekly_anomalies = WeeklyAnomaly.objects.filter(timestamp__date__range=[from_date, to_date])
            
            if driver_filter:
                today_trips = today_trips.filter(driver__id=driver_filter)
                weekly_trips = weekly_trips.filter(driver__id=driver_filter)
                today_anomalies = today_anomalies.filter(driver__id=driver_filter)
                weekly_anomalies = weekly_anomalies.filter(driver__id=driver_filter)
            
            if taxi_filter:
                today_trips = today_trips.filter(taxi__id=taxi_filter)
                weekly_trips = weekly_trips.filter(taxi__id=taxi_filter)
                today_anomalies = today_anomalies.filter(taxi__id=taxi_filter)
                weekly_anomalies = weekly_anomalies.filter(taxi__id=taxi_filter)
                
            if anomaly_type_filter:
                today_anomalies = today_anomalies.filter(type=anomaly_type_filter)
                weekly_anomalies = weekly_anomalies.filter(type=anomaly_type_filter)
                
        except ValueError:
            pass
    
    taxis_on_trip = taxis.filter(on_trip_status="on trip")
    taxis_not_on_trip = taxis.filter(on_trip_status="not on ride")
    
    # Aggregate statistics
    total_drivers = drivers.count()
    total_taxis = taxis.count()
    active_taxis = taxis.filter(is_active=True).count()
    taxis_on_trip_count = taxis_on_trip.count()
    
    today_trip_count = today_trips.count()
    today_trip_distance = today_trips.aggregate(Sum('distance'))['distance__sum'] or 0
    today_trip_duration = today_trips.aggregate(Sum('duration'))['duration__sum'] or 0
    
    weekly_trip_count = weekly_trips.count()
    weekly_trip_distance = weekly_trips.aggregate(Sum('distance'))['distance__sum'] or 0
    weekly_trip_duration = weekly_trips.aggregate(Sum('duration'))['duration__sum'] or 0
    
    today_anomaly_count = today_anomalies.count()
    weekly_anomaly_count = weekly_anomalies.count()
    
    # Anomaly breakdown by type
    anomaly_types = DailyAnomaly.objects.values('type').annotate(count=Count('id')).order_by('-count')
    
    # Driver performance ranking
    driver_performance = []
    for driver in drivers:
        driver_trips = Trip.objects.filter(driver=driver)
        trip_count = driver_trips.count()
        avg_rating = driver_trips.aggregate(Avg('rating'))['rating__avg'] or 0
        anomaly_count = Anomaly.objects.filter(driver=driver).count()
        
        driver_performance.append({
            'driver': driver,
            'trip_count': trip_count,
            'avg_rating': avg_rating,
            'anomaly_count': anomaly_count,
            'score': (avg_rating * 20) - anomaly_count  # Simple scoring formula
        })
    
    driver_performance.sort(key=lambda x: x['score'], reverse=True)
    
    # Get all anomaly types for filter dropdown
    all_anomaly_types = set(DailyAnomaly.objects.values_list('type', flat=True).distinct())
    all_anomaly_types.update(WeeklyAnomaly.objects.values_list('type', flat=True).distinct())
    
    context = {
        'anomaly_labels': labels,
        'anomaly_data': data,
        'drivers': drivers,
        'taxis': taxis,
        'today_trips': today_trips,
        'weekly_trips': weekly_trips,
        'today_anomalies': today_anomalies,
        'weekly_anomalies': weekly_anomalies,
        'taxis_on_trip': taxis_on_trip,
        'taxis_not_on_trip': taxis_not_on_trip,
        
        # Statistics
        'total_drivers': total_drivers,
        'total_taxis': total_taxis,
        'active_taxis': active_taxis,
        'taxis_on_trip_count': taxis_on_trip_count,
        'today_trip_count': today_trip_count,
        'today_trip_distance': today_trip_distance,
        'today_trip_duration': today_trip_duration,
        'weekly_trip_count': weekly_trip_count,
        'weekly_trip_distance': weekly_trip_distance,
        'weekly_trip_duration': weekly_trip_duration,
        'today_anomaly_count': today_anomaly_count,
        'weekly_anomaly_count': weekly_anomaly_count,
        'anomaly_types': anomaly_types,
        'driver_performance': driver_performance,
        
        # For filters
        'all_anomaly_types': all_anomaly_types,
        'selected_driver': driver_filter,
        'selected_taxi': taxi_filter,
        'selected_anomaly_type': anomaly_type_filter,
        'selected_date_from': date_from,
        'selected_date_to': date_to,
    }
    
    return render(request, 'tracking/general_monitor.html', context)




## all the views for LLM reports


def get_weekly_metrics(driver):
    from django.utils.timezone import now

    week_ago = now() - timedelta(days=7)
    weekly_trips = Trip.objects.filter(driver=driver, start_time__gte=week_ago)
    weekly_anomalies = Anomaly.objects.filter(driver=driver, timestamp__gte=week_ago)

    
    active_days = weekly_trips.values('start_time__date').distinct().count()  # Unique days active
    

    return {
        "total_trips": weekly_trips.count(),
        "total_distance": float(weekly_trips.aggregate(Sum('distance'))['distance__sum'] or 0),
        "avg_rating": float(weekly_trips.filter(rating__gt=0).aggregate(Avg('rating'))['rating__avg'] or 0),
        "active_days": active_days,
        "week_ago": week_ago,
        "anomaly_breakdown": list(
            weekly_anomalies.values('type')
                            .annotate(count=Count('id'))
                            .order_by('-count')
        ),
    }

def summarize_driver(request, username):
    

    driver = Driver.objects.filter(user__username__iexact=username).first()
    if not driver:
        return JsonResponse({'error': 'Driver not found.'}, status=404)

    data = get_weekly_metrics(driver)
    
    # Build a detailed, clear prompt
    prompt = (
        f"You are a smart assistant generating a weekly performance summary for a taxi driver based on their operational logs. "
        f"Please provide a concise, insightful summary highlighting performance, safety, and activity level. "
        f"Include these points: total number of trips, total distance traveled, average passenger rating, number of active days (if available) and an overview of driving anomalies (types and frequency). "
        f"Also mention any unusual patterns, like low ratings or repeated short trips. Keep it factual but friendly. \n\n"
        f"Please do not add your own thoughts or assumptions. \n\n"
        f"Start by their name , from which data to which date, do not use stars on points, then the report try to make it insightful: "
        
        f"Driver Name: {driver.user.username}\n"
        f"License Number: {driver.license_number}\n"
        f"Phone: {driver.phone_number}\n"
        
        f"Weekly Driver Report:\n"
        f"- Date: {data['week_ago'].strftime('%Y-%m-%d')}\n"
        f"- Total Trips: {data['total_trips']}\n"
        f"- Total Distance: {data['total_distance']} km\n"
        f"- Average Rating: {data['avg_rating']:.2f} ★\n"
        f"- Active Days: {data['active_days']} days\n"
        
        f"- Total Anomalies: {len(data['anomaly_breakdown'])}\n"
        f"- Anomalies Breakdown:\n"
    )

    for anomaly in data['anomaly_breakdown']:
        prompt += f"  • {anomaly['type'].replace('_', ' ').title()}: {anomaly['count']} instances\n"

    prompt += (
        f"\nSummarize this driver's weekly activity in 7-10 clear, human-friendly sentences, highlighting any notable trends."
    )
    
    # Call the LLM
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
    response = model.generate_content(prompt)
    summary_text = response.text
    return JsonResponse({'summary': summary_text})








def trip_summary(request):
    
    tripName = request.GET.get("trip_name")
    # tripName="Zhambyl Street, Almaty to Tole Bi Street, Тастак, Almaty"

    # Get trip detail
    trip = Trip.objects.filter(trip_name=tripName).order_by('finish_time').last()
    if not trip:
        return JsonResponse({"error": "Trip not found"}, status=404)

    trip_data = {
        "trip_name": trip.trip_name or "N/A",
        "start_time": trip.start_time.strftime("%Y-%m-%d %H:%M:%S") if trip.start_time else "N/A",
        "finish_time": trip.finish_time.strftime("%Y-%m-%d %H:%M:%S") if trip.finish_time else "N/A",
        "distance": float(trip.distance) if trip.distance is not None else "N/A",
        "duration": float(trip.duration) if trip.duration is not None else "N/A",
        "rating": float(trip.rating) if trip.rating is not None else "N/A",
    }

    # Get anomalies
    anomalies = list(
        Anomaly.objects
            .filter(ride_name=tripName)
            .order_by("-timestamp")
            .values("type", "timestamp", "metrics")
    )
    for a in anomalies:
        a["timestamp"] = a["timestamp"].strftime("%Y-%m-%d %H:%M:%S")

    # Combine into prompt
    prompt =(
    f"You are a smart assistant generating a trip summary for a taxi driver. Please provide a concise, insightful summary highlighting performance, safety, and activity level. \n\n"
    f"Please do not add your own thoughts or assumptions. \n\n"
    f"When an anomaly was there, first name the anomaly then list the metrics of it and at after the metrics just one or two sentences about the assumptions on anomaly based on the metrics.\n\n"
    f"make sure to write about anomaly at the end of the summary. \n\n"
    f" - Codes you should know: # 0=Night, 1=Morning, 2=Afternoon, 3=Evening, # 0=Highway, 1=City, 2=Rural, # 0=Dry, 1=Wet, 2=Snow, 3=Ice # traffic: 0=Light, 1=Moderate, 2=Heavy\n\n"
    f"""

                Trip Summary Request

                Trip Information:
                - Name: {trip_data['trip_name']}
                - Start Time: {trip_data['start_time']}
                - Finish Time: {trip_data['finish_time']}
                - Distance: {trip_data['distance']} km
                - Duration: {trip_data['duration']} minutes
                - Rating: {trip_data['rating']}

                Detected Anomalies:
                """)
    if anomalies:
        for idx, anomaly in enumerate(anomalies, 1):
            prompt += f"\n{idx}. Type: {anomaly['type']}, Time: {anomaly['timestamp']}, Metrics: {anomaly['metrics']}"
    else:
        prompt += "\nNone"

    prompt += "\n\nSummarize this trip in 7-10 clear, human-friendly sentences, highlighting any notable trends."

    # Use Gemini model
    model = genai.GenerativeModel(model_name="models/gemini-1.5-pro-latest")
    response = model.generate_content(prompt)
    summary_text = response.text

    return JsonResponse({'summary': summary_text})



    
    


def get_ride_anomalies(request, ride_name):
    # Used daily to search today's database only.
    anomalies = DailyAnomaly.objects.filter(ride_name=ride_name).values('lat', 'long', 'type', 'timestamp','metrics')
    return JsonResponse(list(anomalies), safe=False)

