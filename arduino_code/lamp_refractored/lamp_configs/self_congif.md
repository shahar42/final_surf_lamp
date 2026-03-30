  // 1. Set your lamp's unique ID
  const int ARDUINO_ID = 8;  // Change to your lamp ID

  // 2. Set total LED count
  #define TOTAL_LEDS 88  // Change to your strip's total LED count

  // 3. Map your LED strips (bottom = start, top = end)
  // Wave Height Strip
  #define WAVE_HEIGHT_BOTTOM 5   // First LED of wave height strip
  #define WAVE_HEIGHT_TOP 27     // Last LED of wave height strip

  // Wave Period Strip  
  #define WAVE_PERIOD_BOTTOM 64  // First LED of wave period strip
  #define WAVE_PERIOD_TOP 87     // Last LED of wave period strip

  // Wind Speed Strip (MUST be reversed: BOTTOM > TOP)
  #define WIND_SPEED_BOTTOM 59   // First LED (status indicator)
  #define WIND_SPEED_TOP 34      // Last LED (wind direction)

  // 4. Optional: Adjust max ranges for your location
  #define MAX_WAVE_HEIGHT_METERS 3.0   // Max wave height to display
  #define MAX_WIND_SPEED_MPS 18.0      // Max wind speed to display
