## Project.

This is an attempt to make it dirt simple to display the Talk Group and The Name of the talk group on an external display.  In this case a D1 Mini, and 8 by 32 LED Matrix.   
My setup is an old Acer Netbook and the serial bridge works great with it, but the MQTT bridge has some issues with drop outs and latency.  
That being said MQTT did work, when it worked, I believe the issue was with my machine not the idea, so I have included it and you can test it your self - or use the Serial bridge and have the LED Matrix/D1 Mini plugged into a USB port on your OP25 rig.  
If you have OP25 already setup and running this really should be a simple drop the python script you want to use and modify the OP25start.sh up file.   
I have provided mine as an example. Your probably will be slightly different.  
The important thing to note here is the stderr.2 is now a PIPE it is no longer a "file". It doesn't store any logs or anything else - it takes the output from OP25 and PIPEs it to the python script of choice.  
The Other thing to note the python scripts use `tgid_tags.tsv` to get the names of the talk groups, if you have changed this file, you will need to change it in the python script.  

## Overview

There are four python scripts - All have been tested as best as I could (I'm using the `op25_serial_bridge2.py` script). The differences are:  
1) op25_mqtt_bridge.py - uses a dual topic (actually it uses three topics): The root topic and be set, then you'll on the D1 Mini (or any display for that matter) you'll subscribe to the root+/name and root+/talkgroup. There is no json or anything crazy - just text being sent.  Display it how you like. `D1 Mini Display v3` is included as an example.
2) op25_mqtt_bridge.py - uses one topic (the root topic), parses everything into a json string and sends it out to the MQTT broker. No Example is include on how to use this, but it should be pretty easy if you choose to use it.
3) op25_serial_bridge.py - Probably the easiest simplist thing to use - the only thing you may need to change in the script is the Uart port of your D1 Mini. The software for the D1 is included as an example `OP25 D1 Serial Display` - this works with either serial python stetch.  The only thing you may need to do on the computer is add yourself to the dialout user group. But I didn't need to do this, you might though.
4) ope25_serial_bridge2.py - the biggest difference is this version is not a blocking script, and the display timeout works better (not perfect). but better.

## OP25 MQTT Bridge

IN both scripts you will need to change your root topics, you may want to change your broker. And may need to change the file that holds the IDs of your talk groups. You may also want to change your broker client id to something else.  
On a modern machine these should work wonderful, but on my sluggish Atom Netbook I had a lot of disconnects and freezes, plus the whole latency issue.  
*Let me know if these work for you if you use them*

## OP25 Serial Bridge

The original version `op25_serial_bridge.py` the timeout windows is always between 20 to 26 seconds, changing the time does nothing.   So it is recommended that you use `op25_serial_bridge2.py` At least you change set a custom timeout - I actually found the 22.5 seconds seems to work well for my area.  
you may need to change the file of your IDs, and you may need to change the serial port of your D1 Mini (or other micro-controller).  
And as stated above you might need to add yourself to the dialout group.
I also had to install python3-serial.  `sudo apt install python3-serial`

## Linux LMDE5

These were tested on Linux Mint LMDE5 on Sep. 12 to Sep 15 2026.  Yes LMDE5 is old at this point, and not supported.  
I really can't offer support for anything newer because I'm running a old system. Thou it is believed that these should just work.  

I would love to know if these work for you as well as they do for me.  

## DISCLAIMER:

  This software is provided "as-is" for educational and hobbyist purposes. 
  No technical support, guarantees, or fitness for any specific use are provided.

## License & Attribution

This project is licensed under the MIT License. You are free to copy, modify, and distribute it however you like! 

**Attribution Request:** While not strictly legally required by the license text, if you use this code or build something cool with it, I would love it if you gave credit and linked back to this original repository: `https://github.com/kd8bxp/OP25-MQTT-and-Serial-Bridge`. Thanks!

Support & Warranty Disclaimer:
This project is shared entirely as a hobbyist endeavor for educational and experimental use. It is provided "as-is" without any warranty, explicit or implied, including but not limited to its fitness for any particular purpose. The author offers absolutely no technical support, debugging help, or maintenance guarantees. Use it entirely at your own risk.
