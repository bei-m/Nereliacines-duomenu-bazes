from flask import Flask, jsonify, request
from cassandra.cluster import Cluster
import uuid
from datetime import datetime, timezone

app = Flask(__name__)

cluster = Cluster(['127.0.0.1'], port=9042)
session = cluster.connect()

with app.app_context():
    session.execute("DROP keyspace if exists chatservice")
    
    session.execute("""
        CREATE KEYSPACE IF NOT EXISTS chatservice
        WITH REPLICATION = { 'class': 'SimpleStrategy', 'replication_factor': 1 };
    """)
    
    session.execute("""
        CREATE TABLE IF NOT EXISTS chatservice.channels (
            id text,
            owner text,
            topic text,
            PRIMARY KEY (id, owner)
        );
    """)

    session.execute("""
        CREATE TABLE IF NOT EXISTS chatservice.messagesId (
            channel_id text,
            text text,
            author text,
            timestamp timestamp,
            PRIMARY KEY (channel_id, author, timestamp)
        );
    """)
    
    session.execute("""
        CREATE TABLE IF NOT EXISTS chatservice.messagesIdDate (
            channel_id text,
            text text,
            author text,
            timestamp timestamp,
            PRIMARY KEY (channel_id, timestamp, author)
        );
    """)
    
    session.execute("""
        CREATE TABLE IF NOT EXISTS chatservice.members (
            channel_id text,
            member text,
            PRIMARY KEY (channel_id, member)
        );
    """)

@app.route('/channels/<string:channel_id>/members', methods=['PUT'])
def register_member(channel_id, owner=""):
    duomenys=request.get_json()
    if owner!="":
        duomenys['member']=owner
        
    if 'member' not in duomenys or not duomenys['member'] or duomenys['member']==" ":
        return jsonify({"error":"Klaida. Įveskite narį."}), 400
    
    atsakymas = get_channel(str(channel_id))
    if atsakymas[1]==404:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
    get_member_query="""
        SELECT * FROM chatservice.members
        WHERE channel_id=%s and member=%s;
        """
    rows=session.execute(get_member_query, (channel_id, duomenys['member']))
    
    if rows:
        return jsonify ({"error":"Narys jau registruotas kanale."}), 400
    
    register_member_query="""
    INSERT INTO chatservice.members (channel_id, member)
    VALUES (%s, %s)
    IF NOT EXISTS;
    """
    
    session.execute(register_member_query, (channel_id, duomenys['member']))
    
    return jsonify({"message":"Narys užregistruotas sėkmingai."}), 201

@app.route('/channels', methods=['PUT'])
def create_channel():
    duomenys = request.get_json()
    
    if 'owner' not in duomenys or not duomenys['owner'] or duomenys['owner']==" ":
        return jsonify ({"error":"Klaida. Neįvestas savininko vardas."}), 400
  
    if 'id' not in duomenys or not duomenys['id'] or duomenys['id']==" ":
        channel_id = str(uuid.uuid4())
        wasgiven=False
    else:
        channel_id=str(duomenys['id'])
        wasgiven=True
    
    insert_query="""
        INSERT INTO chatservice.channels (id, owner) 
        VALUES (%s, %s);
    """  
    columns=["id", "owner"]
    reiksmes=[channel_id, duomenys['owner']]
    if 'topic' in duomenys and duomenys['topic'] and duomenys['topic']!=" ":
        columns.append("topic")
        reiksmes.append(duomenys['topic'])
    
    insert_query=f"INSERT INTO chatservice.channels ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(reiksmes))}) IF NOT EXISTS;"
    
    while True:
        result = session.execute(insert_query, reiksmes)
        if result.was_applied:
            register_member(channel_id, duomenys['owner'])
            return jsonify({"id": channel_id}), 201
        elif not result.was_applied and wasgiven:
            return jsonify({"error": "Kanalas tokiu ID jau egzistuoja."}), 400
        else:
            channel_id = str(uuid.uuid4())
    
@app.route('/channels/<string:channel_id>', methods=['GET'])
def get_channel(channel_id):
    get_query="""
    SELECT * FROM chatservice.channels WHERE id=%s;               
    """
    rows=session.execute(get_query, (channel_id,))
    
    info=rows.one()
    
    if info:
        informacija={
            'id': str(info.id),
            'owner': str(info.owner),
        }
        if info.topic:
            informacija['topic']=str(info.topic)
        return jsonify(informacija), 200
    
    else:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
@app.route('/channels/<string:channel_id>', methods=['DELETE'])
def delete_channel(channel_id):
    
    atsakymas = get_channel(channel_id)
    if atsakymas[1]==404:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
    delete_query1="""
    DELETE FROM chatservice.messagesId
    WHERE channel_id=%s;
    """
    
    delete_query2="""
    DELETE FROM chatservice.messagesIdDate
    WHERE channel_id=%s;
    """
    
    delete_query3="""
    DELETE FROM chatservice.members
    WHERE channel_id=%s;
    """
    
    delete_query4="""
    DELETE FROM chatservice.channels
    WHERE id=%s;
    """
    
    session.execute(delete_query1, (channel_id,))
    session.execute(delete_query2, (channel_id,))
    session.execute(delete_query3, (channel_id,))
    session.execute(delete_query4, (channel_id,))
    
    return '', 204

