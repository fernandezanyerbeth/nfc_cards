import os
from flask import Flask, jsonify, render_template_string, request
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import requests
from ua_parser import user_agent_parser

# Cargar variables de entorno
load_dotenv(override=True)

app = Flask(__name__)

# Conexión a la base de datos
def get_db_connection():
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")

    conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)
    print(conn)
    return conn
def get_location_from_ip(ip):
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/").json()
        return {
            "city": response.get("city", "Desconocido"),
            "region": response.get("region", "Desconocido"),
            "country": response.get("country_name", "Desconocido")
        }
    except:
        return {"city": "Desconocido", "region": "Desconocido", "country": "Desconocido"}
# Ruta para mostrar los datos de la tarjeta
@app.route('/card/<int:card_id>')
def show_card(card_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Obtener datos de la tarjeta
    cur.execute("SELECT * FROM cards WHERE id = %s", (card_id,))
    card = cur.fetchone()
    
    if not card:
        cur.close()
        conn.close()
        return jsonify({"error": "Tarjeta no encontrada"}), 404
    
    # Capturar métricas avanzadas
    ip = request.remote_addr
    user_agent = request.headers.get("User-Agent", "Desconocido")
    device_info = user_agent_parser.Parse(user_agent)
    location = get_location_from_ip(ip)
    
    # Registrar escaneo con métricas
    cur.execute("""
        INSERT INTO scans (card_id, ip, device, city, region, country)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        card_id, ip, f"{device_info['user_agent']['family']} ({device_info['os']['family']})",
        location["city"], location["region"], location["country"]
    ))
    conn.commit()
    
    # HTML para mostrar datos
    instagram_url = f"instagram://user?username={card['instagram']}" if card["instagram"] else "#"
    instagram_fallback = f"https://www.instagram.com/{card['instagram']}/" if card["instagram"] else "#"
    
    html = """
    <h1>Tarjeta NFC</h1>
    <p><strong>Nombre:</strong> {{ name }}</p>
    <p><strong>Email:</strong> {{ email }}</p>
    <p><strong>Teléfono:</strong> {{ phone }}</p>
    {% if instagram %}
    <p>
        <a href="{{ instagram_url }}" 
           onclick="setTimeout(function(){ window.location='{{ instagram_fallback }}'; }, 500);"
           style="display: inline-block; padding: 10px 20px; background-color: #E1306C; color: white; text-decoration: none; border-radius: 5px;">
           Seguir en Instagram
        </a>
    </p>
    {% endif %}
    <p><a href='https://tu-app.onrender.com/subscribe'>Suscríbete para métricas avanzadas</a></p>
    """
    cur.close()
    conn.close()
    return render_template_string(html, **card, instagram_url=instagram_url, instagram_fallback=instagram_fallback)

# Ruta para ver métricas
@app.route('/metrics/<int:card_id>')
def get_metrics(card_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Verificar si el dueño está suscrito
    cur.execute("SELECT id FROM cards WHERE id = %s", (card_id,))
    card = cur.fetchone()
    if not card:
        cur.close()
        conn.close()
        return jsonify({"error": "Tarjeta no encontrada"}), 404
    
    cur.execute("SELECT subscribed FROM users WHERE id = %s", (card_id,))
    user = cur.fetchone()
    is_subscribed = user and user["subscribed"]
    
    # Métricas básicas (gratis)
    cur.execute("SELECT COUNT(*) as scan_count FROM scans WHERE card_id = %s", (card_id,))
    basic_metrics = cur.fetchone()
    
    if not is_subscribed:
        cur.close()
        conn.close()
        return jsonify({
            "card_id": card_id,
            "scan_count": basic_metrics["scan_count"],
            "message": "Suscríbete para métricas avanzadas (IP, dispositivo, ubicación)"
        })
    
    # Métricas avanzadas (suscripción)
    cur.execute("""
        SELECT ip, device, city, region, country, scan_time
        FROM scans WHERE card_id = %s
        ORDER BY scan_time DESC
    """, (card_id,))
    advanced_metrics = cur.fetchall()
    
    cur.close()
    conn.close()
    print(basic_metrics["scan_count"])
    print(basic_metrics)
    return jsonify({
        "card_id": card_id,
        "scan_count": basic_metrics["scan_count"],
        "details": advanced_metrics
    })
@app.route('/subscribe')
def subscribe():
    return """
    <h1>Suscripción</h1>
    <p>Por solo $5/mes, obtén métricas avanzadas para tus tarjetas NFC.</p>
    <p>Contacta al equipo: soporte@tu-emprendimiento.com</p>
    """

# Insertar una tarjeta de prueba (ejecutar una vez)
def insert_test_card():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO cards (name, email, phone, url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (url) DO NOTHING
    """, ("Juan Perez", "juan@example.com", "123-456-7890", "http://localhost:5000/card/1"))
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    insert_test_card()  # Inserta una tarjeta de prueba al iniciar
    print("entrando en la app")
    app.run(debug=True)