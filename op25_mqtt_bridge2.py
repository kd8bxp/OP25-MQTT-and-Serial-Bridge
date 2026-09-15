#!/usr/bin/env python3
# Licensed under the MIT License
# Copyright (c) 2026 LeRoy F. Miller, KD8BXP
# 
# Please consider linking back to the original project repository if you use or modify this code.

import os
import re
import sys
import csv
import socket
import time
import json  # 100% native built-in module

# --- Configuration ---
APPS_DIR = os.path.expanduser("~/op25/op25/gr-op25_repeater/apps")
FIFO_PATH = os.path.join(APPS_DIR, "stderr.2")
TSV_PATH = os.path.join(APPS_DIR, "tgid_tags.tsv")  # Your correct tag file

MQTT_HOST = "broker.hivemq.com"
MQTT_PORT = 1883

UNIQUE_ID = "kd8bxp_desk_display" 
# Root Topic only - no sub-paths or wildcards needed!
# Change your topic, pluse don't use mine
ROOT_TOPIC = f"tiger/monster/string" #"{UNIQUE_ID}/op25"

LOG_PATTERN = re.compile(r"tg\((\d+)\),\s+freq\((\d+)\)")

def mqtt_connect():
#probably should change this too....
    client_id = f"kd8bxp_atom_{int(time.time())}"
    try:
        broker_ip = socket.gethostbyname(MQTT_HOST)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(7)
        s.connect((broker_ip, MQTT_PORT))
        
        packet = bytearray([0x10, 0x00, 0x00, 0x04, 0x4d, 0x51, 0x54, 0x54, 0x04, 0x02, 0x00, 0x3c])
        packet.extend(len(client_id).to_bytes(2, 'big'))
        packet.extend(client_id.encode('utf-8'))
        
        packet[1] = len(packet) - 2
        s.sendall(packet)
        res = s.recv(4)
        if res and res[0] == 0x20 and res[1] == 0x02 and res[3] == 0x00:
            s.settimeout(None)
            return s
    except Exception as e:
        print(f"HiveMQ Connection Error: {e}", file=sys.stderr)
    return None

def mqtt_publish(sock, topic, payload):
    try:
        t_bytes = topic.encode('utf-8')
        p_bytes = payload.encode('utf-8')
        
        packet = bytearray([0x30, 0x00])
        packet.extend(len(t_bytes).to_bytes(2, 'big'))
        packet.extend(t_bytes)
        packet.extend(p_bytes)
        
        packet[1] = len(packet) - 2
        sock.sendall(packet)
        return True
    except Exception:
        return False

def load_talkgroups():
    tg_map = {}
    if not os.path.exists(TSV_PATH):
        print(f"Warning: {TSV_PATH} not found.", file=sys.stderr)
        return tg_map
    try:
        with open(TSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                if len(row) >= 2:
                    tg_map[row[0].strip()] = row[1].strip()
        print(f"Successfully loaded {len(tg_map)} talkgroup aliases from TSV.")
    except Exception as e:
        print(f"Error reading TSV file: {e}", file=sys.stderr)
    return tg_map

def main():
    talkgroup_dict = load_talkgroups()
    print(f"Connecting to HiveMQ cloud broker at {MQTT_HOST}...")
    
    mq_sock = mqtt_connect()
    while not mq_sock:
        print("Broker unreachable. Retrying in 10 seconds...")
        time.sleep(10)
        mq_sock = mqtt_connect()
    print("Cloud Pipeline Connected successfully!")

    while True:
        try:
            with open(FIFO_PATH, "r") as fifo:
                for line in fifo:
                    clean_line = line.strip()
                    match = LOG_PATTERN.search(clean_line)
                    if match:
                        tg_id = match.group(1)
                        raw_freq = match.group(2)
                        freq_mhz = f"{float(raw_freq) / 1000000.0:.4f}"
                        tg_name = talkgroup_dict.get(tg_id, "Unknown Activity")
                        
                        # 📦 Pack everything cleanly into a Python dictionary
                        payload_data = {
                            "tg": int(tg_id),
                            "freq": freq_mhz,
                            "name": tg_name
                        }
                        
                        # Convert dictionary into a single serialized JSON string
                        json_payload = json.dumps(payload_data)
                        
                        # Publish everything at once to the root topic
                        if not mqtt_publish(mq_sock, ROOT_TOPIC, json_payload):
                            print("Cloud socket drop detected. Reconnecting...")
                            mq_sock = mqtt_connect()
                        else:
                            print(f"📡 Broadcasted JSON -> {json_payload}")
        except (IOError, OSError):
            time.sleep(1)
        except KeyboardInterrupt:
            break

    if mq_sock:
        mq_sock.close()

if __name__ == "__main__":
    main()
