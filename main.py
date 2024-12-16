from flask import Flask, jsonify, request
from pymongo import MongoClient
import re
from bson.objectid import ObjectId


app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
database = client['e-shop']

clients = database['clients']
products = database['products']

clients.drop()
products.drop()

def is_valid_email(email):
    regex = r'^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.match(regex, email) is not None

def rewrite(object, tipas, avoid=''):
    
    if tipas==True: 
        perrasytas = {"id": str(object['_id'])}
        
        for key in object:
            if key!="_id" and key!=avoid: 
                perrasytas[key]=object[key]
                
    else: 
        if 'id' in object and object['id']:
            id = str(object['id'])
        else:
            id = str(ObjectId())
            
        perrasytas = {"_id": id }
        
        for key in object:
            if key!="id" and key!=avoid:
                perrasytas[key]=object[key]
    return perrasytas

@app.route('/clients', methods=['PUT'])
def register_new_client():
    klientoDuomenys = request.get_json()
    
    if 'name' not in klientoDuomenys or 'email' not in klientoDuomenys:
        return jsonify({"error":"Klaida. Nenurodytas kliento vardas arba el. paštas."}), 400

    if not is_valid_email(klientoDuomenys['email']):
        return jsonify({"error":"Klaida. Neteisingai įvestas el. paštas."}), 400
    
    if clients.find_one({'email':klientoDuomenys['email']}):
            return jsonify({"error":"Klaida. El. paštas jau naudojamas kito kliento."}), 400
    
    if 'id' in klientoDuomenys:
        if clients.find_one({'_id': klientoDuomenys['id']}):
            return jsonify({"error":"Klaida. Klientas tokiu ID jau egzistuoja."}), 404
    
    naujasKlientas = rewrite(klientoDuomenys, 0)
    clients.insert_one(naujasKlientas)
     
    return jsonify({"id": str(naujasKlientas['_id'])}), 201

@app.route('/clients/<clientId>', methods=['GET'])
def get_client(clientId):
    klientas = clients.find_one({'_id': clientId})
    if not klientas:
        return jsonify({"error":"Klaida. Klientas tokiu ID neegzistuoja."}), 404
    else:
        client = rewrite(klientas, 1, 'orders') 
        return jsonify(client), 200

@app.route('/clients/<clientId>', methods=['DELETE'])
def delete_client(clientId):
    
    if not clients.find_one({'_id': clientId}):
        return jsonify({"error":"Klaida. Klientas tokiu ID neegzistuoja."}), 404
    else:
        clients.delete_one({'_id': clientId})
        return '', 204  

@app.route('/products', methods=['PUT'])
def register_product():
    produktoDuomenys = request.get_json()
    
    if 'name' not in produktoDuomenys or 'price' not in produktoDuomenys:
        return jsonify({"error":"Klaida. Nenurodytas produkto pavadinimas arba kaina."}), 400
    if not isinstance(produktoDuomenys['price'], (int, float)):
            return jsonify({"error":"Klaida. Kaina turi būti skaičius."}), 400    
    if 'id' in produktoDuomenys:
        if products.find_one({'_id': produktoDuomenys['id']}):
            return jsonify({"error":"Klaida. Produktas tokiu ID jau egzistuoja."}), 400
    
    naujasProduktas = rewrite(produktoDuomenys,0)
    
    products.insert_one(naujasProduktas)
    
    return jsonify({"id":naujasProduktas['_id']}), 201
        
@app.route('/products', methods=['GET'])
def get_products_by_category():
    kategorija = request.args.get('category')

    if kategorija:
        produktai = list(products.find({'category':kategorija}))
    else:
        produktai = list(products.find())
    
    if len(produktai)==0:
        return '', 204
    
    productsList = []
    for produktas in produktai:
        product = rewrite(produktas,1)
        productsList.append(product)
    
    return jsonify(productsList), 200

@app.route('/products/<string:productId>', methods=['GET'])
def get_product(productId):
    produktas = products.find_one({'_id': productId})
    
    if not produktas:
        return jsonify({"error":"Klaida. Produktas tokiu ID neegzistuoja."}), 404
    else:
        product = rewrite(produktas, 1)
        return jsonify(product), 200

@app.route('/products/<productId>', methods=['DELETE'])
def delete_product(productId):
    produktas = products.find_one({'_id': productId})
    if not produktas:
        return jsonify({"error":"Produktas tokiu ID neegzistuoja."}), 404
    else:
        products.delete_one(produktas)
        return '', 204

