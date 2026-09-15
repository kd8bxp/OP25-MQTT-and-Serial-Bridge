#!/usr/bin/env python3
# Licensed under the MIT License
# Copyright (c) 2026 LeRoy F. Miller, KD8BXP
# 
# Please consider linking back to the original project repository if you use or modify this code.

import os
import re
import sys
import csv
import time
import serial

# --- Configuration ---
APPS_DIR = os.path.expanduser("~/op25/op25/gr-op25_repeater/apps")
FIFO_PATH = os.path.join(APPS_DIR, "stderr.2")
TSV_PATH = os.path.join(APPS_DIR, "tgid_tags.tsv")

# --- Serial Port Configuration ---
SERIAL_PORT = "/dev/ttyUSB0"      # Update to your actual ESP8266 serial handle
BAUD_RATE = 115200                 # Must match your ESP8266's Serial.begin() speed
TIMEOUT_WINDOW = 2.0             # Window to clear the matrix display after a transmission drops

LOG_PATTERN = re.compile(r"tg\((\d+)\),\s+freq\((\d+)\)")

def setup_serial():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"[INFO] Serial interface opened on {SERIAL_PORT} at {BAUD_RATE} baud.")
        return ser
    except serial.SerialException as e:
        print(f"[ERROR] Could not open serial interface {SERIAL_PORT}: {e}", file=sys.stderr)
        sys.exit(1)

def load_talkgroups():
    tg_map = {}
    if not os.path.exists(TSV_PATH):
        print(f"[WARNING] Talkgroup file {TSV_PATH} not found.", file=sys.stderr)
        return tg_map
    try:
        with open(TSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                if len(row) >= 2:
                    tg_map[row[0].strip()] = row[1].strip()
    except Exception as e:
        print(f"[ERROR] Failed reading talkgroup tags: {e}", file=sys.stderr)
    return tg_map

def main():
    talkgroup_dict = load_talkgroups()
    print(f"Loaded {len(talkgroup_dict)} talkgroups.")
    
    # Wait for pipe to exist
    if not os.path.exists(FIFO_PATH):
        print(f"[INFO] Waiting for OP25 named pipe: {FIFO_PATH}...")
        while not os.path.exists(FIFO_PATH):
            time.sleep(1)

    ser = setup_serial()
    last_tx_time = time.time()
    screen_cleared = True  # Start assumed cleared

    print("[INFO] Initialization complete. Streaming OP25 straight to hardware...")

    while True:
        try:
            with open(FIFO_PATH, "r") as fifo:
                for line in fifo:
                    clean_line = line.strip()
                    match = LOG_PATTERN.search(clean_line)
                    
                    if match:
                        tg_id = match.group(1)
                        tg_name = talkgroup_dict.get(tg_id, "Unknown")
                        
                        # Pack into a simple comma-separated protocol string ending with a newline
                        payload = f"{tg_id},{tg_name}\n"
                        
                        try:
                            ser.write(payload.encode('utf-8'))
                            print(f"[TX Data] {payload.strip()}")
                            last_tx_time = time.time()
                            screen_cleared = False
                        except serial.SerialException as se:
                            print(f"[ERROR] Serial write dropped: {se}. Reconnecting port...", file=sys.stderr)
                            ser.close()
                            time.sleep(2)
                            ser = setup_serial()

                    # Check for quiet timeouts between active pipe read frames
                    if not screen_cleared and (time.time() - last_tx_time > TIMEOUT_WINDOW):
                        try:
                            # Send a clear packet so the ESP8266 drops stale transmissions
                            ser.write(b"CLEAR\n")
                            print("[TX Clear] Sent screen timeout clear signal.")
                            screen_cleared = True
                        except serial.SerialException:
                            pass

        except (IOError, OSError):
            # Gracefully loop if OP25 recycles the pipe descriptor or hits a read break
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[INFO] Closing serial links and exiting.")
            break

    if ser:
        ser.close()

if __name__ == "__main__":
    main()
