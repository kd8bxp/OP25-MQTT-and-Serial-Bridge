#!/bin/bash

# 1. Move straight to your OP25 execution directory
cd ~/op25/op25/gr-op25_repeater/apps

# 2. Safety Net: If stderr.2 is a physical file or missing, change it to a memory pipe (FIFO)
if [ ! -p stderr.2 ]; then
    rm -f stderr.2
    mkfifo stderr.2
fi

# 3. Fire up your Python MQTT bridge script silently in the background (&)
#python3 op25_mqtt_bridge.py >/dev/null 2>&1 &
#python3 op25_serial_bridge.py >/dev/null 2>&1 &
python3 op25_serial_bridge2.py >/dev/null 2>&1 &

# 4. Grab the background Python process ID (PID) so we can clean it up later
BRIDGE_PID=$!

# 5. Launch OP25 with your exact radio tuning parameters
./rx.py --nocrypt --args "rtl" --gains 'lna:36' -S 960000 -X -q 3 -o 28000 -v 1 -2 -V -U -T trunk.tsv 2> stderr.2

# 6. Automated Cleanup: When you natively exit the OP25 screen (-X mode),
# this line instantly kills the background Python thread so it doesn't leak memory.
kill $BRIDGE_PID 2>/dev/null