@app.route('/orders', methods=['PUT'])
def place_order():
    duomenys = request.json
    
    if 'clientId' not in duomenys or 'items' not in duomenys or not duomenys['items']:
        return jsonify({"error":"Klaida. Nenurodytas kliento ID arba užsakymo prekės."}), 400   
    
    klientas = clients.find_one({'_id': duomenys['clientId']})
    
    if not klientas:
        return jsonify({"error":"Klientas tokiu ID neegzistuoja."}), 404
    
    for item in duomenys['items']:
        if 'productId' not in item or 'quantity' not in item or not item['quantity']:
            return jsonify({"message":"Klaida. Nenurodytas produkto ID arba kiekis."}), 400
        
        produktas = products.find_one({"_id":item['productId']})
        if not produktas:
            return jsonify ({"error":"Produktas nurodytu ID nerastas."}), 404
    
    naujasUzsakymas = rewrite(duomenys, 0, 'clientId')
    
    clients.update_one(
        {"_id":klientas['_id']},
        {"$push": {"orders":naujasUzsakymas}}
    )
    return jsonify({"id":naujasUzsakymas['_id']}), 201

@app.route('/clients/<clientId>/orders', methods=['GET'])
def get_client_orders(clientId):
    klientas = clients.find_one({'_id':clientId})
    
    if not klientas:     
        return jsonify({"error":"Klientas tokiu ID neegzistuoja."}), 404
    
    uzsakymai = klientas.get('orders', [])
    
    if not uzsakymai:
        return jsonify({"message":"Šis klientas nėra pateikęs nei vieno užsakymo."}), 200
    
    uzsakymuSarasas = []
    for uzsakymas in uzsakymai:
        uzsakymas = rewrite(uzsakymas, 1, 'clientId')
        uzsakymuSarasas.append(uzsakymas)
    
    return jsonify(uzsakymuSarasas), 200
    
@app.route('/statistics/top/clients', methods=['GET'])
def get_top_clients():
    
    pipeline = [
        {
            "$project": 
            {
                "_id": 0,
                "id": "$_id",
                "name": "$name",
                "totalOrders": { "$size": { "$ifNull": ["$orders", []] } }
            }
        },
        {
            "$sort" : {"totalOrders": -1}
        },
        {
            "$limit" : 10
        }   
    ]
    
    top_clients = list(clients.aggregate(pipeline))
    
    return jsonify(top_clients), 200

@app.route('/statistics/top/products', methods=['GET'])
def get_top_products():
    pipeline = [
        {
            "$unwind": {"path": "$orders"}
        },
        {
            "$unwind": {"path": "$orders.items"}
        },
        {
            "$group":
            {
                "_id": "$orders.items.productId",
                "quantity": {"$sum": "$orders.items.quantity"}
            }
        },
        {
            "$lookup":
            {
                "from": "products",
                "localField": "_id",
                "foreignField": "_id",
                "as": "productsInfo"
            }
        },
        {
            "$unwind": {"path": "$productsInfo"}
        },
        {
            "$project":
            {
                "_id": 0,
                "productId":"$_id",
                "name": "$productsInfo.name",
                "quantity": 1 
            }
        },
        {
            "$sort": {"quantity": -1}
        },
        {
            "$limit": 10
        }
    ]
    
    top_products = list(clients.aggregate(pipeline))
    
    return jsonify(top_products), 200

@app.route('/statistics/orders/total', methods=['GET'])
def get_total_orders():
    pipeline = [
        {
            "$unwind":{"path":"$orders"}
        },
        {
            "$count": "orders"
        },
        {
            "$project": {"total":"$orders"}
        }
    ]
    ordersTotal = list(clients.aggregate(pipeline))
    
    if not ordersTotal:
        return jsonify({"total": 0}), 200
     
    return jsonify(ordersTotal[0]), 200

@app.route('/statistics/orders/totalValue', methods=['GET'])
def get_total_order_value():
    pipeline = [
        {
            "$unwind": {"path": "$orders"}
        },
        {
            "$unwind": {"path": "$orders.items"}
        },
        {
            "$group": 
            {
                "_id": "$orders.items.productId",
                "quantity": {"$sum": "$orders.items.quantity"}
            }
        },
        {
            "$lookup": 
            {
                "from": "products",
                "localField": "_id",
                "foreignField": "_id",
                "as": "productInfo"
            }
        },
        {
            "$unwind": {"path": "$productInfo"}
        },
        {
            "$project": 
            {
                "_id": 0,
                "value": {"$multiply": ["$quantity", "$productInfo.price"]}
            }
        },
        {
            "$group": 
            {
                "_id": None,
                "totalValue": {"$sum": "$value"}
            }
        },
        {
            "$project": 
            {
                "_id": 0,
                "totalValue": {"$round": ["$totalValue", 2]}
            }
        }
    ]
    
    totalValue = list(clients.aggregate(pipeline))
    
    if not totalValue:
        return jsonify({"totalValue": 0}), 200
    
    return jsonify(totalValue[0]), 200

@app.route('/cleanup', methods=['POST'])
def cleanup():
    clients.drop()
    products.drop()
    return '', 204

if __name__ == '__main__':
    app.run(debug=True, port=8080)