/*
 * Licensed under the MIT License
 * Copyright (c) 2026 LeRoy F. Miller, KD8BXP
 * 
 * Please consider linking back to the original project repository if you use or modify this code.
 * DISCLAIMER: This software is provided "as-is" for educational and hobbyist purposes. 
 * No technical support, guarantees, or fitness for any specific use are provided.
 */

#include <Arduino.h>
#include <SPI.h>
#include <MD_Parola.h> 
#include <MD_MAX72xx.h>

// --- Hardware Settings ---
#define HARDWARE_TYPE MD_MAX72XX::FC16_HW
#define MAX_DEVICES 4  
#define CS_PIN      D8 

// Initialize Matrix Engine
MD_Parola P = MD_Parola(HARDWARE_TYPE, CS_PIN, MAX_DEVICES);

// --- Fixed-Size Character Buffers ---
char scrollMessage[128]     = {0}; // Active hardware rendering target
char lastScrollMessage[128]  = {0}; // State tracking variable to block stutters

// --- State Variables ---
bool hasDisplayActive = false;

// --- Forward Declarations ---
void parseSerialInput(String input);
void updateDisplay(const char* tg, const char* name);
void clearDisplay();

void setup() {
    // Open hardware serial link at 115200 to match the Atom netbook transmission
    Serial.begin(115200);
    
    P.begin();
    P.setIntensity(0); // Set brightness (0-15)
    P.displayText(scrollMessage, PA_LEFT, 20, 0, PA_SCROLL_LEFT, PA_SCROLL_LEFT);

    clearDisplay();
    Serial.println("\n[SYSTEM] ESP8266 Serial Receiver Online. Ready for data...");
}

void loop() {
    // Process incoming serial data using non-blocking newline delimiter tracking
    if (Serial.available() > 0) {
        String rawInput = Serial.readStringUntil('\n');
        rawInput.trim(); // Strip trailing carriage returns or whitespaces
        
        if (rawInput.length() > 0) {
            parseSerialInput(rawInput);
        }
    }

    // Drive the marquee animation loop if active
    if (hasDisplayActive) {
        if (P.displayAnimate()) {
            P.displayReset(); 
        }
    }
}

// --- Comma Delimited String Parser ---
void parseSerialInput(String input) {
    // 1. Check if the Python script explicitly sent a dead-air clear directive
    if (input == "CLEAR") {
        clearDisplay();
        return;
    }

    // 2. Parse out the comma-separated protocol string: "TG,Name"
    int commaIndex = input.indexOf(',');
    if (commaIndex == -1) {
        return; // Malformed packet fallback
    }

    String tgPart   = input.substring(0, commaIndex);
    String namePart = input.substring(commaIndex + 1);

    // 3. Forward extracted text segments directly to update router
    updateDisplay(tgPart.c_str(), namePart.c_str());
}

// --- Screen Upkeep & Stutter Filter Logic ---
void updateDisplay(const char* tg, const char* name) {
    // 1. Construct the target display layout into a temporary memory buffer
    char tempCombined[128] = {0};
    snprintf(tempCombined, sizeof(tempCombined), "%s %s", tg, name);
    
    // 2. DUPLICATION FILTER: Verify if this is the exact same channel activity running
    if (strcmp(tempCombined, lastScrollMessage) == 0) {
        // Same agency talking! Do not reset or blink the matrix screen.
        return; 
    }
    
    // 3. New traffic confirmed! Commit string to historical filter array
    strncpy(lastScrollMessage, tempCombined, sizeof(lastScrollMessage) - 1);
    
    // 4. Stomp out the active display memory and push string out to physical hardware
    P.displayClear();
    memset(scrollMessage, 0, sizeof(scrollMessage));
    strcpy(scrollMessage, tempCombined);
    
    // 5. Instantly flash-initialize the Parola marquee engine
    P.displayReset();
    hasDisplayActive = true;
    
    Serial.print("[DISPLAY ENGAGED]: ");
    Serial.println(scrollMessage);
}

void clearDisplay() {
    P.displayClear();
    memset(scrollMessage, 0, sizeof(scrollMessage));
    
    // Clear out historical channel cache so next key-up renders instantly
    memset(lastScrollMessage, 0, sizeof(lastScrollMessage));
    
    hasDisplayActive = false;
    Serial.println("[SYSTEM] Display cleared and cache state zeroed.");
}

