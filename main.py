from flask import Flask, request, jsonify
from neo4j import GraphDatabase

app = Flask(__name__)
uri = "bolt://localhost:7687"
username = "neo4j"          
password = "123456789"

driver = GraphDatabase.driver(uri, auth=(username, password))

@app.route('/cleanup', methods=['POST'])
def cleanup():
    query="""
    MATCH (n)
    DETACH DELETE n
    """  
    with driver.session() as s: 
        s.run(query)
        return jsonify({"message":"Cleanup successful."}), 200
    
with app.app_context():
    with driver.session() as session:
        result = session.run("SHOW DATABASES")
        databases = [record["name"] for record in result]
        
        if 'flights' not in databases:
            session.run(f"CREATE DATABASE flights")
        
        driver = GraphDatabase.driver(uri, auth=(username, password), database="flights")
        cleanup()
  
@app.route('/cities', methods=['PUT'])
def register_city():
    duomenys=request.get_json()
    
    if 'name' not in duomenys or not duomenys['name'] or duomenys['name']==" ":
        return jsonify({"error":"Klaida. Nepateiktas miesto pavadinimas."}), 400
    if 'country' not in duomenys or not duomenys['country'] or duomenys['country']==" ":
        return jsonify({"error":"Klaida. Nepateiktas šalies pavadinimas."}), 400
    
    country = duomenys['country'].title()
    name=duomenys['name'].title()
    
    check_query = """
    MATCH (cn:Country {name: $country})
    OPTIONAL MATCH (cn)-[:HAS_CITY]->(ct:City {name: $city})
    RETURN cn, ct
    """
    
    with driver.session() as s:
        result=s.run(check_query, country=country, city=name)
        rezultatas=result.single()
        
        if rezultatas is None:
            create_query="""
            CREATE (c: Country {name: $country})-[:HAS_CITY]->(ct:City {name: $city})
            """
            s.run(create_query, country=country, city=name)
            return jsonify({"message":"Miestas sėkmingai užregistruotas."}), 204 #201
        
        elif rezultatas['cn'] and rezultatas['ct']:
            return jsonify({"error":"Klaida. Toks miestas jau užregistruotas."}), 400
        
        elif rezultatas['cn'] and not rezultatas['ct']:
            create_query="""
            MATCH (c: Country {name:$country})
            CREATE (c)-[:HAS_CITY]->(ct:City {name: $city})
            """
            result = s.run(create_query, country=country, city=name)
            return jsonify({"message":"Miestas sėkmingai užregistruotas."}), 204 #201
        
@app.route('/cities', methods=['GET'])
def get_cities():
    country=request.args.get('country')
    
    if country:
        country=country.title()
        get_query="""
        MATCH (cn:Country{name: $country})-[:HAS_CITY]->(ct:City)
        RETURN cn.name as country , ct.name as city
        """
    else:
        get_query="""
        MATCH (cn:Country)-[:HAS_CITY]->(ct:City)
        RETURN cn.name as country , ct.name as city
        """
    with driver.session() as s:
        result = s.run(get_query, country=country)
        cities = [{"country": record["country"], "name": record["city"]} for record in result]
    return jsonify(cities), 200

@app.route('/cities/<string:name>', methods=['GET'])
def get_city(name):
    
    name=name.title()
    
    get_query="""
    MATCH (c:City{name: $city})<-[HAS_CITY]-(cn:Country) 
    RETURN c.name as city, cn.name as country
    """
     
    with driver.session() as s:
        result = s.run(get_query, city=name)
        
        cities = [{"country": record["country"], "name": record["city"]} for record in result]
        
        if not cities: 
            return jsonify({"error":"Klaida. Miestas nerastas."}), 404
        else:
            return jsonify(cities), 200
        
