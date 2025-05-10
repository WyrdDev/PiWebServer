import subprocess
import psutil
import os
import sys
from flask import Flask, render_template, jsonify, request
import sqlite3
from datetime import datetime, timedelta

app = Flask(__name__)



def is_uart_to_db_running():
    """Check if uartToDB.py is currently running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Look for python processes running uartToDB.py
            if proc.info['name'] == 'python' or proc.info['name'] == 'python3':
                cmdline = proc.info['cmdline']
                if any('uartToDB.py' in arg for arg in cmdline if arg):
                    return True, proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False, None

def start_uart_to_db():
    """Start the uartToDB.py script"""
    try:
        # Get directory of current script
        current_dir = os.path.dirname(os.path.abspath(__file__))
        uart_script_path = os.path.join(current_dir, 'uartToDB.py')
        
        # Launch the process and detach it
        if sys.platform == 'win32':
            # Windows
            subprocess.Popen(['python', uart_script_path], 
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            # Linux/Mac
            subprocess.Popen(['python3', uart_script_path], 
                            start_new_session=True)
        return True
    except Exception as e:
        print(f"Error starting uartToDB.py: {str(e)}")
        return False

def check_and_start_uart_process():
    """Check if uartToDB.py is running and start it if not"""
    is_running, pid = is_uart_to_db_running()
    if is_running:
        return {"status": "running", "pid": pid}
    else:
        success = start_uart_to_db()
        if success:
            return {"status": "started", "pid": None}
        else:
            return {"status": "error", "message": "Failed to start uartToDB.py"}





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
    # Get hours parameter from request, default to 1 hour
    hours = request.args.get('hours', default=1, type=int)
    if hours not in [1, 2, 3, 6, 12, 24]:  # Validate input
        hours = 1
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
    
    try:
        c = conn.cursor()
        sensor_data = {}
        
        # Calculate time threshold
        time_threshold = (datetime.now() - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get data for each sensor since the threshold
        for i in range(1, 9):
            c.execute('''SELECT sensor_value, timestamp 
                        FROM sensor_data 
                        WHERE sensor_name = ? AND timestamp >= ?
                        ORDER BY timestamp DESC''', 
                        (f'sensor{i}', time_threshold))
            results = c.fetchall()
            sensor_data[f'sensor{i}'] = [float(row[0]) for row in results]
            if i == 1:  # Only need to get timestamps once
                timestamps = [row[1] for row in results]
        
        return jsonify({
            'sensor_data': sensor_data,
            'timestamps': timestamps
        })
    
    except sqlite3.Error as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()
        check_and_start_uart_process()




@app.route('/api/uart-status')
def get_uart_status():
    """Endpoint to check and optionally start the UART process"""
    action = request.args.get('action', default='check')
    
    if action == 'check':
        is_running, pid = is_uart_to_db_running()
        return jsonify({"running": is_running, "pid": pid})
    
    elif action == 'start':
        result = check_and_start_uart_process()
        return jsonify(result)
    
    else:
        return jsonify({"error": "Invalid action parameter"}), 400
    



if __name__ == '__main__':
    # Automatically check and start uartToDB.py when Flask starts
    check_and_start_uart_process()
    app.run(host='0.0.0.0', port=8080, debug=True)