@app.route('/channels/<string:channel_id>/messages', methods=['PUT'])
def post_message(channel_id):
    duomenys=request.get_json()
    
    if 'text' not in duomenys or not duomenys['text'] or duomenys['text']==" ":
        return jsonify({"error":"Klaida. Neįvestas žinutės tekstas."}), 400
    elif 'author' not in duomenys or not duomenys['author'] or duomenys['author']==" ":
        return jsonify({"error":"Klaida. Neįvestas žinutės autorius."}), 400
    
    atsakymas = get_channel(channel_id)
    if atsakymas[1]==404:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
    timestamp = datetime.now(timezone.utc)
    post_message_query1="""
    INSERT INTO chatservice.messagesId (channel_id, text, author, timestamp)
    VALUES (%s, %s, %s, %s)
    IF NOT EXISTS;
    """
    
    post_message_query2="""
    INSERT INTO chatservice.messagesIdDate (channel_id, text, author, timestamp)
    VALUES (%s, %s, %s, %s)
    IF NOT EXISTS;
    """

    session.execute(post_message_query1, (channel_id, duomenys['text'], duomenys['author'], timestamp))
    session.execute(post_message_query2, (channel_id, duomenys['text'], duomenys['author'], timestamp))
    
    return jsonify({"message":"Žinutė pridėta sėkmingai."}), 201

@app.route('/channels/<string:channel_id>/messages', methods=['GET'])
def get_messages(channel_id):
    startat = request.args.get('startAt')
    author = request.args.get('author')
    
    atsakymas = get_channel(str(channel_id))
    if atsakymas[1]==404:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
    if not startat and not author:
        get_message_query="""
        SELECT text, author, timestamp FROM chatservice.messagesIdDate
        WHERE channel_id=%s
        ORDER BY timestamp ASC;
        """
        rows=session.execute(get_message_query, (channel_id,))
        
    elif not startat and author:
        get_message_query="""
        SELECT text, author, timestamp FROM chatservice.messagesId
        WHERE channel_id=%s and author=%s
        ORDER BY timestamp ASC;
        """
        rows=session.execute(get_message_query, (channel_id, author))
        
    elif startat and not author:
        timestamp = datetime.fromisoformat(str(startat))
        get_message_query="""
        SELECT text, author, timestamp FROM chatservice.messagesIdDate
        WHERE channel_id=%s and timestamp>=%s
        ORDER BY timestamp ASC;
        """
        rows=session.execute(get_message_query, (channel_id, timestamp))
        
    else: #startat and author
        timestamp = datetime.fromisoformat(str(startat))
        get_message_query="""
        SELECT text, author, timestamp FROM chatservice.messagesId
        WHERE channel_id=%s and author=%s and timestamp>=%s
        ORDER BY timestamp ASC;
        """
        rows=session.execute(get_message_query, (channel_id, author, timestamp))
    
    if rows:   
        messages = [{'text': row.text, 'author': row.author, 'timestamp': str(row.timestamp)} for row in rows]  
        return jsonify(messages), 200
    else:
        return jsonify({"message":"Nėra žinučių atitinkančių paieškos kriterijus."}), 200

@app.route('/channels/<string:channel_id>/members', methods=['GET'])
def get_members(channel_id):
    atsakymas = get_channel(str(channel_id))
    if atsakymas[1]==404:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
    get_members_query="""
    SELECT member from chatservice.members
    WHERE channel_id=%s;
    """
    rows=session.execute(get_members_query, (channel_id,))
    
    if rows:
        members = [str(row.member) for row in rows]
        return jsonify(members), 200
    else:
        return jsonify({"message":"Kanalas neturi narių."}), 200

@app.route('/channels/<string:channel_id>/members/<string:member>', methods=['DELETE'])
def delete_member(channel_id, member):
    atsakymas1 = get_channel(str(channel_id))
    if atsakymas1[1]==404:
        return jsonify({"error":"Kanalas tokiu ID nerastas."}), 404
    
    check="""
    SELECT member FROM chatservice.members
    WHERE channel_id=%s and member=%s;
    """
    rows=session.execute(check, (channel_id, member))
    
    if not rows:
        return jsonify({"error":"Toks nario nurodytame kanale nėra."}), 404
    
    delete_member_query="""
    DELETE FROM chatservice.members
    WHERE channel_id=%s and member=%s;
    """
    
    session.execute(delete_member_query, (channel_id, member))
    
    return jsonify(), 204 

if __name__ == '__main__':
    app.run(debug=True, port=8080)