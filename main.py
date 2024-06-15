import asyncio
import base64
import json
import os
import time
import threading
import uuid

import cv2
import numpy as np
import tinytuya as ty
import websockets as ws

from flask import Flask, request
from ultralytics import YOLO

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

# in second
TIME_LIMIT_NO_HUMAN_DETECTED = 5

object_detection_model = YOLO("yolov8n.pt")

saved_camera = {"ws://192.168.100.4:7711" : {"view" : None, "human_detected" : False}};
saved_plug = {"ebf19ba30ea9d231c5ega7": {"address": "192.168.100.11", "key" : "]apQZ4a3{]k;X+VW", "device" : None, "status": "error"}}
room = {"5786854" : {"name" : "Kamar", "camera" : ["ws://192.168.100.4:7711"], "plug" : ["ebf19ba30ea9d231c5ega7"], "automatic" : False, "last_detect_human" : 0}}

@app.route("/home")
def home():
    response = {"plug" : {"total": 0, "connected" : 0, "active": 0}, "camera" : {"total": len(saved_camera), "connected" : 0}}
    
    for address, camera in saved_camera.items():
        if camera["view"] is not None:
            response["camera"]["connected"] += 1
    
    return json.dumps(response)



@app.route("/roomlist")
def room_list():
    response = {"room": []}
    for room_id, room_data in room.items():
        room_response = {"id": room_id, "name": room_data["name"], "automatic" : room_data["automatic"], "status": "Some on" if check_any_plug_on(room_data["plug"]) else "all off", "human_detected" : False}
        for camera in room_data["camera"]:
            if camera in saved_camera and saved_camera[camera]["human_detected"]:
                room_response["human_detected"] = True
        
        response["room"].append(room_response)
    
    return json.dumps(response)



@app.route("/addnewroom", methods=["POST"])
def add_new_room():
    post = request.get_json()
    name = post["name"]
    room[str(uuid.uuid4())] ={"name" : name, "camera" : [], "plug" : [], "automatic" : False, "last_detect_human" : 0}
    return ""



@app.route("/deleteroom", methods=["POST"])
def delete_room():
    post = request.get_json()
    id = post["id"]
    
    if id in room:
        room.pop(id, {})
    
    return ""

@app.route("/turnroom", methods=["POST"])
def turn_room():
    post = request.get_json()
    room_id = post["room_id"]
    turn_on = post["turn_on"]
    
    set_on_off_room(room_id, turn_on)
    return ""

@app.route("/turnplug", methods=["POST"])
def turn_plug():
    post = request.get_json()
    plug_id = post["plug_id"]
    turn_on = post["turn_on"]
    set_on_off_plug(plug_id, turn_on)
    return ""
    
    
        
@app.route("/getroominfo", methods=["POST"])
def get_room_info():
    post = request.get_json()
    id = post["id"]
    
    room_data = room[id]
    camera_data = []
    for camera_address in room_data["camera"]:
        camera_data.append({
            "name": camera_address,
            "info": "Human detected" if saved_camera[camera_address]["human_detected"] else "No human detected"
        })
        
    plug_data = []
    for plug_id in room_data["plug"]:
        plug = saved_plug[plug_id]
        plug_data.append({
            "name": plug_id,
            "info": "Status On" if saved_plug[plug_id]["status"] == "on" else "Status Off"
        })
    
    room_response = {"name": room_data["name"], "camera": camera_data, "plug": plug_data}
    
    return json.dumps(room_response)


@app.route("/addnewcamera", methods=["POST"])
def add_new_camera():
    post = request.get_json()
    room_id = post["room_id"]
    camera_address = post["camera_address"]
    
    if camera_address not in saved_camera:
        saved_camera[camera_address] = {"view" : None, "human_detected" : False}
    
    room[room_id]["camera"].append(camera_address)

    return ""
    
    
    
@app.route("/setautomatic", methods=["POST"])
def set_autpmatic():
    post = request.get_json()
    room_id = post["room_id"]
    automatic = post["automatic"]
    
    room[room_id]["automatic"] = automatic
    
    return ""
    


async def request_campure_capture(address: str):
    message = ""
    async with ws.connect(address) as websocket:
        await websocket.send("REQUEST_IMAGE")
        message = websocket.recv()
        
    return await message

def process_camera_capture():
    loop = asyncio.new_event_loop()

    while True:
        for address, camera in saved_camera.items():
            try:
                message = loop.run_until_complete(request_campure_capture(address))
                message = base64.b64decode(message)
            
                message_array = np.fromstring(message, np.uint8)
                image_nparray = cv2.imdecode(message_array, cv2.IMREAD_COLOR)
                
                results  = object_detection_model(image_nparray);
                human_detected = False
                for result in results:
                    boxes = result.boxes  # Boxes object for bounding box outputs
                    for i in range(boxes.shape[0]):
                        if (boxes.cls[i] == 0):
                            human_detected = True
                            cv2.rectangle(image_nparray, (int(boxes.xyxy[i][0]), int(boxes.xyxy[i][1])), (int(boxes.xyxy[i][2]), int(boxes.xyxy[i][3])), (255, 255, 0), thickness=2)
                
                camera["view"] = image_nparray
                camera["human_detected"] = human_detected
                    
            except Exception as e:
                camera["view"] = None
                camera["human_detected"] = False

def process_plug_status():
    while True:
        for deviceId, plug in saved_plug.items():
            if plug["device"] is None:
                plug["device"] = ty.OutletDevice(deviceId, plug["address"], plug["key"])
                plug["device"].set_socketPersistent(True)
                plug["device"].set_version(3.4)
                
            status = plug["device"].status()
            try:
                plug["status"] = "on" if status["dps"]["1"] else "off"
            except:
                plug["status"] = "error"
            
        time.sleep(0.25)

def set_on_off_room(room_id : str, on: bool):
    plug_ids = room[room_id]["plug"]
    for plug_id in plug_ids:
        plug = saved_plug[plug_id]
        try:
            if on and plug["status"] == "off":
                plug["device"].turn_on()
            elif plug["status"] == "on":
                plug["device"].turn_off()
        except Exception:
            pass
        
def set_on_off_plug(plug_id : str, on : bool):
    plug = saved_plug[plug_id]
    try:
        if on and plug["status"] == "off":
            plug["device"].turn_on()
        elif plug["status"] == "on":
            plug["device"].turn_off()
    except Exception:
        pass
        
def check_any_camera_detect_human(camera_ids : list):
    for camera_id in camera_ids:
        camera = saved_camera[camera_id]
        if camera["human_detected"]:
            return True
        
    return False


def check_any_plug_on(plug_ids : list):
    for plug_id in plug_ids:
        plug = saved_plug[plug_id]
        if plug["status"] == "on":
            return True
        
    return False

def process_room():
    while True:
        for room_id, room_data in room.items():
            if check_any_camera_detect_human(room_data["camera"]):
                room_data["last_detect_human"] = time.time()
            
            if room_data["automatic"] and time.time() - room_data["last_detect_human"] >= TIME_LIMIT_NO_HUMAN_DETECTED:
                set_on_off_room(room_id, False)
            
        time.sleep(0.25)
    

        
if __name__ == "__main__":
    
    process_camera_capture_thread = threading.Thread(target=process_camera_capture)
    process_camera_capture_thread.start()
    
    process_plug_thread = threading.Thread(target=process_plug_status)
    process_plug_thread.start()
    
    process_room_thread = threading.Thread(target=process_room)
    process_room_thread.start()
    
    app.run(host='0.0.0.0', port=8898)
