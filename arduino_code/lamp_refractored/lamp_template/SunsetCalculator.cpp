#include "SunsetCalculator.h"

SunsetCalculator::SunsetCalculator() {
    location = nullptr;
    latitude = 0.0;
    longitude = 0.0;
    tz_offset = 0;
    sunsetMinutesSinceMidnight = -1;
    sunsetPlayedToday = false;
    lastDayOfYear = 0;
    timeInitialized = false;

    // Load stored coordinates from flash
    preferences.begin("surf_lamp", true); // Read-only
    latitude = preferences.getFloat("latitude", 0.0);
    longitude = preferences.getFloat("longitude", 0.0);
    tz_offset = preferences.getChar("tz_offset", 0);
    preferences.end();

    if (latitude != 0.0 && longitude != 0.0) {
        location = new Dusk2Dawn(latitude, longitude, tz_offset);
        Serial.printf("📍 Loaded coordinates: lat=%.4f, lon=%.4f, tz=%d\n", latitude, longitude, tz_offset);
    }
}

SunsetCalculator::~SunsetCalculator() {
    if (location != nullptr) {
        delete location;
    }
}

void SunsetCalculator::updateCoordinates(float lat, float lon, int8_t tz) {
    // Check if coordinates changed
    bool changed = (abs(lat - latitude) > 0.0001 ||
                   abs(lon - longitude) > 0.0001 ||
                   tz != tz_offset);

    if (!changed) {
        return; // No update needed
    }

    // Store new coordinates
    latitude = lat;
    longitude = lon;
    tz_offset = tz;

    // Write to flash
    preferences.begin("surf_lamp", false); // Read-write
    preferences.putFloat("latitude", lat);
    preferences.putFloat("longitude", lon);
    preferences.putChar("tz_offset", tz);
    preferences.end();

    // Reinitialize Dusk2Dawn
    if (location != nullptr) {
        delete location;
    }
    location = new Dusk2Dawn(latitude, longitude, tz_offset);

    Serial.printf("📍 Coordinates updated: lat=%.4f, lon=%.4f, tz=%d\n", latitude, longitude, tz_offset);

    // Recalculate sunset
    if (timeInitialized) {
        calculateSunset();
    }
}

bool SunsetCalculator::hasCoordinates() {
    return (latitude != 0.0 && longitude != 0.0 && location != nullptr);
}

bool SunsetCalculator::parseAndUpdateTime(String dateHeader) {
    // Parse RFC 2822: "Sat, 20 Dec 2025 22:09:22 GMT"
    if (dateHeader.length() < 20) {
        Serial.println("⚠️ Invalid Date header format");
        return false;
    }

    try {
        int firstComma = dateHeader.indexOf(',');
        if (firstComma < 0) return false;

        // Extract day
        int dayStart = firstComma + 2;
        int dayEnd = dateHeader.indexOf(' ', dayStart);
        String dayStr = dateHeader.substring(dayStart, dayEnd);
        currentTime.day = dayStr.toInt();

        // Extract month
        int monthStart = dayEnd + 1;
        String monthStr = dateHeader.substring(monthStart, monthStart + 3);
        currentTime.month = monthToInt(monthStr);

        // Extract year
        int yearStart = monthStart + 4;
        currentTime.year = dateHeader.substring(yearStart, yearStart + 4).toInt();

        // Extract time HH:MM:SS
        int timeStart = yearStart + 5;
        currentTime.hour = dateHeader.substring(timeStart, timeStart + 2).toInt();
        currentTime.minute = dateHeader.substring(timeStart + 3, timeStart + 5).toInt();
        currentTime.second = dateHeader.substring(timeStart + 6, timeStart + 8).toInt();

        timeInitialized = true;

        Serial.printf("🕐 Time synced (GMT): %04d-%02d-%02d %02d:%02d:%02d\n",
                     currentTime.year, currentTime.month, currentTime.day,
                     currentTime.hour, currentTime.minute, currentTime.second);

        // Convert to local time for day-of-year detection
        // This ensures sunset flag resets at local midnight, not GMT midnight
        int localHour = currentTime.hour + tz_offset;
        int localDay = currentTime.day;
        int localMonth = currentTime.month;
        int localYear = currentTime.year;

        // Handle day rollover from hour adjustment
        if (localHour >= 24) {
            localHour -= 24;
            localDay++;
            // Simple day overflow (doesn't handle month/year rollover perfectly, but good enough)
            int daysInMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
            bool isLeap = (localYear % 4 == 0 && localYear % 100 != 0) || (localYear % 400 == 0);
            if (isLeap) daysInMonth[1] = 29;

            if (localDay > daysInMonth[localMonth - 1]) {
                localDay = 1;
                localMonth++;
                if (localMonth > 12) {
                    localMonth = 1;
                    localYear++;
                }
            }
        } else if (localHour < 0) {
            localHour += 24;
            localDay--;
            if (localDay < 1) {
                localMonth--;
                if (localMonth < 1) {
                    localMonth = 12;
                    localYear--;
                }
                int daysInMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
                bool isLeap = (localYear % 4 == 0 && localYear % 100 != 0) || (localYear % 400 == 0);
                if (isLeap) daysInMonth[1] = 29;
                localDay = daysInMonth[localMonth - 1];
            }
        }

        // Check if LOCAL day changed (reset sunset played flag)
        int currentLocalDay = getDayOfYear(localYear, localMonth, localDay);
        if (currentLocalDay != lastDayOfYear) {
            sunsetPlayedToday = false;
            lastDayOfYear = currentLocalDay;
            Serial.printf("🌅 New LOCAL day detected (day %d), sunset flag reset\n", currentLocalDay);
        }

        return true;

    } catch (...) {
        Serial.println("⚠️ Error parsing Date header");
        return false;
    }
}

