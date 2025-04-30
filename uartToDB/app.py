from flask import Flask, render_template, jsonify
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)


def get_db_connection():
    try:
        conn = sqlite3.connect('sensor_data.db')
        conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None
    

@app.route('/')
def dashboard():
    return render_template('dashboard.html')


@app.route('/api/sensors')
def get_sensor_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        c = conn.cursor()
        sensor_data = {}
        timestamps = []
        
        # Get last 120 points for each sensor with timestamps
        for i in range(1, 9):
            c.execute('''SELECT sensor_value, timestamp 
                        FROM sensor_data 
                        WHERE sensor_name = ?
                        ORDER BY timestamp DESC 
                        LIMIT 120''', (f'sensor{i}',))
            results = c.fetchall()
            sensor_data[f'sensor{i}'] = [float(row[0]) for row in results]
            if i == 1:  # Only need to get timestamps once
                timestamps = [row[1] for row in results]
        
        return jsonify({
            'sensor_data': sensor_data,
            'timestamps': timestamps})
    
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)