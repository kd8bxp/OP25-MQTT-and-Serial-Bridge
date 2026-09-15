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
SERIAL_PORT = "/dev/ttyUSB0"      
BAUD_RATE = 115200                 
TIMEOUT_WINDOW = 22.5             # This will now accurately trigger at exactly 10 seconds

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
    
    if not os.path.exists(FIFO_PATH):
        print(f"[INFO] Waiting for OP25 named pipe: {FIFO_PATH}...")
        while not os.path.exists(FIFO_PATH):
            time.sleep(1)

    ser = setup_serial()
    last_tx_time = time.time()
    screen_cleared = True  

    print("[INFO] Initialization complete. Streaming non-blocking data...")

    # Open the pipe using low-level non-blocking OS flags
    try:
        pipe_fd = os.open(FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
    except Exception as e:
        print(f"[ERROR] Failed to open pipe: {e}", file=sys.stderr)
        sys.exit(1)

    buffer = ""

    while True:
        try:
            # 1. Read raw bytes from the non-blocking pipe descriptor
            try:
                ready_data = os.read(pipe_fd, 4096).decode('utf-8', errors='ignore')
            except (BlockingIOError, OSError):
                ready_data = "" # No data available right now, which is fine!

            if ready_data:
                buffer += ready_data
                # Process complete lines from our text accumulator buffer
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    clean_line = line.strip()
                    match = LOG_PATTERN.search(clean_line)
                    
                    if match:
                        tg_id = match.group(1)
                        tg_name = talkgroup_dict.get(tg_id, "Unknown")
                        payload = f"{tg_id},{tg_name}\n"
                        
                        try:
                            ser.write(payload.encode('utf-8'))
                            print(f"[TX Data] {payload.strip()}")
                            last_tx_time = time.time()
                            screen_cleared = False
                        except serial.SerialException as se:
                            print(f"[ERROR] Serial write dropped: {se}", file=sys.stderr)

            # 2. FIXED: This now runs entirely independent of whether a new line arrived!
            if not screen_cleared and (time.time() - last_tx_time > TIMEOUT_WINDOW):
                try:
                    ser.write(b"CLEAR\n")
                    print(f"[TX Clear] Sent screen timeout clear signal after {TIMEOUT_WINDOW}s.")
                    screen_cleared = True
                except serial.SerialException:
                    pass

            # Small nap to keep the single-core Atom CPU from pinning at 100% loop execution
            time.sleep(0.1)

        except KeyboardInterrupt:
            print("\n[INFO] Closing links and exiting.")
            break
        except Exception as e:
            print(f"[CRITICAL ERROR] Loop break: {e}", file=sys.stderr)
            time.sleep(1)

    os.close(pipe_fd)
    ser.close()

if __name__ == "__main__":
    main()
