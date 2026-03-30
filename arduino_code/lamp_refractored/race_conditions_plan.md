Race Condition Analysis                                                                                                                                                                
                                                                                                                                                                                         
  I've reviewed the dual-core architecture. Here's my analysis:                                                                                                                          
                                                                                                                                                                                         
  Architecture Summary                                                                                                                                                                   
                                                                                                                                                                                         
  - Core 0: Network Secretary - HTTP fetches, time parsing, sunset calculation                                                                                                           
  - Core 1: LED Artist - loop(), LED updates, web server handlers                                                                                                                        
                                                                                                                                                                                         
  ---                                                                                                                                                                                    
  CRITICAL Race Conditions                                                                                                                                                               
                                                                                                                                                                                         
  1. lastSurfData struct (HIGH RISK)                                                                                                                                                     
                                                                                                                                                                                         
  Location: SurfState.h:34-80, accessed from multiple files                                                                                                                              
  ┌───────────────────────────────────┬───────────┬──────────────────────────────────────┐                                                                                               
  │               Field               │   Type    │               Problem                │                                                                                               
  ├───────────────────────────────────┼───────────┼──────────────────────────────────────┤                                                                                               
  │ waveHeight, wavePeriod, windSpeed │ float/int │ Torn reads possible                  │                                                                                               
  ├───────────────────────────────────┼───────────┼──────────────────────────────────────┤                                                                                               
  │ theme                             │ String    │ UNDEFINED BEHAVIOR - not thread-safe │                                                                                               
  ├───────────────────────────────────┼───────────┼──────────────────────────────────────┤                                                                                               
  │ All error flags                   │ bool      │ Non-atomic writes                    │                                                                                               
  └───────────────────────────────────┴───────────┴──────────────────────────────────────┘                                                                                               
  How it happens:                                                                                                                                                                        
  - Core 0 writes via processSurfData() (WebServerHandler.cpp:303-330)                                                                                                                   
  - Core 1 reads via updateSurfDisplay(), updateBlinkingAnimation() (LedController.cpp)                                                                                                  
                                                                                                                                                                                         
  Symptom: Core 1 could read waveHeight from old data while windSpeed is from new data, or crash on String access.                                                                       
                                                                                                                                                                                         
  ---                                                                                                                                                                                    
  2. sunsetCalc instance (MEDIUM-HIGH RISK)                                                                                                                                              
                                                                                                                                                                                         
  Location: DualCoreManager.cpp:117-123                                                                                                                                                  
                                                                                                                                                                                         
  - Core 0 calls: updateCoordinates(), calculateSunset(), getCurrentTime()                                                                                                               
  - Core 1 calls: isSunsetTime(), markSunsetPlayed()                                                                                                                                     
                                                                                                                                                                                         
  The comment at line 116 claims "safe because only written by Core 0" but markSunsetPlayed() writes from Core 1.                                                                        
                                                                                                                                                                                         
  ---                                                                                                                                                                                    
  3. wifiJustReconnected (MEDIUM RISK)                                                                                                                                                   
                                                                                                                                                                                         
  Location: WiFiHandler.h:109                                                                                                                                                            
                                                                                                                                                                                         
  Declared as plain bool, not std::atomic<bool>:                                                                                                                                         
  - Core 0 reads/writes in networkSecretaryTask (DualCoreManager.cpp:48-53)                                                                                                              
  - WiFi event callbacks (potentially from different core) write it                                                                                                                      
                                                                                                                                                                                         
  ---                                                                                                                                                                                    
  4. lastDataFetch (MEDIUM RISK)                                                                                                                                                         
                                                                                                                                                                                         
  Location: WebServerHandler.cpp:14                                                                                                                                                      
                                                                                                                                                                                         
  Declared as plain unsigned long:                                                                                                                                                       
  - Core 0 writes (DualCoreManager.cpp:93)                                                                                                                                               
  - Core 1 reads in loop() for staleness check (lamp_template.ino:180)                                                                                                                   
                                                                                                                                                                                         
  ---                                                                                                                                                                                    
  Properly Protected (Good!)                                                                                                                                                             
                                                                                                                                                                                         
  - All DualCore:: atomic variables                                                                                                                                                      
  - lastSurfData.needsDisplayUpdate (atomic)                                                                                                                                             
  - FETCH_INTERVAL_MS (atomic)                                                                                                                                                           
                                                                                                                                                                                         
  ---                                                                                                                                                                                    
  Recommended Fixes                                                                                                                                                                      
                                                                                                                                                                                         
  1. For lastSurfData: Use a mutex or double-buffer pattern. The atomic needsDisplayUpdate flag should gate access to a fully-written copy.                                              
  2. For theme String: Either use a fixed char array, or copy to a local variable under mutex protection.                                                                                
  3. For wifiJustReconnected: Change to std::atomic<bool>.                                                                                                                               
  4. For lastDataFetch: Change to std::atomic<unsigned long>.                                                                                                                            
  5. For sunsetCalc: Add mutex protection or make internal state atomic.                                                                                                                 
                                                                                                                                                                                         
  Want me to implement any of these fixes?         
