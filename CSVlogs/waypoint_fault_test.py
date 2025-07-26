import airsim
import time
import random
import csv
import datetime

# ----------------------------
# Configurable Waypoints
# ----------------------------
WAYPOINTS = [
   (45, 0, -10), # Start
    (30, 20, -100),
    (39, 39, -77),
    (72, 47, -56),
    (18,28, -50),
    (1500, 50, -50),
]

# ----------------------------
# Initialization
# ----------------------------
client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)
client.takeoffAsync().join()

# Create log file
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"waypoint_log_{timestamp}.csv"

with open(log_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow([
    "ElapsedTime(s)", "FaultActive", "Delay(s)",
    "Target_X", "Target_Y", "Target_Z",
    "Jittered_X", "Jittered_Y", "Jittered_Z",
    "Collision"
])


# ----------------------------
# Fault Injection Movement
# ----------------------------
def move_with_delay_fault(x, y, z, velocity=4, fault_active=False, delay_range=(1.5, 3.0), start_time=None):

    delay = 1  # Temporary default delay
    jitter_x, jitter_y, jitter_z = 0.0, 0.0, 0.0

    if fault_active:
        delay = random.uniform(*delay_range)
        print(f"[FAULT] Injecting artificial delay: {delay:.2f} seconds.")
        time.sleep(delay)
        client.simPrintLogMessage("FAULT", f"Delay: {delay:.2f}s")

        # Inject jitter
        jitter_x = random.uniform(-1.0, 1.0)
        jitter_y = random.uniform(-1.0, 1.0)
        print(f"[FAULT] Jitter applied: ΔX={jitter_x:.2f}, ΔY={jitter_y:.2f}")
    else:
        print("[INFO] No delay fault – moving immediately.")
        client.simPrintLogMessage("MOVE", "Normal command")

    # Apply jitter
    x_jittered = x + jitter_x
    y_jittered = y + jitter_y
    z_jittered = z + jitter_z

    client.moveToPositionAsync(x_jittered, y_jittered, z_jittered, velocity).join()

    # Check for collision
    collision = client.simGetCollisionInfo()
    if collision.has_collided:
        print(f"[COLLISION] Detected with {collision.object_name} at position {collision.position}")
        client.simPrintLogMessage("COLLISION", collision.object_name)
        client.moveToPositionAsync(0, 0, -10, 3).join()

    time.sleep(1)

    # Logging
    if start_time is None:
        start_time = time.time()
    elapsed = time.time() - start_time
    pos = client.getMultirotorState().kinematics_estimated.position

    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            f"{elapsed:.2f}", fault_active, f"{delay:.2f}",
            f"{x:.2f}", f"{y:.2f}", f"{z:.2f}",
            f"{x_jittered:.2f}", f"{y_jittered:.2f}", f"{z_jittered:.2f}",
            "COLLISION" if collision.has_collided else "OK"
        ])


# ----------------------------
# Execute Waypoint Movements
# ----------------------------
print("[INFO] Starting waypoint mission...")
start_time = time.time()

print("[DEBUG] Fault windows are active from 5–10s and 15–20s after start.")


for i, (x, y, z) in enumerate(WAYPOINTS):
    elapsed = time.time() - start_time
   # Force fault on second waypoint
    # Force fault on second waypoint
    fault_active = True if i == 1 else (5 <= elapsed <= 10 or 15 <= elapsed <= 20)

    print(f"[WP-{i+1}] Moving to ({x}, {y}, {z}) | Fault: {fault_active}")
    move_with_delay_fault(x, y, z, velocity=4, fault_active=fault_active, start_time=start_time)
    time.sleep(1)

# ----------------------------
# Land and Cleanup
# ----------------------------
print("[INFO] Mission complete. Landing...")
client.landAsync().join()
client.armDisarm(False)
client.enableApiControl(False)
print("[INFO] Drone disarmed and API control released.")