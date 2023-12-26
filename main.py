from mongoengine import connect
from classes import *
import json
import os
import asyncio
from PIL import Image
from io import BytesIO
from moviepy.editor import VideoFileClip
import numpy as np
from datetime import datetime
import cv2 as cv


from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
import paho.mqtt.client as mqtt
from pymongo import MongoClient
from bson import ObjectId


app = FastAPI()
connect(db="DEE", host="localhost", port=27017)
client = MongoClient('127.0.0.1:27017')
db = client['DEE']

'''
Esta parte del codigo es para uso del la aplicación movil en flutter.
Aun no sabemos cómo hacer que flutter se connecte con  MQTT. Como alternativa temporal, 
hacemos que flutter se comunique con el autopilot service a través de la APIREST, que si que 
puede comunicarse via MQTT.
En el momento en que se solucione el problema de la conexión de flutter a MQTT esta parte del código
se elmimiará'''

################################################################33

client = mqtt.Client(client_id="fastApi", transport='websockets')
is_connected = False


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {str(rc)}")
    client.subscribe("autopilotService/WebApp/telemetryInfo", 2)
    # client.subscribe("+/fastApi/#", 2)


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global is_connected
    # print(f"{msg.topic} {str(msg.payload)}")
    if msg.topic == "autopilotService/WebApp/telemetryInfo":
        is_connected = True


# MQTT Callbacks
client.on_connect = on_connect
client.on_message = on_message

@app.get("/connect")
async def connect_to_broker():
    global is_connected
    try:
        client.connect("localhost", 8000, 10)
        client.loop_start()
        client.publish("WebApp/autopilotService/connect")
        await asyncio.sleep(2)
        if not is_connected:
            raise HTTPException(status_code=503, detail="Connection failed. No telemetryInfo message received.")
        return {"message": "Successfully connected to the broker."}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/disconnect")
async def disconnect_from_broker():
    global is_connected
    try:
        client.publish("WebApp/autopilotService/disconnect")
        client.loop_stop()
        client.disconnect()
        is_connected = False
        return {"message": "Successfully disconnected from the broker."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/connection_status")
async def get_connection_status():
    global is_connected
    return {"is_connected": is_connected}

@app.post("/executeFlightPlan")
async def execute_flight_plan(plan: List[WaypointMQTT]):
    # Convert the FlightPlan to a JSON string
    plan_json = json.dumps(jsonable_encoder(plan))

    # Publish the plan to the MQTT broker
    client.publish("WebApp/autopilotService/executeFlightPlan", plan_json)
    return {"message": "Flight plan published"}
# End MQTT Callbacks

@app.get("/get_results_flight_flutter/{flight_id}")
async def get_results_flight_flutter(flight_id: str):
    client.publish("WebApp/cameraService/getResultFlightFlutter", flight_id)
    return {"message": "Trying to obtain images and pictures"}

###### Hasta aqui el código específico para la aplicación movil en flutter #############

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content=jsonable_encoder(
            ErrorResponse(
                success=False,
                message="Validation error",
                errors=exc.errors(),
            )
        ),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ErrorResponse(success=False, message=exc.detail)
        ),
    )



@app.get("/")
def home():
    return RedirectResponse(url="/docs")


@app.get("/get_all_flights")
def get_all_flights():
    flights = Flights.objects()
    flights_data = []

    for flight in flights:
        individual_flight = json.loads(flight.to_json())

        # Populate related documents
        individual_flight["FlightPlan"] = json.loads(flight.FlightPlan.to_json())

        # Pictures
        #pictures = []
        #for picture in individual_flight["Pictures"]:
            #picture["lat"]=individual_flight["lat"]
            #picture["lon"]=individual_flight["lon"]

            #pic = Picture.objects.get(picture)
            #pictures.append(picture())
            #pic_name = picture["namePicture"]
            #pictures.append(pic_name)
        #individual_flight["Pictures"] = pictures

        # Videos
        #videos = []
        #for video in individual_flight["Videos"]:
            #vid = Video.objects.get(nameVideo=video["nameVideo"])
            #video1 = video.to_json()
            #videos.append(json.loads(video.to_json()))
            #vid_name = video["nameVideo"]
            #videos.append(vid_name)
        #individual_flight["Videos"] = videos

        flights_data.append(individual_flight)

    return flights_data


