# Surf Lamp Shipping Preparation Guide

This document outlines the essential procedures for preparing a Surf Lamp device for production, quality assurance, and shipping to end-users.

## 1. Firmware Preparation for Production

Before flashing the firmware onto production units, several modifications must be made to the source code to ensure each device is unique and secure.

### 1.1. Assign a Unique `ARDUINO_ID`

This is the most critical step. Each device **must** have a unique ID that is registered in the backend database. This ID is the link between the physical hardware and the user's account.

1.  **Open the firmware sketch:** `arduinomain_lamp.ino`
2.  **Locate the ID definition line:**
    ```cpp
    const int ARDUINO_ID = 4433; // ✨ CHANGE THIS for each Arduino device
    ```
3.  **Assign and Record:** Change the integer value to a new, unique ID. This ID should be recorded and associated with the device's serial number in a production database.

### 1.2. Disable Serial Debugging (Optional)

For production units, you may want to disable the extensive serial logging to slightly improve performance and hide internal logic.

*   **Action:** Comment out or remove `Serial.print` statements throughout the code, especially those that print detailed surf data or system status.
*   **Recommendation:** Keep critical error messages (e.g., connection failures) to aid in potential returns or repairs.

### 1.3. Verify Server Discovery URLs

Ensure the `ServerDiscovery.h` file points to the correct production discovery URLs.

```cpp
// In ServerDiscovery.h
const char* discovery_urls[2] = {
    "https://your-github-username.github.io/your-repo/discovery-config/config.json",
    "https://raw.githubusercontent.com/your-github-username/your-repo/master/discovery-config/config.json"
};
```

## 2. Pre-Shipping Quality Assurance (QA) Checklist

Each unit must pass the following QA checks before final testing.

**Technician:** ________________________
**Device Serial Number:** ______________
**Assigned `ARDUINO_ID`:** ______________

| Check # | Item                                     | Pass/Fail | Notes                                       |
| :------ | :--------------------------------------- | :-------- | :------------------------------------------ |
| 1       | **Visual Inspection**                    |           | Check for clean solder joints, no shorts.   |
| 2       | **Connector Integrity**                  |           | Ensure all connectors are secure.           |
| 3       | **Power Supply Test**                    |           | Connect power, check for stable voltage.    |
| 4       | **Firmware Flashed**                     |           | Verify the correct production firmware version. |
| 5       | **Unique ID Verified**                   |           | Confirm the flashed `ARDUINO_ID` matches the record. |
| 6       | **Enclosure Fit**                        |           | Check that the PCB fits correctly in its case. |

## 3. Final Testing Protocol for Manufactured Units

This protocol must be performed on every unit after it passes the initial QA checklist.

### Step 1: Power On and LED Test

1.  Power on the device.
2.  The device will automatically run an LED test sequence on boot (rainbow pattern).
3.  **Expected Result:** All LEDs on all three strips should light up and cycle through colors smoothly. This verifies that the LED hardware is working correctly.

### Step 2: Wi-Fi Configuration Test

1.  The device will fail to find a known network and start its own Access Point (AP).
2.  Using a test phone or computer, connect to the `SurfLamp-Setup` Wi-Fi network (password: `surf123456`).
3.  **Expected Result:** A captive portal should open automatically. This verifies the Wi-Fi configuration server is working.

### Step 3: Connect to Test Network

1.  In the captive portal, enter the credentials for a dedicated **test Wi-Fi network**.
2.  The device will reboot and attempt to connect.
3.  **Expected Result:** The device connects to the test network and gets an IP address. The status LED should turn from Red to Blue (connecting) to Green (connected).

### Step 4: Data Fetch and Display Test

1.  Once connected, the device will attempt to fetch data from the server.
2.  To speed up the test, use a web browser on the same test network to access the device's manual fetch endpoint: `http://<device-ip>/api/fetch`.
3.  **Expected Result:** The device's LEDs should update to display the fetched surf data. This verifies the entire data pipeline from server to device.

## 4. Customer Setup Instruction Template

A small, user-friendly instruction card should be included in the packaging.

---

### **Quick Start Guide: Your Surf Lamp**

**1. Power On**
   Plug in your Surf Lamp. The LEDs will run a quick test pattern.

**2. Connect to Wi-Fi**
   *   On your phone or computer, find and connect to the Wi-Fi network named `SurfLamp-Setup`.
   *   Password: `surf123456`

**3. Configure Your Network**
   *   A setup page should open automatically. If not, open a web browser and go to `http://192.168.4.1`.
   *   Select your home Wi-Fi network, enter the password, and click "Connect".

**4. All Set!**
   Your lamp will reboot and connect to your network. Once connected, it will automatically download the latest surf conditions. Enjoy the waves!

---

## 5. Warranty and Support Considerations

*   **Standard Warranty:** A standard 1-year limited warranty covering manufacturing defects is recommended.
*   **Support Channel:** Establish a clear support channel (e.g., email address, support website) for customers who experience issues.
*   **Common Issues:** The most common support request will likely be related to Wi-Fi setup. Ensure the support team is familiar with the process and common pitfalls (e.g., incorrect password, 5GHz vs. 2.4GHz networks).
*   **Device Identification:** When a customer requests support, it is crucial to ask for the `ARDUINO_ID` or serial number to look up the device in the backend and diagnose issues.
