from flask import Flask, jsonify, request
from pymongo import MongoClient
import re
from bson.objectid import ObjectId
import random
import datetime as d
from datetime import datetime
from haversine import haversine

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
database = client['TripRegistry']

clients = database['clients']
trips = database['trips']

clients.create_index([('_id',1), ('vehicles.vehicleId', 1)]) 
trips.create_index([('clientId', 1),('status', 1)])
trips.create_index([('clientId', 1), ('vehicleId', 1)])

def is_valid_email(email):
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email) is not None

def date_format(date):
    regex = r'^\d{4}[-/\s](0[1-9]|1[0-2])[-/\s](0[1-9]|[12][0-9]|3[01])$'
    return re.match(regex, date) is not None

def is_valid_vin(vin):
    regex = r'^[A-HJ-NPR-Z0-9]{17}'
    return re.match(regex, vin) is not None

def rewrite(data, type):
    
    if type == True:
        new = {"id": str(data['_id'])}
        
        for key in data: 
            if key!="_id": 
                new[key]=data[key]
    
    else:
        if 'id' in data and data['id']:
            id = str(data['id'])
        else:
            id = str(ObjectId())  
    
        new = {"_id": id }
        for key in data:
            if key!="id":
                new[key]=data[key] 
    return new

def rewrite_time(ms):
    seconds = ms // 1000 
    time=d.timedelta(seconds=seconds)
    days = time.days
    hours, remainder = divmod(time.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    newTime=""
    if days: 
        newTime=str(days) + "d " + str(hours) + "h " + str(minutes) + "m " + str(seconds) + "s"
    elif hours:
        newTime=str(hours) + "h " + str(minutes) + "m " + str(seconds) + "s"
    elif minutes:
        newTime=str(minutes)+ "m " + str(seconds) + "s"
    elif seconds:
        newTime=str(seconds) + "s"  
    
    return newTime

def is_valid_coordinates(lat, long):
    return isinstance(lat, (float, int)) and isinstance(long, (float,int)) and -90 <= lat <= 90 and -180 <= long <= 180
    
@app.route('/clients', methods=['PUT'])
def register_client():
    data = request.get_json()
    required=['firstName', 'lastName', 'email', 'dateOfBirth']
    for field in required:
        if field not in data or not data[field] or data[field]==" ":
            return jsonify({"error":"Klaida. Trūksta duomenų."}), 400
    
    if not is_valid_email(data['email']):
        return jsonify({"error":"Klaida. Neteisingai įvestas el. paštas."}), 400
    
    if not date_format(data['dateOfBirth']):
        return jsonify({"error":"Klaida. Neteisingai įvesta gimimo data."}), 400
    
    if clients.find_one({"email": data['email']}):
            return jsonify({"error":"Klaida. El. paštas jau naudojamas kito kliento."}), 400
    
    if 'id' in data:
        if clients.find_one({"_id": data['id']}):
            return jsonify({"error":"Klaida. Klientas tokiu ID jau užregistruotas."}), 400
    
    newClient=rewrite(data, 0)
    
    while clients.find_one({"_id": newClient['_id']}):
        newClient.pop("_id", None)
        newClient=rewrite(newClient, 0)
        
    clients.insert_one(newClient)
    return jsonify({"message": "Klientas užregistruotas sėkmingai.", "id": newClient['_id']}), 201

@app.route('/clients/<string:clientId>', methods=['GET'])
def get_client(clientId):
    includeVehicles = request.args.get('includeVehicles')
    if not includeVehicles or includeVehicles=="False":
        client = clients.find_one({"_id": clientId}, {"vehicles":0})
    else:
        client = clients.find_one({"_id": clientId})
        
    if not client:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    else:
        client_1 = rewrite(client,1)
        return jsonify(client_1), 200

@app.route('/clients/<string:clientId>/vehicles', methods=['PUT'])
def register_vehicle(clientId):
    data=request.get_json()
    
    check = clients.find_one({"_id":clientId})
    if not check:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    
    required=['model', 'make', 'VIN', 'licensePlateNo', 'year']
    for field in required:
        if field not in data or not data[field] or data[field]==" ":
            return jsonify({"error":"Klaida. Trūksta duomenų."}), 400
        
    if not is_valid_vin(data['VIN']):
        return jsonify({"error":"Klaida. Neteisingai įvestas VIN numeris."}), 400
    
    vehicle_by_vin=clients.find_one({"vehicles.VIN":data['VIN']})
    vehicle_by_license=clients.find_one({"vehicles.licensePlateNo":data['licensePlateNo']})
    if 'id' in data:
        data['vehicleId']=data['id']
        data.pop('id', None)
        vehicle_by_id=clients.find_one({"vehicles.vehicleId": data['vehicleId']})
        if vehicle_by_id:
            return jsonify({"error":"Klaida. Transporto priemonė tokiu ID jau užregistruota."}), 400
    else:
        data['vehicleId']=str(ObjectId())
        while clients.find_one({"vehicles.vehicleId": data['vehicleId']}):
            data.pop('vehicleId', None)
            data['vehicleId']=str(ObjectId()) 
        
    if vehicle_by_vin:
        return jsonify({"error":"Klaida. Transporto priemonė tokiu VIN jau užregistruota."}), 400
    if vehicle_by_license:
        return jsonify({"error":"Klaida. Transporto priemonė tokiais valstybiniais numeriais jau užregistruota."}), 400
    
    if 'vehicles' not in check:
        clients.update_one({"_id": clientId}, {"$set": {"vehicles": [data]}})
    else:
        clients.update_one({"_id": clientId}, {"$push": {"vehicles": data}})
    
    return jsonify({"message":"Transporto priemonė užregistruota sėkmingai.", "id": data['vehicleId']}), 201

@app.route('/clients/<string:clientId>/vehicles', methods=['GET'])
def get_vehicles(clientId):
    check = clients.find_one({"_id":clientId})
    if not check:
            return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404  
    
    pipeline = [
        {"$match": {"_id": clientId}},
        {"$unwind" : {"path":"$vehicles"}},
        {"$project": {"_id":0, "vehicles":1}},
        {"$replaceRoot":{"newRoot": "$vehicles"}}
    ]
    vehicles = list(clients.aggregate(pipeline))
    if len(vehicles)==0:
        return '', 204
    else:
        return jsonify(vehicles), 200

@app.route('/clients/<string:clientId>/vehicles/<string:vehicleId>', methods=['GET'])
def get_vehicle(clientId, vehicleId):  
    check = clients.find_one({"_id":clientId})
    if not check:
            return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404  
        
    pipeline= [
        {"$unwind" : {"path":"$vehicles"}},
        {"$match": {"_id": clientId, "vehicles.vehicleId": vehicleId}},
        {"$project": {"_id":0, "vehicles":1}},
        {"$replaceRoot":{"newRoot": "$vehicles"}}
    ]
    vehicle = list(clients.aggregate(pipeline))
    if not vehicle:
        return jsonify({"error": "Klaida. Klientas neturi transporto priemonės tokiu ID."}), 404
    else:
        return jsonify(vehicle), 200
              
@app.route('/trips', methods=['PUT'])
def register_trip():
    data = request.get_json()
    required=['clientId', 'vehicleId', 'coordinates']
    for field in required:
        if field not in data or not data[field] or data[field]==" ":
            return jsonify({"error":"Klaida. Trūksta duomenų."}), 400
    
    if not isinstance(data['coordinates'], list) or len(data['coordinates'])!=2:
        return jsonify({"error":"Klaida. Įveskite koordinates."}), 400
    
    latitude = data['coordinates'][0]
    longitude = data['coordinates'][1]
    if not is_valid_coordinates(latitude, longitude):
        return jsonify({"error":"Klaida. Koordinatės įvestos neteisingai."}), 400
    
    clientId=data['clientId']
    vehicleId=data['vehicleId']
    check = get_vehicle(clientId, vehicleId)
    response, status = check
    if status==404:
        return jsonify({"error": "Klaida. Klientas neegzistuoja arba neturi transporto priemonės tokiu ID."}), 404
    elif status==200:
        trip=trips.find_one({"clientId": clientId, "status":"active"})
        if trip:
            return jsonify({"error":"Klaida. Šis klientas jau yra pradėjęs kelionę kita transporto priemone."}), 400
    
    tripId = str(ObjectId())
    while trips.find_one({"_id": tripId}):
        tripId = str(ObjectId())
        
    startTime = datetime.now()
    newTrip = {
        "_id": tripId,
        "clientId": clientId,
        "vehicleId": vehicleId,
        "positions": [{"coordinates": [latitude, longitude], "time": startTime}],
        "status": "active"
    }
    
    trips.insert_one(newTrip)
    return jsonify({"message":"Kelionė pradėta sėkmingai.", "id": tripId}), 201    

@app.route('/clients/<string:clientId>/trips', methods=['GET'])
def get_trips(clientId):
    pipeline = []
    
    status = request.args.get('status')
    start = request.args.get('startDate')
    end = request.args.get('endDate')
    vehicle = request.args.get('vehicleId')
    
    check=clients.find_one({"_id":clientId})
    if not check:
        return jsonify({"error":"Klientas tokiu ID neegzistuoja."}), 404
    
    if not vehicle:
        pipeline.append({"$match":{"clientId": clientId}})
    if vehicle:
        check1 = get_vehicle(clientId, vehicle)
        if check1[1]==404:
            return jsonify({"error":"Klientas neturi transporto priemonės tokiu ID."}), 404
        pipeline.append({"$match":{"vehicleId":vehicle}})
    if status:
        pipeline.append({"$match":{"status": status}})
    
    pipeline.append(
        {
            "$addFields":
            {
                "startDate": {"$arrayElemAt": ["$positions.time", 0]},
                "endDate": 
                {
                    "$cond": 
                    {
                        "if": {"$eq": ["$status", "finished"]},
                        "then": {"$arrayElemAt": ["$positions.time",-1]},
                        "else": "$$REMOVE"
                    }
                }
            }
        })
    if start and not end:
        start_date = datetime.fromisoformat(start)
        pipeline.append({"$match":{"startDate":{"$gte":start_date}}})
    elif start and end:
        start_date = datetime.fromisoformat(start)
        end_date = datetime.fromisoformat(end)
        if date_format(end):
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        pipeline.append({"$match":{"startDate":{"$gte":start_date, "$lte":end_date}}})
    elif not start and end:
        end_date = datetime.fromisoformat(end)
        if date_format(end):
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
        pipeline.append({"$match":{"startDate":{"$lte":end_date}}})
     
    tripsList = list(trips.aggregate(pipeline))
    if len(tripsList)==0:
        return jsonify({"message": "Kelionių nėra."}), 200
    
    trip_list = []
    for trip in tripsList:
        trip = rewrite(trip, 1)
        trip_list.append(trip)
    
    return jsonify(trip_list), 200

@app.route('/clients/<string:clientId>/trips/<string:tripId>', methods=['GET'])
def get_trip(clientId, tripId):
    check=clients.find_one({"_id":clientId})
    if not check:
        return jsonify({"error":"Klientas tokiu ID neegzistuoja."}), 404
    
    trip = trips.find_one({"_id": tripId, "clientId": clientId})
    if not trip:
        return jsonify({"message": "Klientas neturi kelionės tokiu ID."}), 200
    
    trip = rewrite(trip,1)
    return jsonify(trip), 200
      
@app.route('/clients/<string:clientId>/trips/positions', methods=['PUT'])
def register_position(clientId):
    data = request.get_json()
    if 'coordinates' not in data or not isinstance(data['coordinates'], list) or len(data['coordinates'])!=2:
        return jsonify({"error":"Klaida. Įveskite koordinates."}), 400
    
    latitude = data['coordinates'][0]
    longitude = data['coordinates'][1]
    if not is_valid_coordinates(latitude, longitude):
        return jsonify({"error":"Klaida. Koordinatės įvestos neteisingai."}), 400
    
    check=clients.find_one({"_id": clientId})
    if not check:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    
    active=trips.find_one({"clientId": clientId, "status":"active"})
    if not active:
        return jsonify({"error":"Klaida. Klientas neturi pradėtos kelionės."}), 404
    
    trips.update_one(
        {"clientId": clientId, "status": "active"},
        {"$push": {"positions":{"coordinates": [latitude, longitude], "time": datetime.now()}}})
    return jsonify({"message":"Pozicija užregistruota sėkmingai."}), 201

@app.route('/clients/<string:clientId>/trips/stop', methods=['PUT'])
def end_trip(clientId):
    data = request.get_json()
    if 'coordinates' not in data or not isinstance(data['coordinates'], list) or len(data['coordinates'])!=2:
        return jsonify({"error":"Klaida. Įveskite koordinates."}), 400
    latitude = data['coordinates'][0]
    longitude = data['coordinates'][1]
    if not is_valid_coordinates(latitude, longitude):
        return jsonify({"error":"Klaida. Koordinatės įvestos neteisingai."}), 400
    
    client=clients.find_one({"_id": clientId})
    if not client:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    
    active=trips.find_one({"clientId":clientId, "status":"active"})
    if active:
        endTime = datetime.now()
        trips.update_one(
            {"clientId": clientId, "status":"active"},
            {
                "$set": {"status":"finished"},
                "$push": {"positions":{"coordinates": [latitude, longitude], "time": endTime}}
            }
            )
        return jsonify({"message":"Kelionė užbaigta."}), 200
    else:
        return jsonify({"message":"Klientas neturi jokių pradėtų kelionių."}), 200

@app.route('/clients/<string:clientId>/vehicles', methods=['DELETE'])
def delete_vehicles(clientId): 
    client = clients.find_one({"_id":clientId}, {"vehiclesAmount": {"$size": "$vehicles"}})
    
    if not client:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    
    trips.delete_many({"clientId": clientId})
    clients.update_one({"_id": clientId}, {"$unset":{"vehicles":""}})
    return str(), 204 

@app.route('/clients/<string:clientId>/vehicles/<string:vehicleId>', methods=['DELETE'])
def delete_vehicle(clientId, vehicleId):
    client = clients.find_one({"_id":clientId}, {"vehiclesAmount": {"$size": "$vehicles"}})
    
    if not client:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404

    if vehicleId:
        check = get_vehicle(clientId, vehicleId)
        response, status = check
        if status==404:
            return jsonify({"error": "Klaida. Klientas neturi transporto priemonės tokiu ID."}), 404
        
        trips.delete_many({"clientId": clientId, "vehicleId": vehicleId})
        vehiclesAmount = client.get('vehiclesAmount', 0)
        if vehiclesAmount>1:
            clients.update_one({"_id": clientId}, {"$pull": {"vehicles": {"vehicleId": vehicleId}}})
        else:
            clients.update_one({"_id": clientId}, {"$unset":{"vehicles":""}})
    else:
        trips.delete_many({"clientId": clientId})
        clients.update_one({"_id": clientId}, {"$unset":{"vehicles":""}})
    return str(), 204 

@app.route('/clients/<string:clientId>', methods=['DELETE'])
def delete_client(clientId):
    client = clients.find_one({"_id": clientId})
    if not client:
        return str(), 204
    trips.delete_many({"clientId": clientId})
    clients.delete_one({"_id": clientId})
    return str(), 204

@app.route('/distance/<string:clientId>', methods=['GET'])
def get_distance(clientId):
    tripId=request.args.get('tripId')
    vehicle=request.args.get('vehicleId')
   
    fields=[]
    client = clients.find_one({"_id": clientId})
    if not client:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    if tripId:
        check2 = trips.find_one({"_id": tripId, "clientId": clientId})
        if not check2:
            return jsonify({"error": "Klaida. Klientas neturi kelionės tokiu ID."}), 404
        fields.append('tripId')
    elif vehicle:
        check3 = get_vehicle(clientId, vehicle)
        if check3[1]==404:
            return jsonify({"error": "Klaida. Klientas neturi transporto priemonės tokiu ID."}), 404
        fields.append('vehicleId')
    else:
        fields.append('clientId')
    
    if 'tripId' in fields:
        pipeline = [
            {
                "$match" : {"_id": tripId}
            },
            {
                "$unwind": {"path":"$positions"}
            },
            {
                "$project":
                {
                    "_id": 1,
                    "latitude": { "$arrayElemAt": ["$positions.coordinates", 0]},
                    "longitude": {"$arrayElemAt": ["$positions.coordinates", 1]}
                }
            }
        ]
    elif 'vehicleId' in fields:
        pipeline = [
            {
                "$match" : {"vehicleId": vehicle}
            },
            {
                "$unwind": {"path":"$positions"}
            },
            {
                "$project":
                {
                    "_id": 1,
                    "latitude": { "$arrayElemAt": ["$positions.coordinates", 0]},
                    "longitude": {"$arrayElemAt": ["$positions.coordinates", 1]}
                }
            }
        ]
    else:
        pipeline = [
            {
                "$match" : {"clientId": clientId}
            },
            {
                "$unwind": {"path":"$positions"}
            },
            {
                "$project":
                {
                    "_id": 1,
                    "latitude": { "$arrayElemAt": ["$positions.coordinates", 0]},
                    "longitude": {"$arrayElemAt": ["$positions.coordinates", 1]}
                }
            }
        ]
     
    positionsList = list(trips.aggregate(pipeline))  
    distance=0
    for i in range (len(positionsList)-1):
        if i==len(positionsList)-1 or positionsList[i]['_id']==positionsList[i+1]['_id']:
            latitude1 = float(positionsList[i]['latitude'])
            longitude1 = positionsList[i]['longitude']
            latitude2 = positionsList[i+1]['latitude']
            longitude2 = positionsList[i+1]['longitude']
            distance+=haversine((latitude1, longitude1), (latitude2, longitude2))
        else:
            continue
    km = int(distance/1)
    m = round(((distance - km)*1000),0)
    
    return str("total distance: "+str(km)+" km "+str(int(m))+" m"), 200

@app.route('/duration/<string:clientId>', methods=['GET'])
def get_duration(clientId):
    tripId=request.args.get('tripId')
    vehicleId=request.args.get('vehicleId')
    
    client = clients.find_one({"_id": clientId})
    if not client:
        return jsonify({"error": "Klaida. Klientas tokiu ID neegzistuoja."}), 404
    fields=['clientId']
    pipeline=[]
    if vehicleId:
        check1=get_vehicle(clientId, vehicleId)
        if check1[1]==404:
            return jsonify({"error": "Klaida. Klientas neturi transporto priemonės tokiu ID."}), 404
        fields.pop(fields.index('clientId'))
        fields.append('vehicleId')
    if tripId:
        check3 = trips.find_one({"_id": tripId, "clientId": clientId})
        if not check3:
            return jsonify({"error": "Klaida. Klientas neturi kelionės tokiu ID."}), 404
        if vehicleId:
            if check3['vehicleId']!=vehicleId:
                return jsonify({"error":"Klaida. Šia transporto priemone nebuvo atlikta kelionė tokiu ID."}), 404
        fields.pop(fields.index('clientId'))
        fields.append('tripId')

    if 'tripId' in fields:
        pipeline = [
            {
                "$match": {"_id": tripId}
            },
            {
                "$project": 
                {
                    "_id": 0,
                    "start": { "$arrayElemAt": ["$positions", 0]},
                    "end": {"$arrayElemAt": ["$positions", -1]}
                }
            },
            {
                "$project": { "totalDuration": {"$subtract": ["$end.time", "$start.time"]}}
            } 
        ]
    elif 'vehicleId' in fields:
        pipeline = [
            {
                "$match": {"vehicleId": vehicleId}
            },
            {
                "$project": 
                {
                    "_id": 0,
                    "start": { "$arrayElemAt": ["$positions", 0]},
                    "end": {"$arrayElemAt": ["$positions", -1]}
                }
            },
            {
                "$project": { "duration": {"$subtract": ["$end.time", "$start.time"]}}
            }, 
            {
                "$group":
                {
                    "_id" : None,
                    "totalDuration": {"$sum": "$duration"} 
                }
            },
            {
                "$project": {"_id": 0}
            } 
        ]
    elif 'clientId' in fields:
        pipeline = [
            {
                "$match": {"clientId": clientId}
            },
            {
                "$project": 
                {
                    "_id": 0,
                    "start": { "$arrayElemAt": ["$positions", 0]},
                    "end": {"$arrayElemAt": ["$positions", -1]}
                }
            },
            {
                "$project": { "duration": {"$subtract": ["$end.time", "$start.time"]}}
            },
            {
                "$group":
                {
                    "_id" : None,
                    "totalDuration": {"$sum": "$duration"} 
                }
            },
            {
                "$project": {"_id": 0}
            } 
        ]
    else:
        return str(), 204
    
    trips1 = list(trips.aggregate(pipeline))
    if not trips1:
        return str("total duration: 0s"), 200
    else:
        ms=trips1[0]['totalDuration']
        return str("total duration: "+ rewrite_time(ms)), 200
       
@app.route('/cleanup', methods=['POST'])
def cleanup():
    clients.drop()
    trips.drop()
    return '', 204

if __name__ == '__main__':
    app.run(debug=True, port=8080)