@app.post("/add_flightplan", responses={422: {"model": ErrorResponse}})
def add_flightplan(data: FlightPlanData):
    try:
        title = data.title
        waypoints = data.waypoints
        pic_interval = data.PicInterval
        vid_interval = data.VidInterval

        num_waypoints = len(waypoints)
        num_pics = 0
        num_vids = 0
        flight_waypoints = []
        pics_waypoints = []
        vid_waypoints = []
        for w in waypoints:
            waypoint = Waypoint(lat=w.lat, lon=w.lon, height=w.height)
            flight_waypoints.append(waypoint)
            if w.takePic:
                pics_waypoints.append(waypoint)
                num_pics += 1
            if w.videoStart or w.videoStop:
                if w.videoStart:
                    num_vids += 1
                    waypoint_vid = VideoPlan(mode="moving", latStart=w.lat, lonStart=w.lon)
                if w.videoStop:
                    waypoint_vid.latEnd = w.lat
                    waypoint_vid.lonEnd = w.lon
                    vid_waypoints.append(waypoint_vid)
            if w.staticVideo:
                num_vids += 1
                static_vid = VideoPlan(mode="static", lat=w.lat, lon=w.lon, length=vid_interval)
                vid_waypoints.append(static_vid)

        new_flight_plan = FlightPlan(Title=title,
                                     NumWaypoints=num_waypoints,
                                     FlightWaypoints=flight_waypoints,
                                     NumPics=num_pics,
                                     PicsWaypoints=pics_waypoints,
                                     NumVids=num_vids,
                                     VidWaypoints=vid_waypoints,
                                     PicInterval=pic_interval,
                                     VidTimeStatic=vid_interval)
        new_flight_plan.save()
        id_flightplan = str(new_flight_plan.id)
        return {"success": True, "message": "Waypoints Saved", "id": id_flightplan}

    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.post("/add_flight", responses={422: {"model": ErrorResponse}})
def add_flight(data: FlightData):
    try:
        startTime = data.startTime
        startTimeNew = startTime[:-3]
        pictures = []
        i=0
        while i < len(data.Pictures):
            pictures.append({
                "waypoint": data.Pictures[i].waypoint,
                "namePicture": data.Pictures[i].namePicture,
                "lat": data.Pictures[i].lat,
                "lon": data.Pictures[i].lon})
            i=i+1
        videos = []
        i=0
        while i < len(data.Videos):
            videos.append({
                "startWaypoint": data.Videos[i].startWaypoint,
                "endWaypoint": data.Videos[i].endWaypoint,
                "nameVideo": data.Videos[i].nameVideo,
                "latStart": data.Videos[i].latStart,
                "lonStart": data.Videos[i].lonStart,
                "latEnd": data.Videos[i].latEnd,
                "lonEnd": data.Videos[i].lonEnd})
            i = i + 1
        new_flight = Flights(Date=datetime.strptime(data.Date, '%Y-%m-%dT%H:%M:%S'),
                             startTime=datetime.strptime(startTimeNew, '%Y-%m-%dT%H:%M:%S.%f'),
                             GeofenceActive=data.GeofenceActive,
                             FlightPlan=ObjectId(data.Flightplan),
                             NumVids=data.NumVids,
                             NumPics=data.NumPics,
                             Pictures=pictures,
                             Videos=videos)
        new_flight.save()
        id_flight = str(new_flight.id)


        """
        return {"success": True, "message": "Waypoints Saved", "id": id_flight}
        client_source = MongoClient('192.168.208.5:27017')
        db_source = client_source['DEE']
        collectionAir = db_source['flights']

        # Conectar a la base de datos de destino
        client_dest = MongoClient('127.0.0.1:27017')
        db_dest = client_dest['DEE']
        collectionGround = db_dest['flights']

        # Buscar el documento específico en la base de datos de origen
        documento = collectionAir.find_one({"_id": ObjectId(flight_id)})

        documento["FlightPlan"] = ObjectId(data.FlightPlanid)
        collectionGround.insert_one(documento)
        """

    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})