@app.route('/cities/<string:city>/airports', methods=['PUT'])
def register_airport(city):
    city=city.title()
    duomenys=request.get_json()
    
    if 'name' not in duomenys or not duomenys['name'] or duomenys['name']==" ":
        return jsonify({"error":"Klaida. Nepateiktas oro uosto pavadinimas."}), 400
    
    if 'code' not in duomenys or not duomenys['code'] or duomenys['code']==" ":
        return jsonify({"error":"Klaida. Nepateiktas oro uosto kodas."}), 400
    
    atsakymas=get_city(city)
    if atsakymas[1]==404:
        return jsonify({"error":"Klaida. Nurodytas miestas nėra registruotas sistemoje."}), 400
    
    with driver.session() as s:
        check_query="""
        MATCH (c:City {name: $city})-[:HAS_AIRPORT]->(a:Airport)
        WHERE 
            a.name = $name OR
            a.code = $code
        RETURN a
        """
        result=s.run(check_query, city=city.title(), name=duomenys['name'].title(), code=duomenys['code'])
        if result.single() is not None:
            return jsonify({"error":"Klaida. Oro uostas tokiu pavadinimu arba kodu jau registruotas sistemoje."}), 400
        else:
            name=duomenys['name'].title()
            register_query="""
            MATCH (c:City{name: $city})
            CREATE (c)-[:HAS_AIRPORT]->(a:Airport{name: $name, code: $code}) 
            """
            s.run(register_query, city=city, name=name, code=duomenys['code'])
            if 'numberOfTerminals' in duomenys and duomenys['numberOfTerminals'] and duomenys['numberOfTerminals']!=" ":
                if not isinstance(duomenys['numberOfTerminals'], int):
                    return jsonify({"error":"Klaida. Terminalų skaičius turi būti sveikasis skaičius."}), 400
                update_query="""
                MATCH (a:Airport {name: $name})
                SET a.numberOfTerminals=$terminals
                """
                s.run(update_query, name=name, terminals=duomenys['numberOfTerminals'])
            if 'address' in duomenys and duomenys['address'] and duomenys['address']!=" ":
                update_query="""
                MATCH (a:Airport {name: $name})
                SET a.address=$address
                """
                s.run(update_query, name=name, address=duomenys['address'].title())
            
            return jsonify({"message":"Oro uostas užregistruotas sėkmingai."}), 204 #201
        
@app.route('/cities/<string:city>/airports', methods=['GET'])
def get_airports_in_a_city(city):
    city=city.title()
    
    atsakymas=get_city(city)
    if atsakymas[1]==404:
        return jsonify({"error":"Klaida. Toks miestas nėra registruotas sistemoje."}), 404
    
    get_query="""
    MATCH (a:Airport)<-[HAS_AIRPORT]-(c:City {name: $city})
    RETURN c.name as city, a.code as code, a.name as name, a.address as address, a.numberOfTerminals as numberOfTerminals
    """
    with driver.session() as s:
        result=s.run(get_query, city=city)
        airports = [ {key: record[key] for key in ["city", "code", "name", "numberOfTerminals", "address"] if record.get(key) is not None}
        for record in result]
    return jsonify(airports), 200

@app.route('/airports/<string:code>', methods=['GET'])
def get_airport(code):
    get_query="""
    MATCH (a:Airport {code:$code})<-[HAS_AIRPORT]-(c:City)
    RETURN c.name as city, a.name as name, a.code as code, a.numberOfTerminals as numberOfTerminals, a.address as address
    """
    with driver.session() as s:
        result=s.run(get_query, code=code)
        airports = [ {key: record[key] for key in ["city", "code", "name", "numberOfTerminals", "address"] if record.get(key) is not None}
            for record in result]
        if not airports:
            return jsonify({"error":"Oro uosto nurodytu kodu sistemoje nėra."}), 404
        else:
            return jsonify(airports[0]), 200

