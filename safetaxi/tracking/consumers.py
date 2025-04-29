import asyncio
import json
import numpy as np
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from .models import Taxi, Anomaly, Driver, DailyAnomaly, WeeklyAnomaly, Dispatcher
from .anomaly_detector import detect_anomalies   
import traceback
from .telegram_alert_sender import send_telegram_alert


taxi_metrics_store = {} # for the frontend
from shapely.geometry import LineString, Point
from geopy.distance import geodesic

# track on/off‑route per taxi
_route_state = {}  # plate_number (True = on route)
def check_route_deviation(plate_number, current_lat, current_lon, planned_route,threshold):
        
        print(f"Checking route deviation.......")
        on_route = _route_state.get(plate_number, True)
        route_line = LineString(planned_route)

        # build geometry
        pt = Point(current_lon, current_lat)
        proj = route_line.interpolate(route_line.project(pt))
        proj_latlon = (proj.y, proj.x)
        cur_latlon = (current_lat, current_lon)

        # compute distance in meters
        dist_m = geodesic(cur_latlon, proj_latlon).meters
        print(f"distance_+_+_+_+_______ {dist_m}")

        if on_route and dist_m > threshold:
            _route_state[plate_number] = False
            return True, dist_m

        # reset state once back within threshold
        if not on_route and dist_m <= threshold:
            _route_state[plate_number] = True

        return False, dist_m


class TaxiReceiveConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        print("✅ TaxiReceiveConsumer: WebSocket client connected")
        
    async def disconnect(self, close_code):
        print(f"❌ TaxiReceiveConsumer: WebSocket disconnected with code: {close_code}")
    
    async def receive(self, text_data):
        try:
            # Handle ping messages (heartbeat)
            if text_data.strip() == "ping":
                await self.send(text_data="pong")
                return

            # Process incoming JSON data
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                print(f"⚠️ TaxiReceiveConsumer: Invalid JSON received: {text_data}")
                return

            plate_number = data.get("plate_number")
            if not plate_number:
                print("⚠️ TaxiReceiveConsumer: Missing plate number in data")
                await self.send(text_data=json.dumps({"error": "Taxi not found"}))
                return
                
            # Retrieve taxi record
            taxi = await self.get_taxi(plate_number)
            if not taxi:
                print(f"⚠️ TaxiReceiveConsumer: Taxi with plate {plate_number} not found")
                await self.send(text_data=json.dumps({"error": "Taxi not found"}))
                return

            # Update taxi location and metrics
            current_ride_name = taxi.current_ride_name
            
            #initializing the metrics for the taxi
            
            
            
            
            
            if data.get("ride_status") == "ended":
                if plate_number in _route_state and _route_state[plate_number] == False:
                    print("🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦🚦 Alert!!!!!!!!! passeger in danger")
                    taxi.passenger_in_danger = True
                    
                taxi_metrics_store[plate_number] = {
                "speed": 0,
                "acceleration": 0,
                "jerk": 0,
                "traffic_condition": None,
                "road_condition": None,
                "road_type": None,
                "time_of_day": None,
                "speed_limit": None,
                "heading": None,
                "yaw_rate": 0,
                "steering_angle": 0,
                "anomaly": None
                }
                
                print("🚦 Ride status ended: setting speed, yaw_rate, and steering_angle to 0")
                
                
                
                
                taxi.is_active = False
                
                taxi.on_trip_status = "trip just ended"
                taxi.current_metrics = taxi_metrics_store[plate_number]
                
            
                
                await sync_to_async(taxi.save)()
                
                

                await self.send(text_data=json.dumps(data))
                return  
            
            anomaly_detected, anomaly_type = detect_anomalies(data)
            if anomaly_detected:
                await self.save_anomaly(taxi, anomaly_type, data)
                data["anomaly"] = {"type": anomaly_type}
            else:
                data["anomaly"] = None
            
            
            raw = taxi.route
            
            if isinstance(raw, str):
                raw = json.loads(raw) 
                

            print(f"current lat: {data['current_lat']}")
            print(f"current lon: {data['current_lon']}")
            
            route_dev, dist = check_route_deviation(
                plate_number,
                data["current_lat"],
                data["current_lon"],
                raw,
                threshold=500
                
            )
            
            if data["speed"] > data["speed_limit"]:
                if not data["anomaly"] == None:
                    data["anomaly"]["type"].append("speeding")
                else:
                    data["anomaly"] = {"type": "speeding"}
                    
                print("🛑🛑🛑🛑🛑 Speeding")
                await self.save_anomaly(taxi, "speeding", data)

                    

                
            
            
            if route_dev:
                if not data["anomaly"] == None:
                    
                    data["anomaly"]["type"].append("route_deviation")
                else:
                    data["anomaly"] = {"type": "route_deviation"}
                
                print("🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑🛑 Deviation")
                
                await self.save_anomaly(taxi, "route_deviation", data)
                

            taxi_metrics_store[plate_number] = {
                "speed": data["speed"],
                "acceleration": data["acceleration"],
                "jerk": data["jerk"],
                "traffic_condition": data["traffic_condition"],
                "road_condition": data["road_condition"],
                "road_type": data["road_type"],
                "time_of_day": data["time_of_day"],
                "speed_limit": data["speed_limit"],
                "heading": data["heading"],
                "yaw_rate": data["yaw_rate"],
                "steering_angle": data["steering_angle"],
                "anomaly": data.get("anomaly", None),
                "Route_deviation": route_dev,
                "route_deviation_distance": dist,
                
            }
            
            
            
            taxi.current_lat = data.get("current_lat")
            taxi.current_lon = data.get("current_lon")
            taxi.heading = data.get("heading")
            taxi.current_metrics = taxi_metrics_store[plate_number]
            # (Assume other metrics are processed similarly)
            # print("------------------------------------------")
            # print(data)
            # print("------------------------------------------")
            await sync_to_async(taxi.save)()

            

            await self.send(text_data=json.dumps(data))
            
        except Exception as e:
            print(f"TaxiReceiveConsumer: Error processing data: {e}")
            traceback.print_exc()
            try:
                await self.send(text_data=json.dumps({"error": str(e)}))
            except Exception:
                pass



    
    
    @sync_to_async
    def get_taxi(self, plate_number):
        return Taxi.objects.filter(plate_number=plate_number).first()

    @sync_to_async
    def save_anomaly(self, taxi, anomaly_type, metrics):
        """Save each detected anomaly type as a separate record in the DB and notify driver."""
        driver = Driver.objects.filter(assigned_taxi=taxi).first()
        passenger=taxi.current_passenger

        dispatcher = Dispatcher.objects.first()
        ride_name = taxi.current_ride_name
        taxi_lat = taxi.current_lat
        taxi_lon = taxi.current_lon
        
        print(f"------saving the anomaly and ride_name---------:{ride_name}")
        
        if driver:
            # Split multi-anomalies and save them individually
            types = [t.strip() for t in anomaly_type.split(",")]
            for single_type in types:
                common_data = {
                    "metrics": metrics,
                    "driver": driver,
                    "taxi": taxi,
                    "type": single_type,
                    "ride_name": ride_name,
                    "lat": taxi_lat,
                    "long": taxi_lon,
                }
                
                Anomaly.objects.create(**common_data)

                DailyAnomaly.objects.create(**common_data)

                WeeklyAnomaly.objects.create(**common_data)
                
                passenger_message = f"🚨 Safety Notice for Your Ride ({ride_name}) 🚕\n\n" \
                    f"We detected a driving irregularity:\n" \
                    f"• Type: {single_type}\n" \
                    f"• Location: Lat: {taxi_lat}, Lon: {taxi_lon}\n\n" \
                    f"Our team is actively monitoring the situation to ensure your safety. " \
                    f"If you feel uncomfortable, please contact support or end the ride when safe."

                dispatcher_message = f"📡 Dispatcher Alert: Anomaly in Ride {ride_name}\n\n" \
                     f"• Driver: {driver.user.username}\n" \
                     f"• Taxi Plate: {taxi.plate_number}\n" \
                     f"• Anomaly Type: {single_type}\n" \
                     f"• Coordinates: Lat {taxi_lat}, Lon {taxi_lon}\n\n" \
                     f"Metrics: {metrics}\n\n" \
                     f"🚧 Immediate review is recommended."

                
                message = f"⚠️ Anomaly detected in your ride ({ride_name}):\n\n" \
                          f"Type: {single_type}\n" \
                          f"Location: Lat: {taxi_lat}, Lon: {taxi_lon}\n" \
                          f"Please drive carefully!\n\n" \
                          f"Details: {metrics}"
                
                send_telegram_alert(dispatcher.telegram_chat_id, dispatcher_message)
                send_telegram_alert(driver.telegram_chat_id, message)

                send_telegram_alert(passenger.telegram_chat_id, passenger_message)
        
            print(f"TaxiReceiveConsumer: Anomaly saved: {anomaly_type}")       