"""
@app.post("/add_flight/{flight_id}", responses={422: {"model": ErrorResponse}})
def add_flight(flight_id: str, data: UpdateFlight):
    try:
        startTime = data.startTime
        startTimeNew = startTime[:-3]
        new_flight = Flights(Date=datetime.strptime(data.Date, '%Y-%m-%dT%H:%M:%S'),
                             startTime=datetime.strptime(startTimeNew, '%Y-%m-%dT%H:%M:%S.%f'),
                            GeofenceActive=data.GeofenceActive,
                            FlightPlan=ObjectId(data.Flightplan),
                            NumVids=data.NumVids,
                            NumPics=data.NumPics,
                            Pictures=data.Pictures,
                            Videos=data.Videos)
        new_flight.save()
        id_flight = str(new_flight.id)
        return {"success": True, "message": "Waypoints Saved", "id": id_flight}
        client_source = MongoClient('192.168.208.5:27017')
        db_source = client_source['DEE']
        collectionAir = db_source['flights']

        # Conectar a la base de datos de destino
        client_dest = MongoClient('127.0.0.1:27017')
        db_dest = client_dest['DEE']
        collectionGround = db_dest['flights']

        # Buscar el documento específico en la base de datos de origen
        documento = collectionAir.find_one({"_id": ObjectId(flight_id)})

        documento["FlightPlan"] = ObjectId(data.FlightPlanid)
        collectionGround.insert_one(documento)

    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})
"""
"""       
@app.get("/get_flightplan_id/{flight_id}")
def get_flightplan_id(flight_id: str):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flights']

        flight = collection.find_one({"_id": ObjectId(flight_id)})
        flightplan_id = str(flight["FlightPlan"])
        #client.close()
        return ({"FlightPlan id": flightplan_id})
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})
"""
@app.get("/get_flight_plan/{flightplan_id}")
def get_flight_plan(flightplan_id: str):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flightPlan']

        flightplan = collection.find_one({"_id": ObjectId(flightplan_id)})
        flightplan["_id"] = str(flightplan["_id"])
        flightplan["DateAdded"] = flightplan["DateAdded"].isoformat()
        client.close()
        return JSONResponse(content=flightplan, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.get("/get_flight_plan_id/{flightplan_title}")
def get_flight_plan_id(flightplan_title: str):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flightPlan']

        flightplan = collection.find_one({"Title": flightplan_title})
        if flightplan is None:
            return JSONResponse(content=flightplan, status_code=404)
            #raise HTTPException(status_code=404, detail={"FlightPlan no encontrado"})
        else:
            #flightplan["_id"] = str(flightplan["_id"])
            #flightplan["DateAdded"] = flightplan["DateAdded"].isoformat()
            client.close()
            return {"success": True, "message": "Flight Plan found", "id": str(flightplan["_id"])}
            #return JSONResponse(content=str(flightplan["_id"]), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

"""
@app.get("/get_pic_interval/{flightplan_id}")
def get_pic_interval(flightplan_id: str):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flightPlan']

        flightplan = collection.find_one({"_id": ObjectId(flightplan_id)})
        pic_Interval = flightplan["PicInterval"]
        #client.close()
        return {"Pic interval": pic_Interval}
        #return JSONResponse(content=flightplan, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.get("/get_vid_interval/{flightplan_id}")
def get_vid_interval(flightplan_id: str):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flightPlan']

        flightplan = collection.find_one({"_id": ObjectId(flightplan_id)})
        vid_Interval = flightplan["VidTimeStatic"]
        #client.close()
        return {"Vid interval": vid_Interval}
        #return JSONResponse(content=flightplan, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.put("/add_video", response_model=SuccessResponse, responses={422: {"model": ErrorResponse}})
async def add_video(data: NewVideo):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flights']

        flight_id = data.idFlight
        name_video = data.nameVideo
        startVideo = data.startVideo
        endVideo = data.endVideo
        latStartVideo = data.latStart
        lonStartVideo = data.lonStart
        latEndVideo = data.latEnd
        lonEndVideo = data.lonEnd

        flightplan = collection.find_one({"_id": ObjectId(flight_id)})

        if flightplan:
            #picture_data = Picture(NamePicture=name_picture)
            #picture_data_dict = picture_data
            flightplan["Videos"].append({
                "startWaypoint": startVideo,
                "endWaypoint": endVideo,
                "nameVideo": name_video,
                "latStart": latStartVideo,
                "lonStart": lonStartVideo,
                "latEnd": latEndVideo,
                "lonEnd": lonEndVideo})
            collection.replace_one({"_id": ObjectId(flightplan["_id"])}, flightplan)
            return {"success": True, "message": "Video saved"}
        #client.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.put("/add_picture", response_model=SuccessResponse, responses={422: {"model": ErrorResponse}})
async def add_picture(data: NewPicture):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flights']

        flight_id = data.idFlight
        name_picture = data.namePicture
        lat_image = data.latImage
        lon_image = data.lonImage

        flightplan = collection.find_one({"_id": ObjectId(flight_id)})

        if flightplan:
            #picture_data = Picture(NamePicture=name_picture)
            #picture_data_dict = picture_data
            flightplan["Pictures"].append({
                "waypoint": data.waypoint,
                "namePicture": name_picture,
                "lat": lat_image,
                "lon": lon_image})
            collection.replace_one({"_id": ObjectId(flightplan["_id"])}, flightplan)
            return {"success": True, "message": "Picture saved"}
        #client.close()
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.get("/get_results_flight/{flight_id}")
def get_results_flight(flight_id: str):
    try:
        client = MongoClient('127.0.0.1:27017')
        db = client['DEE']
        collection = db['flights']

        flight = collection.find_one({"_id": ObjectId(flight_id)})
        videos = flight["Videos"]
        pictures = flight["Pictures"]

        #client.close()
        return ({"Videos": videos, "Pictures": pictures})
    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})
"""
@app.post("/save_picture/{picture_name}")
async def save_picture(picture_name: str, request: Request):
    try:
        #client = MongoClient('127.0.0.1:27017')
        #db = client['DEE']
        #collection = db['flights']

        data_bytes = await request.body()


        #with open("media/pictures/" + picture_name, "wb") as f:
        #    f.write(body)


        #with open("media/pictures/" + picture_name, "wb") as buffer:
        #    buffer.write(file.read())

        #datos = request.body()

        actual_dir = os.path.dirname(os.path.abspath(__file__))
        img_route = os.path.join(actual_dir, "media", "pictures", picture_name)
        #img_route = "E:\TFG\Alejandro Final\APIRESTDEE/media/pictures/" + picture_name
        nparr = np.frombuffer(data_bytes, np.uint8)
        image = cv.imdecode(nparr, cv.IMREAD_COLOR)
        try:
            cv.imwrite(img_route, image)
        except Exception as e:
            print(f"Error al guardar la imagen: {e}")
        cv.waitKey(0)
        #print('Imagen recibida y guardada en:', img_route)

    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})

