import redis
from flask import Flask, request, jsonify
from redis import ConnectionPool
import re

app = Flask(__name__) 

pool = ConnectionPool(host='localhost', port=6379, db=0, decode_responses=True)
r = redis.Redis(connection_pool=pool)

licenseRegex = "^[A-Z]{3}[- ]*[0-9]{3}$"

def garageKey(garazo_id):
    return f'garage:{garazo_id}'

def spotKey(garazo_id, vietos_nr):
    return f'garage:{garazo_id}:spot:{vietos_nr}'

@app.route('/flush', methods=['POST'])
def flush_database():
    r.flushdb()
    return jsonify({"message": "Database cleared successfully!"}), 200


@app.route('/garage', methods=['PUT'])
def register_garage():
    
    duomenys = request.get_json()
    garazo_id = duomenys.get('id')
    spots = duomenys.get('spots')
    address = duomenys.get('address')
    
    if not garazo_id:
        return jsonify({"error": "Nenurodytas id laukas."}), 400
    if not spots:
        return jsonify({"error": "Nenurodytas spots laukas."}), 400
    if not address:
        return jsonify({"error": "Nenurodytas address laukas."}), 400
    
    key = garageKey(garazo_id)
    
    while True:
        with r.pipeline() as trans:
            try:
                trans.watch(key)
                if trans.exists(key):
                    trans.unwatch()
                    return jsonify ({"error": "Toks garažas jau užregistruotas."}), 400

                trans.multi()
                trans.hset(key, mapping={"id":str(duomenys['id']), "spots": int(duomenys['spots']), "address": str(duomenys['address'])})
                trans.execute()
                return jsonify({"message": "Garažas sėkmingai užregistruotas sistemoje."}), 200
            
            except redis.exceptions.WatchError:
                continue
            finally:
                trans.unwatch()

@app.route('/garage/<garazo_id>', methods=['GET'])
def get_garage(garazo_id):  
    key = garageKey(garazo_id)
    if not r.exists(key):
        return jsonify({"error": "Garažas tokiu ID nerastas."}), 404
    
    spots_value = r.hget(key, 'spots')
    address_value = r.hget(key, 'address')
    
    garazo_info = {
            "id": garazo_id,
            "spots": int(spots_value),
            "address": address_value
        }

    return jsonify(garazo_info), 200
     
@app.route('/garage/<garazo_id>/configuration/spots', methods=['GET']) 
def get_spots(garazo_id):
    key = garageKey(garazo_id)
    
    spots = r.hget(key, 'spots')
    
    if spots:
        return str(int(spots)), 200
    else:
        return jsonify({"error":"Garažas su tokiu ID nerastas."}), 404

@app.route('/garage/<garazo_id>/configuration/spots', methods=['POST'])
def update_spots(garazo_id):
    duomenys = request.get_json()
    
    spots = duomenys.get('spots')
    
    if spots<0:
        return jsonify({"error":"Pateiktas neteisingas skaičius. (Vietų skaičius turi būti teigiamas skaičius.)"}), 400
    
    key = garageKey(garazo_id)
    
    while True:
        with r.pipeline() as trans:
            try:
                trans.watch(key)
                if not trans.exists(key):
                    trans.unwatch()
                    return jsonify({"error": "Garažas tokiu ID nerastas."}), 404

                trans.multi()
                trans.hset(key, 'spots', int(spots))
                trans.execute()
                
                return jsonify({"message": "Garažo vietų skaičius pakeistas."}), 200
            
            except redis.exceptions.WatchError:
                continue
            finally:
                trans.unwatch()

@app.route('/garage/<garazo_id>/spots/<int:vietos_nr>', methods=['POST'])
def occupy_spot(garazo_id, vietos_nr): 
    key = garageKey(garazo_id)
    
    while True:
        with r.pipeline() as trans:
            try:
                trans.watch(key)
                if not trans.exists(key):
                    trans.unwatch()
                    return jsonify({"error": "Garažas tokiu ID nerastas."}), 404

                trans.execute()
                trans.hget(key, 'spots')
                spots=trans.execute()
                
                if vietos_nr<1 or vietos_nr>int(spots[0]):
                    trans.unwatch()
                    return jsonify({"error":"Vieta nerasta."}), 404
                
                trans.execute()
                vietosKey = spotKey(garazo_id, vietos_nr)
                trans.exists(vietosKey)
                spot_exists=trans.execute()
                
                if spot_exists[0]:
                    trans.unwatch()
                    return ({"error":"Vieta jau užimta."}), 404
                
                duomenys = request.get_json()
                licenseNo = duomenys.get('licenseNo')
                
                if re.search(licenseRegex, licenseNo) == None:
                    trans.unwatch()
                    return jsonify({"error": "Įvesti neteisingi mašinos numeriai."}), 400
                
                trans.multi()
                trans.set(vietosKey, licenseNo)
                trans.execute()
                return jsonify({"message":"Vieta užimta sėkmingai."}), 200
            
            except redis.exceptions.WatchError:
                continue
            finally:
                trans.unwatch()

@app.route('/garage/<garazo_id>/spots/<int:vietos_nr>', methods=['GET'])
def get_spot_occupier(garazo_id, vietos_nr):
    key = garageKey(garazo_id)
    
    if not r.exists(key):
        return jsonify({"error": "Garažas tokiu ID nerastas."}), 404
    
    spots = r.hget(key, 'spots')
    if vietos_nr<1 or vietos_nr>int(spots):
        return jsonify({"error":"Vieta nerasta."}), 404
    
    vietosKey = spotKey(garazo_id, vietos_nr)
    
    if r.exists(vietosKey):
        vieta=r.get(vietosKey)
        return str(vieta), 200
    else:
        return jsonify({"message": "Vieta laisva."}), 204

@app.route('/garage/<garazo_id>/spots/<int:vietos_nr>', methods=['DELETE']) 
def free_spot(garazo_id, vietos_nr):
    key = garageKey(garazo_id)
    
    while True:
        with r.pipeline() as trans:
            try:
                trans.watch(key)
                if not trans.exists(key):
                    trans.unwatch()
                    return jsonify({"error": "Garažas tokiu ID nerastas."}), 404

                trans.execute()
                trans.hget(key, 'spots')
                spots=trans.execute()
                
                if vietos_nr<1 or vietos_nr>int(spots[0]):
                    trans.unwatch()
                    return jsonify({"error":"Vieta nerasta."}), 404
                
                trans.execute()
                vietosKey = spotKey(garazo_id, vietos_nr)
                
                
                trans.multi()
                trans.delete(vietosKey)
                trans.execute()
                return ({"message":"Vieta atlaisvinta sėkmingai"}), 200
            
            except redis.exceptions.WatchError:
                continue
            finally:
                trans.unwatch()

@app.route('/garage/<garazo_id>/status', methods=['GET']) 
def get_garage_status(garazo_id):
    key = garageKey(garazo_id)
    
    if not r.exists(key):
        return jsonify({"error": "Garažas tokiu ID nerastas."}), 404
    
    spots = r.hget(key, 'spots')
    uzimtos_vietos=0
    
    for vieta in range (1, int(spots)+1):
        vietosKey=spotKey(garazo_id, vieta)
        if r.exists(vietosKey):
            uzimtos_vietos+=1;
    
    return jsonify ({"freeSpots":int(int(spots)-uzimtos_vietos), "occupiedSpots":int(uzimtos_vietos)}), 200
    

if __name__ == "__main__":
    app.run(debug=True, port=8080)
