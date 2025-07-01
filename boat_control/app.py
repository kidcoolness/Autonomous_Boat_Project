import threading
import socket
from flask import Flask, render_template, jsonify
from flask import request

app = Flask(__name__)

boat_state = {
    "x": 0,
    "y": 0,
    "mayday": False,
    "trail": [],
    "heading": 0
}

@app.route("/")
def index():
    return render_template("status.html")

@app.route("/api/send", methods=["POST"])
def api_send():
    data = request.get_json()
    cmd = data.get("command")
    if cmd:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(("192.168.8.244", 9999))  # Replace with your boat’s actual IP if needed
                s.sendall(cmd.encode())
            print(f"[GUI] Sent manual command: {cmd}")
            return jsonify({"status": "ok"})
        except Exception as e:
            print(f"[GUI] Failed to send command: {e}")
            return jsonify({"status": "error", "details": str(e)}), 500
    return jsonify({"status": "error", "details": "No command received"}), 400


@app.route("/api/status")
def api_status():
    return jsonify({
        "x": boat_state["x"],
        "y": boat_state["y"],
        "mayday": boat_state["mayday"],
        "trail": boat_state["trail"],
        "heading": boat_state["heading"]
    })

def listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", 9998))
    sock.listen(5)
    print("[GUI] Listening for boat updates on port 9998")
    while True:
        conn, addr = sock.accept()
        with conn:
            data = conn.recv(1024)
            if not data:
                continue
            msg = data.decode().strip()
            print(f"[GUI] Received: {msg}")
            if msg.startswith("MAYDAY"):
                boat_state["mayday"] = True
            elif msg.startswith("POS:"):
                boat_state["mayday"] = False
                try:
                    parts = msg.split(":")
                    boat_state["x"] = int(parts[2].split(",")[0])
                    boat_state["y"] = int(parts[3].split(",")[0])
                    if len(parts) > 4:
                        boat_state["heading"] = int(parts[4])
                    boat_state["trail"].append((boat_state["x"], boat_state["y"]))
                except Exception as e:
                    print(f"[GUI] Error parsing position: {e}")

if __name__ == "__main__":
    threading.Thread(target=listener, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