@app.post("/save_video/{video_name}")
async def save_video(video_name: str, request: Request):
    try:
        data_bytes = await request.body()

        actual_dir = os.path.dirname(os.path.abspath(__file__))
        vid_route = os.path.join(actual_dir, "media", "videos", video_name)
        #vid_route = "E:\TFG\Alejandro Final\APIRESTDEE/media/videos/" + video_name

        try:
            with open(vid_route, 'wb') as file:
                file.write(data_bytes)
        except Exception as e:
            print(f"Error al guardar el video: {e}")
        cv.waitKey(0)
        #print('Video recibido y guardado en:', vid_route)

    except Exception as e:
        raise HTTPException(status_code=400, detail={str(e)})


@app.get("/get_all_flightPlans")
def get_all_flightPlans():
    waypoints = json.loads(FlightPlan.objects().to_json())
    return {"Waypoints": waypoints}


# Serve media files
directory_path = os.path.join(os.path.dirname(__file__), "media")
app.mount("/media", StaticFiles(directory=directory_path), name="media")

@app.get("/media/pictures/{file_name}")
async def get_picture(file_name: str):
    return FileResponse(os.path.join("media", "pictures", file_name))

@app.get("/media/videos/{file_name}")
async def get_video(file_name: str):
    return FileResponse(os.path.join("media", "videos", file_name))

@app.get("/thumbnail/{file_name}")
async def get_video_thumbnail(file_name: str):
    # Load the video
    video = VideoFileClip(os.path.join("media", "videos", file_name))

    thumbnail = video.get_frame(0)
    img = Image.fromarray(np.uint8(thumbnail))

    image_io = BytesIO()
    img.save(image_io, format='JPEG')
    image_io.seek(0)

    return StreamingResponse(image_io, media_type="image/jpeg")




