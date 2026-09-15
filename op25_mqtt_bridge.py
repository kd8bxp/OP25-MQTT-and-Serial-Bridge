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

# --- Configuration ---
APPS_DIR = os.path.expanduser("~/op25/op25/gr-op25_repeater/apps")
FIFO_PATH = os.path.join(APPS_DIR, "stderr.2")
TSV_PATH = os.path.join(APPS_DIR, "tgid_tags.tsv") #"trunk.tsv")

# Where is your MQTT Broker? (e.g., your desktop PC, a Pi, or the ESP32 if running a broker)
MQTT_HOST = "broker.hivemq.com" #"192.168.1.50"  # <-- CHANGE THIS to your MQTT broker IP
MQTT_PORT = 1883
#Change your Topic please don't use mine
TOPIC_PREFIX = "tiger/monster/string" #"op25/scanner"

LOG_PATTERN = re.compile(r"tg\((\d+)\),\s+freq\((\d+)\)")

# --- Ultra-Lightweight Pure Python MQTT Packet Writer (Zero Dependencies) ---
#probably should change the client id as well
def mqtt_connect(client_id="op25_atom"):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((MQTT_HOST, MQTT_PORT))
        
        # Protocol name (MQTT) and flags
        packet = bytearray([0x10, 0x00, 0x00, 0x04, 0x4d, 0x51, 0x54, 0x54, 0x04, 0x02, 0x00, 0x3c])
        packet.extend(len(client_id).to_bytes(2, 'big'))
        packet.extend(client_id.encode('utf-8'))
        packet[1] = len(packet) - 2
        
        s.send(packet)
        res = s.recv(4) # Expecting CONNACK
        if res and res[0] == 0x20 and res[3] == 0x00:
            s.settimeout(None)
            return s
    except Exception as e:
        print(f"MQTT Connect Error: {e}", file=sys.stderr)
    return None

def mqtt_publish(sock, topic, payload):
    try:
        t_bytes = topic.encode('utf-8')
        p_bytes = payload.encode('utf-8')
        
        packet = bytearray([0x30, 0x00]) # Fixed header for QoS 0
        packet.extend(len(t_bytes).to_bytes(2, 'big'))
        packet.extend(t_bytes)
        packet.extend(p_bytes)
        
        # Calculate remaining length
        rem_len = len(packet) - 2
        packet[1] = rem_len
        
        sock.sendall(packet)
        return True
    except Exception:
        return False

def load_talkgroups():
    tg_map = {}
    if not os.path.exists(TSV_PATH):
        return tg_map
    try:
        with open(TSV_PATH, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for row in reader:
                if not row or row[0].startswith("#"):
                    continue
                if len(row) >= 2:
                    tg_map[row[0].strip()] = row[1].strip()
    except Exception:
        pass
    return tg_map

def main():
    talkgroup_dict = load_talkgroups()
    print(f"Loaded {len(talkgroup_dict)} talkgroups. Connecting to MQTT at {MQTT_HOST}...")
    
    mq_sock = mqtt_connect()
    while not mq_sock:
        time.sleep(5)
        mq_sock = mqtt_connect()
    print("Connected to MQTT Broker successfully!")

    while True:
        try:
            #pipe_fd = os.open(FIFO_PATH, os.O_RDONLY | os.O_NONBLOCK)
            with open(FIFO_PATH, "r") as fifo:
            #with os.fdopen(pipe_fd, "r") as fifo:
                for line in fifo:
                    clean_line = line.strip()
                    match = LOG_PATTERN.search(clean_line)
                    if match:
                        tg_id = match.group(1)
                        raw_freq = match.group(2)
                        freq_mhz = f"{float(raw_freq) / 1000000.0:.4f}"
                        tg_name = talkgroup_dict.get(tg_id, "Unknown")
                        
                        # Send directly over raw socket to MQTT
                        if not mqtt_publish(mq_sock, f"{TOPIC_PREFIX}/talkgroup", tg_id):
                            print("Connection lost. Reconnecting...")
                            mq_sock = mqtt_connect()
                        else:
                            mqtt_publish(mq_sock, f"{TOPIC_PREFIX}/frequency", freq_mhz)
                            mqtt_publish(mq_sock, f"{TOPIC_PREFIX}/name", tg_name)
        except (IOError, OSError):
            time.sleep(1)
        except KeyboardInterrupt:
            break

    if mq_sock:
        mq_sock.close()

if __name__ == "__main__":
    main()
