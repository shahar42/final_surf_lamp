# Surf Lamp System Communication Diagrams

## 1. Lamp Startup Sequence

```mermaid
sequenceDiagram
    participant Arduino as ESP32 Arduino
    participant Discovery as Discovery Service<br/>(Vercel/GitHub)
    participant Server as Flask Server<br/>(Render)
    participant DB as PostgreSQL<br/>(Supabase)
    participant Redis as Redis<br/>(Optional)

    Note over Arduino: Power On / Restart
    Arduino->>Arduino: Initialize LEDs, WiFi
    Arduino->>Arduino: Display Arduino ID (5s)
    Arduino->>Arduino: Play startup animation

    alt WiFi Connected
        Arduino->>Discovery: GET /config.json
        Discovery-->>Arduino: {"api_server": "surf-lamp-server.onrender.com"}
        
        Note over Arduino: Apply startup jitter (prevent thundering herd)
        Arduino->>Arduino: delay(jitter based on ARDUINO_ID)
        
        Arduino->>Server: GET /api/arduino/{id}/surf-data-v3
        Server->>DB: Query arduinos + locations + users
        DB-->>Server: Arduino config, location data, user settings
        
        alt Redis Available
            Server->>Redis: HSET lamp_heartbeats {arduino_id: timestamp}
        end
        
        Server-->>Arduino: Binary response (26 bytes):<br/>wave_height, wave_period, wind_speed,<br/>lat/lng, thresholds, settings
        
        Arduino->>Arduino: Parse binary data
        Arduino->>Arduino: Update LED display
        Arduino->>Arduino: Start dual-core tasks
    else WiFi Not Connected
        Arduino->>Arduino: Enter config portal mode
    end
```

---

## 2. Normal Operation (Polling Loop)

```mermaid
sequenceDiagram
    participant Core0 as ESP32 Core 0<br/>(Network Secretary)
    participant Core1 as ESP32 Core 1<br/>(LED Artist)
    participant Server as Flask Server<br/>(Render)
    participant DB as PostgreSQL<br/>(Supabase)
    participant Redis as Redis<br/>(Optional)
    participant Processor as Background Processor<br/>(Render)
    participant WeatherAPI as Weather APIs<br/>(Stormglass/OpenMeteo)

    rect rgb(240, 248, 255)
        Note over Processor,WeatherAPI: Background Processor Loop (every 15 min)
        Processor->>DB: Get location API configs
        DB-->>Processor: Location configs with API URLs
        
        loop For each location
            Processor->>WeatherAPI: Fetch wave data
            WeatherAPI-->>Processor: wave_height, wave_period
            Processor->>WeatherAPI: Fetch wind data
            WeatherAPI-->>Processor: wind_speed, wind_direction
            
            Processor->>DB: UPDATE locations SET wave_height_m=X,<br/>wind_speed_mps=Y WHERE location=Z
        end
        
        Processor->>DB: UPDATE processor_heartbeat
    end

    rect rgb(255, 250, 240)
        Note over Core0,Redis: Arduino Polling Loop (every 13 min)
        Core0->>Server: GET /api/arduino/{id}/surf-data-v3
        
        Server->>DB: SELECT * FROM arduinos<br/>JOIN locations JOIN users
        DB-->>Server: Cached surf conditions +<br/>user settings + thresholds
        
        alt Physical ESP32 Device
            alt Redis Available
                Server->>Redis: HSET arduino:last_seen {id: timestamp}<br/>SETBIT arduino:online_bitmap
            else Redis Unavailable
                Note over Server: Skip DB write to protect database
            end
        end
        
        Server-->>Core0: Binary response (26 bytes)
        
        Core0->>Core0: Parse binary data, update atomic variables
        Core0-->>Core1: needsDisplayUpdate.store(true)
        Core1->>Core1: Update LED display (200 FPS)
        
        alt Data is stale (>30 min)
            Core1->>Core1: Blink orange status LED
        else Data is fresh
            Core1->>Core1: Blink green status LED
        end
    end
```

---

## Key Components Summary

| Component | Role | Technology |
|-----------|------|------------|
| **ESP32 Arduino** | Display device, polls server every 13 min | C++, FreeRTOS dual-core |
| **Discovery Service** | Returns current API server URL | Vercel/GitHub static JSON |
| **Flask Server** | API gateway, serves data to Arduinos | Python Flask, Gunicorn |
| **Background Processor** | Fetches weather data, updates DB | Python, SQLAlchemy |
| **PostgreSQL** | Persistent storage | Supabase |
| **Redis** | High-performance heartbeat storage | Optional, reduces DB writes |

---

## Data Flow Notes

1. **Separation of concerns**: Processor fetches from weather APIs → DB. Arduinos fetch from Server → DB.
2. **Location-driven**: Data is stored per-location, multiple lamps can share the same location's data.
3. **Binary protocol (v3)**: 94% smaller than JSON (26 bytes vs ~450 bytes).
4. **Thundering herd prevention**: Startup jitter based on `ARDUINO_ID` prevents all lamps hitting server simultaneously after power outage.