DateTime SunsetCalculator::getCurrentTime() {
    return currentTime;
}

void SunsetCalculator::calculateSunset() {
    if (!hasCoordinates() || !timeInitialized) {
        return;
    }

    // Calculate sunset for current day (false = no DST adjustment, server handles DST)
    int minutes = location->sunset(currentTime.year, currentTime.month, currentTime.day, false);

    if (minutes < 0) {
        Serial.println("⚠️ No sunset today (polar region?)");
        sunsetMinutesSinceMidnight = -1;
        return;
    }

    sunsetMinutesSinceMidnight = minutes;

    int sunsetHour = minutes / 60;
    int sunsetMin = minutes % 60;

    Serial.printf("🌅 Sunset calculated: %02d:%02d (±15min trigger window)\n", sunsetHour, sunsetMin);
}

bool SunsetCalculator::isSunsetTime() {
    if (!timeInitialized || sunsetMinutesSinceMidnight < 0 || sunsetPlayedToday) {
        return false;
    }

    // Convert GMT to local time for sunset comparison
    int localHour = currentTime.hour + tz_offset;
    int localMinute = currentTime.minute;

    // Handle hour overflow/underflow
    if (localHour >= 24) {
        localHour -= 24;
    } else if (localHour < 0) {
        localHour += 24;
    }

    int currentLocalMinutes = localHour * 60 + localMinute;
    int windowStart = sunsetMinutesSinceMidnight - 15;
    int windowEnd = sunsetMinutesSinceMidnight + 15;

    bool inWindow = (currentLocalMinutes >= windowStart && currentLocalMinutes <= windowEnd);

    if (inWindow && !sunsetPlayedToday) {
        Serial.printf("🌅 SUNSET TRIGGER! Local time: %02d:%02d, Sunset: %02d:%02d\n",
                     localHour, localMinute,
                     sunsetMinutesSinceMidnight / 60, sunsetMinutesSinceMidnight % 60);
    }

    return inWindow;
}

void SunsetCalculator::markSunsetPlayed() {
    sunsetPlayedToday = true;
    Serial.println("🌅 Sunset animation played, flag set");
}

int SunsetCalculator::getDayOfYear(int year, int month, int day) {
    // Days in each month (non-leap year)
    int daysInMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};

    // Check for leap year
    bool isLeap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    if (isLeap) {
        daysInMonth[1] = 29;
    }

    int dayOfYear = day;
    for (int i = 0; i < month - 1; i++) {
        dayOfYear += daysInMonth[i];
    }

    return dayOfYear;
}

// printStatus() removed to save flash memory

// Helper function: Convert month name to integer
int monthToInt(String month) {
    if (month == "Jan") return 1;
    if (month == "Feb") return 2;
    if (month == "Mar") return 3;
    if (month == "Apr") return 4;
    if (month == "May") return 5;
    if (month == "Jun") return 6;
    if (month == "Jul") return 7;
    if (month == "Aug") return 8;
    if (month == "Sep") return 9;
    if (month == "Oct") return 10;
    if (month == "Nov") return 11;
    if (month == "Dec") return 12;
    return 1;
}
