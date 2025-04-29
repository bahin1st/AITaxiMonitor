import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir))
sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "safetaxi.settings")
import django
django.setup()

from tracking.models import Taxi


import csv
import json
import asyncio
import websockets
import sys
import time
from datetime import datetime

from asgiref.sync import sync_to_async

# Get CSV file and plate number from arguments
if len(sys.argv) != 3:
    print("Usage: python sim.py <csv_file_path> <plate_number>")
    sys.exit(1)

CSV_FILE = sys.argv[1]
PLATE_NUMBER = sys.argv[2]



@sync_to_async
def get_taxi(plate_number):
    return Taxi.objects.filter(plate_number=plate_number).first()

WEBSOCKET_URL = "ws://127.0.0.1:8000/ws/taxi/receive/"
RECONNECT_DELAY = 5
HEARTBEAT_INTERVAL = 10
DATA_SEND_INTERVAL = 1

should_shutdown = False

async def heartbeat_sender(websocket):
    while not should_shutdown:
        try:
            await websocket.send("ping")
            print("❤️ Heartbeat sent")
            await asyncio.sleep(HEARTBEAT_INTERVAL)
        except websockets.exceptions.ConnectionClosed:
            print("⚠️ Connection closed during heartbeat")
            break
        except Exception as e:
            print(f"❌ Error sending heartbeat: {e}")
            break

async def send_data():
    global should_shutdown
    print(f"🚀 Simulator started at {datetime.now().strftime('%H:%M:%S')}")
    
    while not should_shutdown:
        ws = None
        try:
            print(f"🔌 Connecting to WebSocket at {WEBSOCKET_URL}...")
            ws = await websockets.connect(WEBSOCKET_URL)
            print("✅ Connected to WebSocket!")
    
            heartbeat_task = asyncio.create_task(heartbeat_sender(ws))
    
            try:
                with open(CSV_FILE, "r") as file:
                    reader = csv.DictReader(file)
                    for row in reader:
                        if should_shutdown:
                            print("⛔ Shutdown requested")
                            break
    
                        try:
                            data = {
                                "plate_number": PLATE_NUMBER,
                                "current_lat": float(row["latitude"]),
                                "current_lon": float(row["longitude"]),
                                "speed": float(row["speed"]),
                                "speed_limit": float(row["speed_limit"]),
                                "acceleration": float(row["acceleration"]),
                                "heading": float(row["heading"]),
                                "yaw_rate": float(row["yaw_rate"]),
                                "steering_angle": float(row["steering_angle"]),
                                "jerk": float(row["jerk"]),
                                "road_type": int(row["road_type"]),
                                "time_of_day": int(row["time_of_day"]),
                                "traffic_condition": int(row["traffic_condition"]),
                                "road_condition": int(row["road_condition"]),
                            }
                        except ValueError as e:
                            print(f"⚠️ Error converting data: {e}")
                            continue
                        
                        
                        taxi = await get_taxi(PLATE_NUMBER)
                        if taxi and not taxi.is_active:
                            print("🛑 Taxi ride status is ended, stopping simulation.")
                            should_shutdown = True
                            break
                            
                        print(f"🚕 Sending data: Lat={data['current_lat']}, Lon={data['current_lon']}, Speed={data['speed']}")
                        data_json = json.dumps(data)
    
                        try:
                            await ws.send(data_json)
                        except websockets.exceptions.ConnectionClosed:
                            print("⚠️ Connection closed while sending data")
                            break
    
                        try:
                            response = await asyncio.wait_for(ws.recv(), timeout=5)
                            try:
                                response_data = json.loads(response)
                                if isinstance(response_data, dict):
                                    if response_data.get("error"):
                                        print(f"⚠️ Error from server: {response_data['error']}")
                                    elif response_data.get("anomaly"):
                                        print(f"🚨 ANOMALY DETECTED: {response_data['anomaly']['type']}")
                                    else:
                                        print("📩 Data acknowledged")
                            except json.JSONDecodeError:
                                if response == "pong":
                                    print("🔄 Received pong response")
                                else:
                                    print(f"📩 Received non-JSON response: {response}")
                        except asyncio.TimeoutError:
                            print("⚠️ No response from server (timeout)")
                        except websockets.exceptions.ConnectionClosed as e:
                            print(f"❌ Connection closed: {e}")
                            break
    
                        await asyncio.sleep(DATA_SEND_INTERVAL)
    
                # Once the CSV is fully processed, send an "end ride" message.
                print("✅ All data points sent, simulation complete")
                try:
                    final_message = json.dumps({
                        "plate_number": PLATE_NUMBER,
                        "ride_status": "ended"
                    })
                    await ws.send(final_message)
                    print("🚦 Ride end message sent")
                except Exception as e:
                    print(f"⚠️ Failed to send ride end message: {e}")
    
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
                try:
                    await ws.close()
                except Exception as e:
                    print(f"⚠️ Error closing WebSocket: {e}")
    
        except websockets.exceptions.ConnectionClosed as e:
            print(f"❌ Connection closed: {e}. Reconnecting in {RECONNECT_DELAY} seconds...")
        except Exception as e:
            print(f"❌ Error: {e}. Reconnecting in {RECONNECT_DELAY} seconds...")
    
        should_shutdown = True
        await asyncio.sleep(RECONNECT_DELAY)

async def main():
    global should_shutdown
    data_task = asyncio.create_task(send_data())
    
    try:
        await data_task
    except asyncio.CancelledError:
        should_shutdown = True
        print("🛑 Shutdown requested, cleaning up...")
        if not data_task.done():
            data_task.cancel()
            try:
                await data_task
            except asyncio.CancelledError:
                pass
        print("✅ Simulator shutdown complete")
    except KeyboardInterrupt:
        should_shutdown = True
        print("🛑 Keyboard interrupt received, shutting down...")
        if not data_task.done():
            data_task.cancel()
            try:
                await data_task
            except asyncio.CancelledError:
                pass
        print("✅ Simulator shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Keyboard interrupt received, exiting...")
