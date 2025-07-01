import numpy as np
from PIL import Image
from sklearn.cluster import KMeans
import json

MAP_FILE = "allBlue.png" #"static/img/c7380979-e49d-4b9c-9c61-2cd361ac5631.png"

img = Image.open(MAP_FILE).convert("RGB")
w, h = img.size
pixels = np.array(img).reshape((-1, 3))

print("[AI] Running KMeans clustering...")
kmeans = KMeans(n_clusters=3, random_state=0).fit(pixels)
labels = kmeans.labels_
centers = kmeans.cluster_centers_

# Find the "bluest" cluster by max average blue component
bluest_idx = np.argmax(centers[:, 2])  # index of cluster with highest B

safe_coords = []
idx = 0
for y in range(h):
    for x in range(w):
        if labels[idx] == bluest_idx:
            boat_x = x - w // 2
            boat_y = h // 2 - y
            safe_coords.append((boat_x, boat_y))
        idx += 1

with open("safe_coords.json", "w") as f:
    json.dump(safe_coords, f)

print(f"[AI] Saved {len(safe_coords)} safe water points in cluster {bluest_idx}")
