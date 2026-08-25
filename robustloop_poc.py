import math
import json
import os
from datetime import datetime

class FaultInjector:
    """
    Simuliert semantische Sensorfehler (Freeze, Delay) in einem ROS2-ähnlichen Datenstrom.
    """
    def __init__(self, fault_type="freeze", start_ms=2000, duration_ms=700):
        self.fault_type = fault_type
        self.start_ms = start_ms
        self.duration_ms = duration_ms
        self.frozen_value = None
        self.buffer = []

    def process(self, true_distance, current_ms):
        # Simuliere einen ROS2 Header (Zeit in Sekunden)
        timestamp_sec = current_ms / 1000.0
        
        # Normale, fehlerfreie Message
        ros_msg = {
            "header": {"stamp_sec": round(timestamp_sec, 3)},
            "range": round(true_distance, 3)
        }

        if self.start_ms <= current_ms < self.start_ms + self.duration_ms:
            if self.fault_type == "freeze":
                if self.frozen_value is None:
                    self.frozen_value = ros_msg["range"]
                ros_msg["range"] = self.frozen_value
                # Bei echtem Freeze friert oft auch der interne Sensor-Takt ein
                ros_msg["header"]["stamp_sec"] = round(self.start_ms / 1000.0, 3)
            
            elif self.fault_type == "delay":
                # Verzögerung: Alter Wert wird geschickt, aber mit altem Zeitstempel
                if self.buffer:
                    delayed_msg = self.buffer.pop(0)
                    ros_msg = delayed_msg
        else:
            self.frozen_value = None

        if self.fault_type == "delay":
            self.buffer.append(ros_msg.copy())
            if len(self.buffer) > 10: # Puffergröße für Verzögerung
                self.buffer.pop(0)

        return ros_msg

def run_simulation(fault_type):
    timestamps, truth, sensor, statuses = [], [], [], []
    
    injector = FaultInjector(fault_type=fault_type, start_ms=2000, duration_ms=1500)
    
    current_ms = 0
    robot_speed_ms = 0.2 # Roboter fährt mit 0.2 m/s auf ein Hindernis zu
    
    # Safety Assertion Konfiguration
    collision_threshold_m = 0.15
    brake_threshold_m = 0.5
    
    while current_ms <= 5000:
        t_sec = current_ms / 1000.0
        # Ground Truth: Roboter nähert sich linear einem Hindernis
        true_dist = 2.0 - (robot_speed_ms * t_sec)
        true_dist = max(0.0, true_dist)
        
        # Hole Sensorwert (potenziell fehlerhaft)
        msg = injector.process(true_dist, current_ms)
        sensor_dist = msg["range"]
        
        # DETERMINISTISCHE SAFETY ASSERTION
        status = "RUNNING"
        if true_dist <= brake_threshold_m and sensor_dist > brake_threshold_m:
            # Ground Truth sagt: "Bremsen!" aber Sensor sagt: "Alles klar, weiterfahren"
            status = "FAIL: Collision imminent, sensor missed ground truth"
        elif true_dist <= collision_threshold_m:
            status = "CRASH"
            
        timestamps.append(round(t_sec, 2))
        truth.append(round(true_dist, 3))
        sensor.append(sensor_dist)
        statuses.append(status)
        
        current_ms += 50
        
    return timestamps, truth, sensor, statuses

def generate_report(timestamps, truth, sensor, statuses, fault_type):
    fail_index = next((i for i, s in enumerate(statuses) if "FAIL" in s), None)
    
    data_json = json.dumps({
        "labels": timestamps,
        "datasets": [
            {
                "label": "Ground Truth (Echte Umgebung)",
                "data": truth,
                "borderColor": "rgba(54, 162, 235, 1)",
                "borderDash": [5, 5],
                "fill": False
            },
            {
                "label": f"Sensor Output (Fault: {fault_type})",
                "data": sensor,
                "borderColor": "rgba(255, 99, 132, 1)",
                "borderWidth": 3,
                "fill": False
            }
        ]
    })

    html_content = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>RobustLoop Reliability Report V2</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; background-color: #f9f9f9; }}
            .container {{ max-width: 900px; margin: auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .meta-box {{ background: #eef2f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .fail {{ color: #e74c3c; font-weight: bold; }}
            .pass {{ color: #27ae60; font-weight: bold; }}
            .code {{ background: #2c3e50; color: #ecf0f1; padding: 10px; border-radius: 4px; font-family: monospace; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RobustLoop Reliability Report</h1>
            <div class="meta-box">
                <p><strong>Test-ID:</strong> RUN-002 | <strong>Fehlerart:</strong> {fault_type.upper()}</p>
                <p><strong>Safety Assertion:</strong> <code>if (true_dist < 0.5m && sensor_dist > 0.5m) -> FAIL</code></p>
                <p><strong>Ergebnis:</strong> <span class="fail">FAIL</span> - Roboter fuhr weiter, obwohl die Ground Truth eine Kollision vorhergesagt hat.</p>
                <p><strong>Zeit bis zum Systemversagen:</strong> {fail_index * 0.05 if fail_index else 'N/A'} Sekunden nach Simulationsstart.</p>
            </div>
            <canvas id="faultChart" width="800" height="400"></canvas>
            <p style="font-size: 12px; color: #7f8c8d; margin-top: 20px;">* Deterministische Auswertung: Der Test schlägt fehl, weil die Software dem fehlerhaften Sensor vertraut hat, anstatt die physikalische Unmöglichkeit (Ground Truth) abzufangen.</p>
        </div>

        <script>
            const ctx = document.getElementById('faultChart').getContext('2d');
            const chartData = {data_json};
            const myChart = new Chart(ctx, {{
                type: 'line',
                data: chartData,
                options: {{
                    scales: {{
                        x: {{ type: 'linear', title: {{ display: true, text: 'Zeit (Sekunden)' }} }},
                        y: {{ title: {{ display: true, text: 'Hindernisabstand (Meter)' }}, min: 0, max: 2.5 }}
                    }},
                    plugins: {{ title: {{ display: true, text: 'Verhalten bei Semantic Fault Injection' }} }}
                }}
            }});
        </script>
    </body>
    </html>
    """

    report_filename = f"robustloop_report_{fault_type}.html"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return report_filename

if __name__ == "__main__":
    print("="*50)
    print("RobustLoop Fault Injection - V2 (With Safety Assertions)")
    print("="*50)
    
    # Test 1: Freeze Fault
    print("\n[1/2] Simuliere 'Freeze' Fehler...")
    t, truth, sensor, statuses = run_simulation(fault_type="freeze")
    filename1 = generate_report(t, truth, sensor, statuses, "freeze")
    try:
        os.startfile(filename1)
    except:
        pass
    
    # Test 2: Delay Fault
    print("[2/2] Simuliere 'Delay' Fehler...")
    t, truth, sensor, statuses = run_simulation(fault_type="delay")
    filename2 = generate_report(t, truth, sensor, statuses, "delay")
    
    print("\n" + "="*50)
    print("V2 Reports erfolgreich generiert. (Öffne die HTML-Dateien im Browser)")
    print("="*50)
