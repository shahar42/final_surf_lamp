# Surf Lamp - WiFi Setup Instructions

## Before You Start
**Register your device** using the Arduino ID printed on the lamp or box at: [Registration Page URL]

---

## WiFi Configuration - Choose Your Method

### **Option A: Mobile Phone (Recommended)**

1. **Open WiFi Settings** on your phone
2. **Connect to network:** `SurfLamp-Setup`
3. **Enter password:** `surf123456`
4. **Wait for popup** (appears automatically within 60 seconds)
   - If popup doesn't appear, open your browser and go to any website
5. **Select your home WiFi** from the list
6. **Enter your WiFi password**
7. **Tap Connect**
8. **Done!** Your lamp will connect to your home network

**Troubleshooting:**
- If popup doesn't appear after 2 minutes, disconnect and reconnect to `SurfLamp-Setup`
- Make sure your home WiFi is **2.4GHz** (5GHz is not supported)

---

### **Option B: Computer**

1. **Click WiFi icon** on your computer
2. **Connect to network:** `SurfLamp-Setup`
3. **Enter password:** `surf123456`
4. **Open web browser** (Chrome, Firefox, Edge, Safari)
5. **Type in address bar:** `http://192.168.4.1`
6. **Press Enter**
7. **Select your home WiFi** from the list
8. **Enter your WiFi password**
9. **Click Save**
10. **Done!** Your lamp will connect to your home network

**Troubleshooting:**
- If page doesn't load, check that you're still connected to `SurfLamp-Setup`
- Make sure your home WiFi is **2.4GHz** (5GHz is not supported)

---

## LED Status Indicators

| LED Color | Meaning |
|-----------|---------|
| 🟡 **Yellow blinking** | Configuration mode - waiting for WiFi setup |
| 🟢 **Green blinking** | Connecting to your WiFi |
| 🟣 **Purple blinking** | Checking location (1 second) |
| 🟢 **Green steady blink** | Connected - lamp is working |
| 🔴 **Red blinking** | WiFi connection lost |

---

## Important Notes

- **2.4GHz WiFi Required** - The lamp does not support 5GHz networks
- **WPA2 Security** - If your router uses WPA3-only, change it to WPA2 or Mixed mode
- **Signal Strength** - Place the lamp within good WiFi range during setup
- **Password Case Sensitive** - WiFi passwords are case-sensitive

---

## Common Issues

**Q: Lamp stays yellow and won't connect**
- A: Make sure you entered the correct WiFi password (case-sensitive)
- A: Check that your router's 2.4GHz band is enabled
- A: Move lamp closer to router

**Q: Lamp connects but shows orange LED**
- A: This means the server is unreachable. Wait 13 minutes for the next data fetch
- A: Check that the lamp can reach the internet

**Q: I moved to a new house**
- A: The lamp will detect the new location (purple LED) and automatically enter setup mode

---

**Need Help?**
Contact support: [support email/link]
