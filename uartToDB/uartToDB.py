import serial
import sqlite3
import time
from datetime import datetime

def connect_serial():
    return serial.Serial("/dev/serial0", baudrate=115200, timeout=5)

def main():
    conn = sqlite3.connect('sensor_data.db')
    c = conn.cursor()
    
    # Create table with separate columns for sensor name and value
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  sensor_name TEXT,
                  sensor_value REAL)''')
    conn.commit()
    
    ser = connect_serial()
    
    try:
        while True:
            try:
                if ser.in_waiting > 0:
                    raw_data = ser.readline().decode('utf-8').strip()
                    print(f"Received: {raw_data}")
                    
                    # Process data format: #sensor1:val1,sensor2:val2...$
                    if raw_data.startswith('#') and raw_data.endswith('$'):
                        clean_data = raw_data[1:-1]  # Remove start/end markers
                        sensors = clean_data.split(',')
                        
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        for sensor in sensors:
                            try:
                                name, value = sensor.split(':')
                                c.execute('''INSERT INTO sensor_data 
                                           (timestamp, sensor_name, sensor_value) 
                                           VALUES (?, ?, ?)''',
                                           (current_time, name.strip(), float(value)))
                                conn.commit()
                                print(f"Inserted: {name} = {value} at {current_time}")
                            except ValueError as e:
                                print(f"Error parsing sensor data: {str(e)}")
                    
                time.sleep(30) # 600ms
                
            except (OSError, serial.SerialException):
                print("Connection lost - reconnecting...")
                ser.close()
                ser = connect_serial()
                time.sleep(2)
                
    except KeyboardInterrupt:
        ser.close()
        conn.close()

if __name__ == "__main__":
    main()



    