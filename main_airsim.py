import airsim
import time
import random
import numpy as np
import csv
import datetime

# Create a unique timestamped filename for each log
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"fault_log_{timestamp}.csv"

# Initialize the log file with headers
with open(log_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(["ElapsedTime(s)", "FaultActive", "Delay(s)", "X", "Y", "Z", "Status"])

# ----------------------------
# Setup and Initialization
# ----------------------------
client = airsim.MultirotorClient()
client.confirmConnection()
client.enableApiControl(True)
client.armDisarm(True)

print("[INFO] Taking off...")
client.takeoffAsync().join()


# ----------------------------
# Fault Injection Function
# ----------------------------
def move_with_delay_fault(x, y, z, velocity, fault_active=False, delay_range=(1.5, 3.0), start_time=None):
    delay = 1 #Temporary default delay

    if fault_active:
        delay = random.uniform(*delay_range)
        print(f"[FAULT] Injecting artificial delay: {delay:.2f} seconds.")
        time.sleep(delay)
        client.simPrintLogMessage("FAULT", f"Delay: {delay:.2f}s")
    else:
        print("[INFO] No delay fault – moving immediately.")
        client.simPrintLogMessage("MOVE", "Normal command")

    # Move
    client.moveToPositionAsync(x, y, z, velocity).join()

    # Check for collision
    collision = client.simGetCollisionInfo()
    if collision.has_collided:
        print(f"[COLLISION] Detected with {collision.object_name} at position {collision.position}")
        client.simPrintLogMessage("COLLISION", collision.object_name)
        client.moveToPositionAsync(0, 0, -10, 3).join()

    time.sleep(1)

    # Log drone state
    pos = client.getMultirotorState().kinematics_estimated.position

    if start_time is None:
        start_time = time.time()
    elapsed = time.time() - start_time

    with open(log_file, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            f"{elapsed:.2f}",
            fault_active,
            f"{delay:.2f}",
            f"{pos.x_val:.2f}",
            f"{pos.y_val:.2f}",
            f"{pos.z_val:.2f}",
            "COLLISION" if collision.has_collided else "OK"
        ])

# ----------------------------
# Delay Fault Schedule Setup
# ----------------------------
start_time = time.time()
total_duration = 20  # Run loop for 20 seconds

# ----------------------------
# Initial Positioning
# ----------------------------
print("[INFO] Moving to (50, 99, -25, 2)...")
move_with_delay_fault(0, 0, -10, 3, fault_active=False, start_time=start_time)

# ----------------------------
# Main Loop with Fault Injection
# ----------------------------
print("[INFO] Entering automated movement loop with delay fault windows (5–10s and 15–20s).")

while time.time() - start_time < total_duration:

    # Define fault activation windows
    elapsed = time.time() - start_time
    fault_active = (2 <= elapsed <= 18)
    

    print(f"[DEBUG] Elapsed: {elapsed:.2f}s | Fault Active: {fault_active}")

    # Generate random target
    target_x = random.uniform(-12, -8)
    target_y = random.uniform(8, 12)
    target_z = -10
    velocity = 4

    # Execute movement with fault logic
    move_with_delay_fault(target_x, target_y, target_z, velocity, fault_active=fault_active, start_time=start_time)

    time.sleep(1)

# ----------------------------
# Landing and Cleanup
# ----------------------------
print("[INFO] Mission complete. Landing...")
client.landAsync().join()
client.armDisarm(False)
client.enableApiControl(False)
print("[INFO] Drone disarmed and API control released.")
