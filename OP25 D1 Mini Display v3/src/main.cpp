/*
 * Licensed under the MIT License
 * Copyright (c) 2026 LeRoy F. Miller, KD8BXP
 * 
 * Please consider linking back to the original project repository if you use or modify this code.
 * DISCLAIMER: This software is provided "as-is" for educational and hobbyist purposes. 
 * No technical support, guarantees, or fitness for any specific use are provided.
 */

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MD_Parola.h> 
#include <MD_MAX72xx.h>

// --- WiFi Configuration ---
const char* ssid            = "";
const char* password        = "";
const char* mqtt_server_ip  = "35.156.188.238"; //broker.hivemq.com

// --- MQTT Topics ---
const char* topic_name      = "tiger/monster/string/name"; //match your topics don't use mine please
const char* topic_talkgroup = "tiger/monster/string/talkgroup"; 

// --- Hardware Settings ---
#define HARDWARE_TYPE MD_MAX72XX::FC16_HW
#define MAX_DEVICES 4  
#define CS_PIN      D8 

// Initialize Instances
WiFiClient espClient;
PubSubClient mqttClient(espClient); 
MD_Parola P = MD_Parola(HARDWARE_TYPE, CS_PIN, MAX_DEVICES);

// --- Fixed-Size Character Buffers ---
char currentName[64]      = {0};
char currentTalkgroup[64] = {0};
char scrollMessage[128]   = {0}; // Holds combined text string

// --- State Tracking Holding Variables ---
//char lastSeenTalkgroup[64] = {0};  // Holds the previous TG ID for duplication checks
char lastScrollMessage[128] = {0};

bool hasDisplayActive     = false;
unsigned long lastMessageTime = 0;
const unsigned long DISPLAY_TIMEOUT = 8000; //10000; //10 seconds //20000; // 20 seconds

// --- Forward Declarations ---
void setupWiFi();
void callback(char* topic, byte* payload, unsigned int length);
void reconnect();
void triggerInstantUpdate();
void clearDisplay();

void setup() {
    Serial.begin(115200);
    
    P.begin();
    P.setIntensity(0); 
    P.displayText(scrollMessage, PA_LEFT, 20, 0, PA_SCROLL_LEFT, PA_SCROLL_LEFT);

    clearDisplay();
    setupWiFi();
    
    mqttClient.setServer(mqtt_server_ip, 1883);
    mqttClient.setCallback(callback);
}

void loop() {
    if (!mqttClient.connected()) {
        reconnect();
    } else {
        mqttClient.loop();
    }

    if (hasDisplayActive) {
        if (P.displayAnimate()) {
            P.displayReset(); 
        }

        // Active traffic window check
        if (millis() - lastMessageTime >= DISPLAY_TIMEOUT) {
            clearDisplay(); // Wipes screen AND clears our lastSeenTalkgroup buffer
        }
    }
}

void setupWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);
    Serial.print("Connecting.");
    while (WiFi.status() != WL_CONNECTED) { 
        Serial.print(".");
        delay(500); 
    }
    Serial.println("Connected!!");
}

// --- Incoming Data Handler ---
/*void callback(char* topic, byte* payload, unsigned int length) {
    // Fix: Declared message as a proper text array buffer
    char message[64] = {0};
    unsigned int copyLength = (length > 63) ? 63 : length;
    memcpy(message, payload, copyLength);
    message[copyLength] = '\0';

    Serial.printf("Arrived [%s]: %s\n", topic, message);

    if (strcmp(topic, topic_talkgroup) == 0) {
        // --- DUPLICATION COMPARISON LOGIC ---
        if (strcmp(message, lastSeenTalkgroup) == 0) {
            // Same agency is transmitting again; push out timeline but skip reset blink
            lastMessageTime = millis();
            return; 
        }
        
        // Brand new talkgroup id received; update state tracking log
        strncpy(lastSeenTalkgroup, message, sizeof(lastSeenTalkgroup) - 1);
        
        memset(currentTalkgroup, 0, sizeof(currentTalkgroup));
        strncpy(currentTalkgroup, message, sizeof(currentTalkgroup) - 1);
        triggerInstantUpdate();
    } 
    else if (strcmp(topic, topic_name) == 0) {
        memset(currentName, 0, sizeof(currentName));
        strncpy(currentName, message, sizeof(currentName) - 1);
        triggerInstantUpdate();
    }
}*/

