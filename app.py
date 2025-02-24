import os
from flask import Flask, jsonify, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# Conexión a la base de datos
def get_db_connection():
    conn = psycopg2.connect(
        host='localhost',
        port=5433,
        database='nfc',
        user='postgres',  # Tu usuario de PostgreSQL
        password=18626622  # Tu contraseña de PostgreSQL
    )
    return conn

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
    
    # Registrar el escaneo
    cur.execute("INSERT INTO scans (card_id) VALUES (%s)", (card_id,))
    conn.commit()
    
    # Plantilla HTML sencilla para mostrar los datos
    html = """
    <h1>Tarjeta de Presentación</h1>
    <p><strong>Nombre:</strong> {{ name }}</p>
    <p><strong>Email:</strong> {{ email }}</p>
    <p><strong>Teléfono:</strong> {{ phone }}</p>
    """
    cur.close()
    conn.close()
    return render_template_string(html, **card)

# Ruta para ver métricas
@app.route('/metrics/<int:card_id>')
def get_metrics(card_id):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("SELECT COUNT(*) as scan_count FROM scans WHERE card_id = %s", (card_id,))
    metrics = cur.fetchone()
    
    cur.close()
    conn.close()
    return jsonify({"card_id": card_id, "scan_count": metrics["scan_count"]})

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
    app.run(debug=True)