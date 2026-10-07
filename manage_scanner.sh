#!/bin/bash

# Move straight to your OP25 execution directory
cd ~/op25/op25/gr-op25_repeater/apps

# Safety Net: If stderr.2 is a physical file or missing, change it to a memory pipe (FIFO)
if [ ! -p stderr.2 ]; then
    rm -f stderr.2
    mkfifo stderr.2
fi

# Check if the tmux session is already running
tmux has-session -t scanner 2>/dev/null

if [ $? != 0 ]; then
    # Create a new, detached tmux session named "scanner" and start with the bridge view
    tmux new-session -d -s scanner -n "Bridge"
    
    # Send the auto-restarting Python bridge process to window 0 ("Bridge")
    # This keeps logs completely separated from the main OP25 screen!
    tmux send-keys -t scanner:Bridge "while true; do echo '[STARTING BRIDGE...]'; python3 op25_serial_bridge2.py; echo '[CRASH DETECTED] Restarting bridge in 2 seconds...'; sleep 2; done" C-m

    # Create a second tmux window specifically for the OP25 screen
    tmux new-window -t scanner -n "OP25"

    # Launch OP25 inside the second window. When OP25 closes, kill the entire tmux session.
    OP25_CMD="./rx.py --nocrypt --args 'rtl' --gains 'lna:36' -S 960000 -X -q 3 -o 28000 -v 1 -2 -V -U -T trunk.tsv 2> stderr.2"
    tmux send-keys -t scanner:OP25 "$OP25_CMD; tmux kill-session -t scanner" C-m

    # Default focus to the OP25 terminal display so it renders immediately on attach
    tmux select-window -t scanner:OP25
fi

# Attach your local terminal screen directly into the live tmux environment
tmux attach-session -t scanner
