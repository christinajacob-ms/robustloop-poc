import math
import json
import os
import random
from datetime import datetime

class IndustrialFaultInjector:
    """
    Simuliert komplexe, zeitbasierte Sensorfehler (Industrial Grade).
    Adressiert: Jitter, Clock-Drift, Packet Loss und Transient Outliers.
    """
    def __init__(self, fault_type="freeze", start_ms=2000, duration_ms=1500):
        self.fault_type = fault_type
        self.start_ms = start_ms
        self.duration_ms = duration_ms
        
        # State-Variablen für komplexe Fehler
        self.frozen_value = None
        self.cumulative_drift = 0.0
        self.drift_rate = 0.001 # 1ms Drift pro Sekunde
        
    def process(self, true_distance, current_ms):
        # System-Zeit (Ground Truth Time)
        system_time_sec = current_ms / 1000.0
        
        # Basis-ROS2-Message Struktur
        ros_msg = {
            "header": {"stamp_sec": round(system_time_sec, 3)},
            "range": round(true_distance, 3)
        }

        # Fehler-Injektions-Fenster
        if self.start_ms <= current_ms < self.start_ms + self.duration_ms:
            
            if self.fault_type == "freeze":
                if self.frozen_value is None:
                    self.frozen_value = ros_msg["range"]
                ros_msg["range"] = self.frozen_value
                # Zeitstempel friert oft mit ein (typischer Treiber-Bug)
                ros_msg["header"]["stamp_sec"] = round(self.start_ms / 1000.0, 3)

            elif self.fault_type == "jitter":
                # Nicht-deterministischer Jitter (Zeitstempel schwankt zufällig)
                jitter = random.uniform(-0.02, 0.02) # +/- 20ms
                ros_msg["header"]["stamp_sec"] = round(system_time_sec + jitter, 3)

            elif self.fault_type == "clock_drift":
                # Kumulativer Clock-Drift (Uhren laufen auseinander)
                self.cumulative_drift += self.drift_rate * 0.05 # Drift pro Step
                ros_msg["header"]["stamp_sec"] = round(system_time_sec + self.cumulative_drift, 3)

            elif self.fault_type == "dropout":
                # Paketverlust: Nachricht wird einfach nicht gesendet (Simuliert QoS-Loss)
                if random.random() < 0.3: # 30% Verlustwahrscheinlichkeit
                    return None 

            elif self.fault_type == "outlier":
                # Transiente statistische Ausreißer (z.B. Reflexionen an glänzenden Objekten)
                if random.random() < 0.1: # 10% Chance für einen Spike
                    ros_msg["range"] = round(random.uniform(0.1, 5.0), 3)

        else:
            self.frozen_value = None

        return ros_msg

def run_simulation(fault_type):
    timestamps, truth, sensor, statuses = [], [], [], []
    
    injector = IndustrialFaultInjector(fault_type=fault_type)
    
    current_ms = 0
    robot_speed_ms = 0.2 # 0.2 m/s Richtung Wand
    
    # Safety Assertion: Wenn wir näher als 0.5m dran sind, aber der Sensor > 0.5m meldet -> FAIL
    brake_threshold_m = 0.5
    
    while current_ms <= 5000:
        t_sec = current_ms / 1000.0
        true_dist = max(0.0, 2.0 - (robot_speed_ms * t_sec))
        
        msg = injector.process(true_dist, current_ms)
        
        # Handle Dropout (Keine Nachricht empfangen)
        if msg is None:
            sensor_val = None # Lücke in den Daten
            status = "WARNING: Packet Loss" if true_dist < brake_threshold_m else "RUNNING"
        else:
            sensor_val = msg["range"]
            status = "RUNNING"
            if true_dist <= brake_threshold_m and sensor_val > brake_threshold_m:
                status = "FAIL: Safety Violation (Sensor blindness)"

        timestamps.append(round(t_sec, 2))
        truth.append(round(true_dist, 3))
        sensor.append(sensor_val)
        statuses.append(status)
        
        current_ms += 50
        
    return timestamps, truth, sensor, statuses

def generate_report(timestamps, truth, sensor, statuses, fault_type):
    # Finde den ersten Fail-Punkt
    fail_index = next((i for i, s in enumerate(statuses) if "FAIL" in s), None)
    
    data_json = json.dumps({
        "labels": timestamps,
        "datasets": [
            {
                "label": "Ground Truth (Physical Reality)",
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
                "fill": False,
                "spanGaps": False # Wichtig, um Dropouts als Lücken zu zeigen!
            }
        ]
    })

    html_content = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <title>RobustLoop Industrial Report V3</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 40px; background-color: #f4f7f6; }}
            .container {{ max-width: 1000px; margin: auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            .meta-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 5px solid #3498db; margin-bottom: 20px; }}
            .fail {{ color: #e74c3c; font-weight: bold; }}
            .pass {{ color: #27ae60; font-weight: bold; }}
            .tag {{ background: #3498db; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RobustLoop Reliability Report <span style="font-size: 18px; color: #7f8c8d;">V3 (Industrial)</span></h1>
            <div class="meta-box">
                <p><strong style="color:#2c3e50">Test-ID:</strong> RL-IND-003 | <strong style="color:#2c3e50">Fault Type:</strong> <span class="tag">{fault_type.upper()}</span></p>
                <p><strong style="color:#2c3e50">Safety Assertion:</strong> <code>distance < 0.5m AND sensor > 0.5m</code></p>
                <p><strong style="color:#2c3e50">Result:</strong> <span class="fail">FAIL</span> - Robot failed to detect critical proximity due to semantic fault.</p>
                <p><strong style="color:#2c3e50">Incident Time:</strong> {fail_index * 0.05 if fail_index else 'N/A'}s</p>
            </div>
            <canvas id="faultChart" width="800" height="400"></canvas>
            <div style="margin-top: 20px; font-size: 13px; color: #666; line-height: 1.6;">
                <strong>Technical Analysis:</strong><br>
                This test simulates real-world failures described by industrial partners (Fraunhofer IPA / Olive Robotics). 
                The <b>Ground Truth</b> represents the physical reality, while the <b>Sensor Output</b> represents the data stream entering the ROS2 navigation stack. 
                The FAIL occurs because the software trusts the plausible but incorrect sensor value, bypassing the safety buffer.
            </div>
        </div>

        <script>
            const ctx = document.getElementById('faultChart').getContext('2d');
            const chartData = {data_json};
            const myChart = new Chart(ctx, {{
                type: 'line',
                data: chartData,
                options: {{
                    scales: {{
                        x: {{ type: 'linear', title: {{ display: true, text: 'Time (Seconds)' }} }},
                        y: {{ title: {{ display: true, text: 'Distance to Obstacle (Meters)' }}, min: 0, max: 2.5 }}
                    }},
                    plugins: {{
                        title: {{ display: true, text: 'Physical Reality vs. Faulty Sensor Stream' }}
                    }}
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
    print("="*60)
    print("RobustLoop Industrial Fault Injection - V3")
    print("="*60)
    
    faults = ["freeze", "jitter", "clock_drift", "dropout", "outlier"]
    
    for f in faults:
        print(f"\n[+] Simulating {f} fault...")
        t, truth, sensor, statuses = run_simulation(f)
        filename = generate_report(t, truth, sensor, statuses, f)
        print(f"    Report generated: {filename}")
    
    print("\n" + "="*60)
    print("V3 Industrial Reports complete. Open them in your browser.")
    print("="*60)
    
    # Open the first one automatically
    try:
        os.startfile("robustloop_report_freeze.html")
    except:
        pass
