import socket
import time
import json
from datetime import datetime, timedelta

GUI_IP = "192.168.8.235"
GUI_PORT = 9998
BOAT_PORT = 9999

# Load safe points precomputed on laptop
with open("safe_coords.json") as f:
    SAFE_POINTS = set(tuple(p) for p in json.load(f))
print(f"[BOAT] Loaded {len(SAFE_POINTS)} safe coordinates.")

x, y = 0, 0
heading = 0
speed = 0
last_command_time = datetime.utcnow()
TIMEOUT_MINUTES = 20

def check_collision(x, y):
    return (x, y) in SAFE_POINTS

def send_update(mayday=False):
    msg = "MAYDAY" if mayday else f"POS:X:{x},Y:{y},H:{heading}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((GUI_IP, GUI_PORT))
            s.sendall(msg.encode())
        print(f"[BOAT] Sent update: {msg}")
    except Exception as e:
        print(f"[BOAT] Failed to send update: {e}")

def return_and_hold():
    global x, y
    print("[BOAT] Returning to origin...")
    while x != 0 or y != 0:
        if x > 0: x -= 1
        elif x < 0: x += 1
        if y > 0: y -= 1
        elif y < 0: y += 1
        if not check_collision(x, y):
            print("[BOAT] MAYDAY on return!")
            send_update(mayday=True)
        else:
            send_update()
        time.sleep(0.5)
    print("[BOAT] Holding at origin...")
    pattern = ['E', 'N', 'W', 'S', 'W', 'N', 'E', 'S']
    while True:
        if datetime.utcnow() - last_command_time < timedelta(minutes=TIMEOUT_MINUTES):
            print("[BOAT] New command received; exiting holding.")
            break
        for cmd in pattern:
            move_boat(cmd)
            if not check_collision(x, y):
                print("[BOAT] MAYDAY during holding!")
                send_update(mayday=True)
            else:
                send_update()
            time.sleep(0.5)

def move_boat(cmd):
    global x, y, heading, speed
    if cmd == 'N': y += 1; heading = 0
    elif cmd == 'S': y -= 1; heading = 180
    elif cmd == 'E': x += 1; heading = 90
    elif cmd == 'W': x -= 1; heading = 270
    elif cmd == 'SPD+1': speed += 1; print(f"[BOAT] Speed +1 → {speed}")
    elif cmd == 'SPD+5': speed += 5; print(f"[BOAT] Speed +5 → {speed}")
    elif cmd == 'SPD-1': speed = max(0, speed-1); print(f"[BOAT] Speed -1 → {speed}")

def listen_for_commands():
    global last_command_time
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", BOAT_PORT))
    sock.listen(5)
    sock.settimeout(1.0)
    print("[BOAT] Listening for commands...")
    while True:
        if datetime.utcnow() - last_command_time > timedelta(minutes=TIMEOUT_MINUTES):
            return_and_hold()
        try:
            conn, addr = sock.accept()
        except socket.timeout:
            continue
        with conn:
            data = conn.recv(1024)
            if not data:
                continue
            msg = data.decode().strip().upper()
            print(f"[BOAT] Received: {msg}")
            last_command_time = datetime.utcnow()
            move_boat(msg)
            if not check_collision(x, y):
                print("[BOAT] MAYDAY! Boat crashed!")
                send_update(mayday=True)
            else:
                send_update()

if __name__ == "__main__":
    listen_for_commands()
