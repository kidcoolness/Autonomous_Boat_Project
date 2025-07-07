import socket
import time
import json
import math
from datetime import datetime, timedelta
import threading

GUI_IP = "172.16.0.9"
GUI_PORT = 9998
BOAT_PORT = 9999

# Load safe points precomputed on laptop
with open("safe_coords.json") as f:
    SAFE_POINTS = set(tuple(p) for p in json.load(f))
print(f"[BOAT] Loaded {len(SAFE_POINTS)} safe coordinates.")

boat_state = {
    "x": 0,
    "y": 0,
    "mayday": False,
    "trail": [],
    "heading": 0,
}

speed = 1
last_command_time = datetime.utcnow()
TIMEOUT_MINUTES = 5

def check_collision(x, y):
    return (x, y) in SAFE_POINTS

def send_update(mayday=False):
    msg = "MAYDAY" if mayday else f"POS:X:{boat_state['x']},Y:{boat_state['y']},H:{boat_state['heading']}"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((GUI_IP, GUI_PORT))
            s.sendall(msg.encode())
        print(f"[BOAT] Sent update: {msg}")
    except Exception as e:
        print(f"[BOAT] Failed to send update: {e}")

def move_continuously():
    global last_command_time
    while True:
        # Return to holding if no commands received
        if datetime.utcnow() - last_command_time > timedelta(minutes=TIMEOUT_MINUTES):
            return_and_hold()

        if speed > 0:
            rad = math.radians(boat_state["heading"])
            dx = round(math.cos(rad) * speed)
            dy = round(math.sin(rad) * speed)
            boat_state["x"] += dx
            boat_state["y"] += dy

            # Update trail every move
            boat_state["trail"].append((boat_state["x"], boat_state["y"]))

            if not check_collision(boat_state["x"], boat_state["y"]):
                print("[BOAT] MAYDAY during movement!")
                send_update(mayday=True)
                boat_state["mayday"] = True
            else:
                send_update()
                boat_state["mayday"] = False

        time.sleep(2.0)

def return_and_hold():
    print("[BOAT] Returning to holding point...")
    global speed

    # Calculate correct heading towards (0,0) on every move
    while boat_state["x"] != 0 or boat_state["y"] != 0:
        dx = -boat_state["x"]
        dy = -boat_state["y"]

        # Compute angle in degrees from current pos to (0,0)
        if dx == 0 and dy == 0:
            heading_to_zero = boat_state["heading"]
        else:
            heading_to_zero = (math.degrees(math.atan2(dy, dx)) + 360) % 360

        boat_state["heading"] = heading_to_zero

        # Move towards (0,0) by speed step
        distance = math.hypot(dx, dy)
        step = min(speed, distance)

        if distance < 1:
            boat_state["x"], boat_state["y"] = 0, 0
        else:
            boat_state["x"] += round(math.cos(math.radians(heading_to_zero)) * step)
            boat_state["y"] += round(math.sin(math.radians(heading_to_zero)) * step)

        boat_state["trail"].append((boat_state["x"], boat_state["y"]))

        if not check_collision(boat_state["x"], boat_state["y"]):
            print("[BOAT] MAYDAY on return!")
            send_update(mayday=True)
            boat_state["mayday"] = True
        else:
            send_update()
            boat_state["mayday"] = False
        time.sleep(0.5)

    print("[BOAT] Holding at origin...")
    pattern = [(90, 30), (0, 30), (270, 30), (180, 30)]  # E, N, W, S with duration steps

    while True:
        if datetime.utcnow() - last_command_time < timedelta(minutes=TIMEOUT_MINUTES):
            print("[BOAT] New command received; exiting holding.")
            break

        for hold_heading, hold_duration in pattern:
            boat_state["heading"] = hold_heading
            for _ in range(hold_duration):
                if datetime.utcnow() - last_command_time < timedelta(minutes=TIMEOUT_MINUTES):
                    print("[BOAT] New command received; exiting holding.")
                    return
                boat_state["x"] += round(math.cos(math.radians(boat_state["heading"])) * speed)
                boat_state["y"] += round(math.sin(math.radians(boat_state["heading"])) * speed)
                boat_state["trail"].append((boat_state["x"], boat_state["y"]))

                if not check_collision(boat_state["x"], boat_state["y"]):
                    print("[BOAT] MAYDAY during holding!")
                    send_update(mayday=True)
                    boat_state["mayday"] = True
                else:
                    send_update()
                    boat_state["mayday"] = False
                time.sleep(0.5)


def move_boat(cmd):
    global speed
    if cmd == 'N':
        boat_state["heading"] = 270  # Up = decrease Y
        print("[BOAT] Heading set to North")
    elif cmd == 'S':
        boat_state["heading"] = 90   # Down = increase Y
        print("[BOAT] Heading set to South")
    elif cmd == 'E':
        boat_state["heading"] = 0    # Right = increase X
        print("[BOAT] Heading set to East")
    elif cmd == 'W':
        boat_state["heading"] = 180  # Left = decrease X
        print("[BOAT] Heading set to West")
    elif cmd == 'SPD+1':
        speed += 1
        print(f"[BOAT] Speed +1 → {speed}")
    elif cmd == 'SPD+5':
        speed += 5
        print(f"[BOAT] Speed +5 → {speed}")
    elif cmd == 'SPD-1':
        speed = max(0, speed-1)
        print(f"[BOAT] Speed -1 → {speed}")
    elif cmd == 'HOLD':
        print("[BOAT] Commanded to return to holding pattern.")
        return_and_hold()


def listen_for_commands():
    global last_command_time
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("0.0.0.0", BOAT_PORT))
    sock.listen(5)
    sock.settimeout(1.0)
    print("[BOAT] Listening for commands...")
    while True:
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

if __name__ == "__main__":
    threading.Thread(target=listen_for_commands, daemon=True).start()
    move_continuously()