import asyncio
import json
import traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Taxi

class TaxiUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.is_connected = True
        # Start periodic update task
        self.update_task = asyncio.create_task(self.send_taxi_updates())
        print("✅ TaxiUpdateConsumer: WebSocket client connected")

    async def disconnect(self, close_code):
        self.is_connected = False
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
        print(f"❌ TaxiUpdateConsumer: WebSocket disconnected with code: {close_code}")

    async def send_taxi_updates(self):
        try:
            while self.is_connected:
                try:
                    taxi_data = await self.get_taxi_data()
                    await self.send(text_data=json.dumps(taxi_data))
                except Exception as e:
                    print(f"TaxiUpdateConsumer: Error sending taxi updates: {e}")
                    traceback.print_exc()
                await asyncio.sleep(1)  # Adjust the update interval as needed
        except asyncio.CancelledError:
            pass

    @sync_to_async
    def get_anomaly_stats(self, taxi):
        """Fetch daily, monthly, and yearly anomaly counts grouped by type."""
        from django.utils.timezone import now
        from django.db.models import Count
        today = now().date()

        # Count anomalies by type for different time ranges
        anomalies = Anomaly.objects.filter(taxi=taxi).values("type")
        dailyanomaly = DailyAnomaly.objects.filter(taxi=taxi).values("type")


        daily = dailyanomaly.annotate(count=Count("id"))
        monthly = anomalies.filter(timestamp__month=today.month, timestamp__year=today.year).annotate(count=Count("id"))
        yearly = anomalies.filter(timestamp__year=today.year).annotate(count=Count("id"))

        def format_stats(queryset):
            return {a["type"]: a["count"] for a in queryset}

        return {
            "daily": format_stats(daily),
            "monthly": format_stats(monthly),
            "yearly": format_stats(yearly),
        }

    async def get_taxi_data(self):
        """Fetch all active taxis with anomaly statistics asynchronously."""
        
        # Fetch taxis from the database
        taxis = await sync_to_async(lambda: list(Taxi.objects.select_related("driver__user").all()))()

        taxi_data_list = []
        for taxi in taxis:
            # Fetch anomaly stats
            anomalies = await self.get_anomaly_stats(taxi)

            # Merge in-memory taxi metrics with anomaly stats
            taxi_data_list.append({
                "plate_number": taxi.plate_number,
                "current_ride_name": taxi.current_ride_name,
                "current_lat": taxi.current_lat,
                "current_lon": taxi.current_lon,
                "driver_name": taxi.driver.user.username if taxi.driver else "Unknown",
                "route": json.loads(taxi.route) if isinstance(taxi.route, str) else taxi.route,
                "anomalies": anomalies,  # Add anomalies to the data
                "metrics": taxi_metrics_store.get(taxi.plate_number, {}),  # Retrieve the relevant metrics for all taxies
                "current_status": taxi.is_active,
                "on_trip_status": taxi.on_trip_status,
                "passenger_in_danger": taxi.passenger_in_danger,
                "heading": taxi.heading,
            })

        return taxi_data_list