@app.route('/flights', methods=['PUT'])
def register_flight():
    duomenys=request.get_json()
    
    butini_laukai = ["number", "fromAirport", "toAirport", "price", "flightTimeInMinutes", "operator"]
    
    missing = [laukas for laukas in butini_laukai if laukas not in duomenys or duomenys[laukas]==" " or not duomenys[laukas]]
    if missing:
        return jsonify({"error": "Klaida. Trūksta informacijos."}), 400
    
    if not isinstance(duomenys['flightTimeInMinutes'], int):
        return jsonify({"error":"Klaida. Skrydžio trukmė turi būti įvesta sveikiaisiais skaičiais."}), 400
    if not isinstance(duomenys['price'], float) and not isinstance(duomenys['price'], int):
        return jsonify({"error":"Klaida. Kaina turi būti įvesta skaičiais."}), 400
    
    atsakymas1=get_airport(duomenys['fromAirport'])
    atsakymas2=get_airport(duomenys['toAirport'])
    print(atsakymas1)
    if atsakymas1[1]==404 or atsakymas2[1]==404:
        return jsonify({"error":"Klaida. Bent vienas iš nurodytų oro uostų nėra registruotas sistemoje."}), 404
    
    check_query="""
    MATCH (a:Airport)<-[f:FLIGHT_TO{number: $number}]-(b:Airport)
    RETURN f
    """
    
    register_query="""
    MATCH (a1:Airport {code: $code1}), (a2:Airport {code: $code2})
    CREATE (a1)-[f:FLIGHT_TO {number: $number, price: $price, flightTimeInMinutes : $flightTimeInMinutes, operator: $operator}]->(a2)
    """
    
    with driver.session() as s:
        result=s.run(check_query, number=duomenys['number'])
        if result.single():
            return jsonify({"error":"Skrydis tokiu numeriu jau registruotas."}), 400
        else:
            s.run(register_query, code1=duomenys['fromAirport'], code2=duomenys['toAirport'], number=duomenys['number'], price=duomenys['price'], flightTimeInMinutes=duomenys['flightTimeInMinutes'], operator=duomenys['operator'])
            return jsonify({"message":"Skrydis užregistruotas sėkmingai."}), 204 #201

@app.route('/flights/<string:code>', methods=['GET'])
def get_flight(code):
    get_query="""
    MATCH (a1:Airport)-[f:FLIGHT_TO {number: $code}]->(a2:Airport)
    MATCH (c1:City)-[:HAS_AIRPORT]->(a1)
    MATCH (c2:City)-[:HAS_AIRPORT]->(a2)
    RETURN a1.code as fromAirport, c1.name as fromCity,
           a2.code as toAirport, c2.name as toCity, 
           f.number as number, f.price as price,        
           f.flightTimeInMinutes as flightTimeInMinutes, f.operator as operator
    """
    
    with driver.session() as s:
        result=s.run(get_query, code=code)
        airport = [ {key: record[key] for key in ["number", "fromAirport", "fromCity", "toAirport", "toCity", "flightTimeInMinutes", "price", "operator"] if record.get(key) is not None}
        for record in result]
        if airport:
            return jsonify(airport[0]), 200
        else:
            return jsonify({"error":"Skrydis tokiu numeriu nerastas."}), 404
    
@app.route('/search/flights/<string:fromCity>/<string:toCity>', methods=['GET'])
def search_flights_between_cities(toCity, fromCity):
    toCity=toCity.title()
    fromCity=fromCity.title()
    
    atsakymas1=get_city(fromCity)
    atsakymas2=get_city(toCity)
    if atsakymas1[1]==404 or atsakymas2[1]==404:
        return jsonify({"error":"Bent vienas iš nurodytų miestų nėra registruotas sistemoje."}), 404
    
    search_query="""
    MATCH (a1:Airport)<-[:HAS_AIRPORT]-(c1:City {name: $fromCity})
    MATCH (a2:Airport)<-[:HAS_AIRPORT]-(c2:City {name: $toCity})
    MATCH path = allShortestPaths((a1)-[:FLIGHT_TO*1..4]->(a2))
    RETURN 
        a1.code AS fromAirport, 
        a2.code AS toAirport,
        [r IN relationships(path) | r.number] AS flights,
        REDUCE(totalPrice = 0, r IN relationships(path) | totalPrice + r.price) AS price,
        REDUCE(totalMinutes = 0, r IN relationships(path) | totalMinutes + r.flightTimeInMinutes) AS flightTimeInMinutes
    """
    
    with driver.session() as s:
        result=s.run(search_query, fromCity=fromCity, toCity=toCity)
        flights = [ {key: record[key] for key in ["fromAirport", "toAirport", "flights", "price", "flightTimeInMinutes"] if record.get(key) is not None}
            for record in result]
        if not flights:
            return jsonify({"error":"Skrydžių nėra."}), 404
        else:
            return jsonify(flights), 200

                
if __name__ == "__main__": 
    app.run(debug=True, port=8080)     