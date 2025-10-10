# LED Mapping Notes - Single Strip Configuration

## Overview
This document records the LED index mapping for the **single continuous LED strip** that is physically wrapped to appear as 3 separate strips on the lamp.

---

## Hardware Configuration

**Date Mapped:** 10/10/25 

## LED Index Mapping

### Strip 1: Wave Height (Right Side)
- **Start Index:** 1
- **End Index:** 14
- **Total LEDs:** 14
- **Direction:**  bottom up


### Strip 2: Wave Period (Left Side)
- **Start Index:** 33
- **End Index:** 46
- **Total LEDs:** 13
- **Direction:** bottom up index 33 is the bottom of the strip


### Strip 3: Wind Speed (Center)
- **Start Index:** 30 (this indes is also the status led adn thats its only purpose)
- **End Index:** 17 (index 17 the wind direction led and thats its only purpose)
- **Total LEDs:** 13
- **Direction:** up bottom(30 is the bottom of the strip)



### Direction Reversal
If any strip section runs in reverse (bottom-up vs top-down):
- Strip 2(wind strip) runs in REVERSE direction from index 30 to 17