/*void callback(char* topic, byte* payload, unsigned int length) {
    unsigned int copyLength = (length > 63) ? 63 : length;

    if (strcmp(topic, topic_talkgroup) == 0) {
        // 1. Convert the raw payload bytes into a safe, null-terminated string
        char tempTG[64] = {0};
        memcpy(tempTG, payload, copyLength);
        tempTG[copyLength] = '\0';

        // 2. Compare it to our dedicated state tracker variable
        if (strcmp(tempTG, lastSeenTalkgroup) == 0) {
            // It's the same agency keying up again! Just kick the timer down the road
            lastMessageTime = millis();
            return; 
        }
        
        // 3. It's a brand new agency! Update our state tracking memory immediately
        strncpy(lastSeenTalkgroup, tempTG, sizeof(lastSeenTalkgroup) - 1);
        
        // 4. Update the global display buffer and trigger the instant screen reset
        memset(currentTalkgroup, 0, sizeof(currentTalkgroup));
        strncpy(currentTalkgroup, tempTG, sizeof(currentTalkgroup) - 1);
        triggerInstantUpdate();
    } 
    else if (strcmp(topic, topic_name) == 0) {
        // Handle the incoming name packet cleanly
        char tempName[64] = {0};
        memcpy(tempName, payload, copyLength);
        tempName[copyLength] = '\0';

        // Copy directly to the global name array
        memset(currentName, 0, sizeof(currentName));
        strncpy(currentName, tempName, sizeof(currentName) - 1);
        triggerInstantUpdate();
    }
    
}*/

void callback(char* topic, byte* payload, unsigned int length) {
    unsigned int copyLength = (length > 63) ? 63 : length;

    if (strcmp(topic, topic_talkgroup) == 0) {
        memset(currentTalkgroup, 0, sizeof(currentTalkgroup));
        memcpy(currentTalkgroup, payload, copyLength);
        currentTalkgroup[copyLength] = '\0';
        triggerInstantUpdate();
    } 
    else if (strcmp(topic, topic_name) == 0) {
        memset(currentName, 0, sizeof(currentName));
        memcpy(currentName, payload, copyLength);
        currentName[copyLength] = '\0';
        triggerInstantUpdate();
    }
}

/*void triggerInstantUpdate() {
    P.displayClear();
    memset(scrollMessage, 0, sizeof(scrollMessage));
    snprintf(scrollMessage, sizeof(scrollMessage), "%s %s", currentTalkgroup, currentName);
    P.displayReset();
    
    lastMessageTime = millis();
    hasDisplayActive = true;
}*/

void triggerInstantUpdate() {
    // 1. Construct the target message into a temporary buffer first
    char tempCombined[128] = {0};
    snprintf(tempCombined, sizeof(tempCombined), "%s %s", currentTalkgroup, currentName);
    Serial.println(tempCombined);
    
    // 2. Compare the whole thing against the last successfully drawn string
    if (strcmp(tempCombined, lastScrollMessage) == 0) {
        // Exact same transmission! Keep the timer alive but DO NOT touch or blink the screen.
        lastMessageTime = millis();
        return; 
    }
    
    // 3. It's brand new traffic! Save it to our history tracker immediately
    strncpy(lastScrollMessage, tempCombined, sizeof(lastScrollMessage) - 1);
    
    // 4. Stomp out the active display memory and physically clear the screen
    P.displayClear();
    memset(scrollMessage, 0, sizeof(scrollMessage));
    strcpy(scrollMessage, tempCombined);
    
    // 5. Instantly force the hardware engine to start the fresh marquee scroll
    P.displayReset();
    
    lastMessageTime = millis();
    hasDisplayActive = true;
}

void reconnect() {
    static unsigned long lastConnectAttempt = 0;
    if (millis() - lastConnectAttempt < 5000) return;
    lastConnectAttempt = millis();
    
    // Fix: Declared idBuffer as a proper text array buffer
    char idBuffer[32] = {0};
    snprintf(idBuffer, sizeof(idBuffer), "wemosd1-matrix-%04X", (unsigned int)random(0xFFFF));
    
    if (mqttClient.connect(idBuffer, "", "")) {
        mqttClient.subscribe(topic_name);
        mqttClient.subscribe(topic_talkgroup);
    }
}

/*void clearDisplay() {
    P.displayClear();
    memset(scrollMessage, 0, sizeof(scrollMessage));
    
    // Reset our duplicate channel memory filter tracker when display goes quiet
    memset(lastSeenTalkgroup, 0, sizeof(lastSeenTalkgroup));
    
    hasDisplayActive = false;
    Serial.println("Display cleared due to timeout window tracking.");
}*/

void clearDisplay() {
    P.displayClear();
    memset(scrollMessage, 0, sizeof(scrollMessage));
    
    // Clear out our combined history string memory when the display goes quiet
    memset(lastScrollMessage, 0, sizeof(lastScrollMessage));
    
    hasDisplayActive = false;
    Serial.println("Display cleared and history state strings zeroed out.");
}
