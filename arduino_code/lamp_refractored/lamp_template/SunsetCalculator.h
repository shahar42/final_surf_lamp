#ifndef SUNSET_CALCULATOR_H
#define SUNSET_CALCULATOR_H

#include <Arduino.h>
#include <Preferences.h>
#include <Dusk2Dawn.h>

struct DateTime {
    int year;
    int month;
    int day;
    int hour;
    int minute;
    int second;
};

class SunsetCalculator {
private:
    Preferences preferences;
    Dusk2Dawn* location;

    float latitude;
    float longitude;
    int8_t tz_offset;

    int sunsetMinutesSinceMidnight;
    bool sunsetPlayedToday;
    int lastDayOfYear;

    DateTime currentTime;
    bool timeInitialized;

public:
    SunsetCalculator();
    ~SunsetCalculator();

    // Coordinate management
    void updateCoordinates(float lat, float lon, int8_t tz);
    bool hasCoordinates();

    // Time synchronization from HTTP Date header
    bool parseAndUpdateTime(String dateHeader);
    DateTime getCurrentTime();

    // Sunset calculation
    void calculateSunset();
    bool isSunsetTime();
    void markSunsetPlayed();

    // Utility
    int getDayOfYear(int year, int month, int day);
    int getSunsetMinutesSinceMidnight() const { return sunsetMinutesSinceMidnight; }
    bool wasSunsetPlayedToday() const { return sunsetPlayedToday; }

    // Debug functions removed to save flash memory
};

// Helper functions
int monthToInt(String month);

#endif
