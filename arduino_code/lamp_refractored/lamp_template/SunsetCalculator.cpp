#include "SunsetCalculator.h"

// ==================== CONSTRUCTOR HELPERS ====================

void SunsetCalculator::initializeDefaults() {
    latitude = 0.0;
    longitude = 0.0;
    tz_offset = 0;
    sunsetMinutesSinceMidnight = -1;
    sunsetPlayedToday = false;
    lastDayOfYear = 0;
    timeInitialized = false;
}

void SunsetCalculator::loadCoordinatesFromFlash() {
    preferences.begin("surf_lamp", true);  // Read-only
    latitude = preferences.getFloat("latitude", 0.0);
    longitude = preferences.getFloat("longitude", 0.0);
    tz_offset = preferences.getChar("tz_offset", 0);
    preferences.end();
}

void SunsetCalculator::initializeSunriseCalculator() {
    if (latitude != 0.0 && longitude != 0.0) {
        Serial.printf("📍 Loaded coordinates: lat=%.4f, lon=%.4f, tz=%d\n", latitude, longitude, tz_offset);
    }
}

// ==================== CONSTRUCTOR ====================

SunsetCalculator::SunsetCalculator() {
    mutex = xSemaphoreCreateMutex();
    initializeDefaults();
    loadCoordinatesFromFlash();
    initializeSunriseCalculator();
}

SunsetCalculator::~SunsetCalculator() {
    // No dynamic memory to clean up
}

void SunsetCalculator::updateCoordinates(float lat, float lon, int8_t tz) {
    xSemaphoreTake(mutex, portMAX_DELAY);
    
    // Check if coordinates changed
    bool changed = (abs(lat - latitude) > 0.0001 ||
                   abs(lon - longitude) > 0.0001 ||
                   tz != tz_offset);

    if (!changed) {
        xSemaphoreGive(mutex);
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

    Serial.printf("📍 Coordinates updated: lat=%.4f, lon=%.4f, tz=%d\n", latitude, longitude, tz_offset);
    
    bool shouldRecalc = timeInitialized;
    xSemaphoreGive(mutex);

    // Recalculate sunset (call outside lock to avoid deadlock/recursion)
    if (shouldRecalc) {
        calculateSunset();
    }
}

bool SunsetCalculator::hasCoordinates() {
    xSemaphoreTake(mutex, portMAX_DELAY);
    bool has = (latitude != 0.0 && longitude != 0.0);
    xSemaphoreGive(mutex);
    return has;
}

// ==================== PARSE TIME HELPERS ====================

bool SunsetCalculator::validateDateHeader(String header) {
    return (header.length() >= 20 && header.indexOf(',') >= 0);
}

void SunsetCalculator::parseRFC2822Date(String dateHeader) {
    int firstComma = dateHeader.indexOf(',');

    // Extract day
    int dayStart = firstComma + 2;
    int dayEnd = dateHeader.indexOf(' ', dayStart);
    currentTime.day = dateHeader.substring(dayStart, dayEnd).toInt();

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
}

void SunsetCalculator::convertToLocalTimeAndHandleRollover(int& hour, int& day, int& month, int& year) {
    hour = currentTime.hour + tz_offset;

    if (hour >= 24) {
        hour -= 24;
        day++;
        int daysInMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
        bool isLeap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
        if (isLeap) daysInMonth[1] = 29;

        if (day > daysInMonth[month - 1]) {
            day = 1;
            month++;
            if (month > 12) {
                month = 1;
                year++;
            }
        }
    } else if (hour < 0) {
        hour += 24;
        day--;
        if (day < 1) {
            month--;
            if (month < 1) {
                month = 12;
                year--;
            }
            int daysInMonth[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
            bool isLeap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
            if (isLeap) daysInMonth[1] = 29;
            day = daysInMonth[month - 1];
        }
    }
}

void SunsetCalculator::checkAndResetDayChangeFlag(int localYear, int localMonth, int localDay) {
    int currentLocalDay = getDayOfYear(localYear, localMonth, localDay);
    if (currentLocalDay != lastDayOfYear) {
        sunsetPlayedToday = false;
        lastDayOfYear = currentLocalDay;
        Serial.printf("🌅 New LOCAL day detected (day %d), sunset flag reset\n", currentLocalDay);
    }
}

// ==================== PARSE AND UPDATE TIME ====================

bool SunsetCalculator::parseAndUpdateTime(String dateHeader) {
    if (!validateDateHeader(dateHeader)) {
        Serial.println("⚠️ Invalid Date header format");
        return false;
    }

    xSemaphoreTake(mutex, portMAX_DELAY);
    try {
        parseRFC2822Date(dateHeader);

        int localHour = 0;
        int localDay = currentTime.day;
        int localMonth = currentTime.month;
        int localYear = currentTime.year;

        convertToLocalTimeAndHandleRollover(localHour, localDay, localMonth, localYear);
        checkAndResetDayChangeFlag(localYear, localMonth, localDay);

        xSemaphoreGive(mutex);
        return true;

    } catch (...) {
        xSemaphoreGive(mutex);
        Serial.println("⚠️ Error parsing Date header");
        return false;
    }
}

DateTime SunsetCalculator::getCurrentTime() {
    xSemaphoreTake(mutex, portMAX_DELAY);
    DateTime ret = currentTime;
    xSemaphoreGive(mutex);
    return ret;
}

void SunsetCalculator::calculateSunset() {
    xSemaphoreTake(mutex, portMAX_DELAY);
    
    // Check inside lock to be safe, though hasCoordinates handles its own lock 
    // we access member vars directly here so we need the lock anyway.
    if ((latitude == 0.0 && longitude == 0.0) || !timeInitialized) {
        xSemaphoreGive(mutex);
        return;
    }

    // Capture values for calculation to avoid holding lock during heavy math if needed
    // (SolarCalculator is fast enough to keep inside lock for simplicity)
    double lat = latitude;
    double lon = longitude;
    int y = currentTime.year;
    int m = currentTime.month;
    int d = currentTime.day;
    int8_t tz = tz_offset;
    
    // Call SolarCalculator with year, month, day
    double transit, sunrise, sunset;
    calcSunriseSunset(y, m, d, lat, lon, transit, sunrise, sunset);

    if (sunset < 0) {
        Serial.println("⚠️ No sunset today (polar region?)");
        sunsetMinutesSinceMidnight = -1;
        xSemaphoreGive(mutex);
        return;
    }

    // Convert sunset time from hours (in UTC) to local time minutes since midnight
    // sunset is returned as hours in UTC, convert to local time
    double sunsetLocal = sunset + tz;

    // Handle day wraparound
    if (sunsetLocal >= 24.0) {
        sunsetLocal -= 24.0;
    } else if (sunsetLocal < 0.0) {
        sunsetLocal += 24.0;
    }

    // Convert to minutes since midnight
    sunsetMinutesSinceMidnight = (int)(sunsetLocal * 60.0);

    int sunsetHour = sunsetMinutesSinceMidnight / 60;
    int sunsetMin = sunsetMinutesSinceMidnight % 60;

    Serial.printf("🌅 Sunset calculated: %02d:%02d (±15min trigger window)\n", sunsetHour, sunsetMin);
    xSemaphoreGive(mutex);
}

bool SunsetCalculator::isSunsetTime() {
    xSemaphoreTake(mutex, portMAX_DELAY);
    if (!timeInitialized || sunsetMinutesSinceMidnight < 0 || sunsetPlayedToday) {
        xSemaphoreGive(mutex);
        return false;
    }

    // Convert GMT to local time for sunset comparison
    int localHour = currentTime.hour + tz_offset;
    int localMinute = currentTime.minute;
    int currentSunsetMins = sunsetMinutesSinceMidnight;
    bool played = sunsetPlayedToday;
    xSemaphoreGive(mutex);

    // Handle hour overflow/underflow
    if (localHour >= 24) {
        localHour -= 24;
    } else if (localHour < 0) {
        localHour += 24;
    }

    int currentLocalMinutes = localHour * 60 + localMinute;
    int windowStart = currentSunsetMins - 15;
    int windowEnd = currentSunsetMins + 15;

    bool inWindow = (currentLocalMinutes >= windowStart && currentLocalMinutes <= windowEnd);

    if (inWindow && !played) {
        Serial.printf("🌅 SUNSET TRIGGER! Local time: %02d:%02d, Sunset: %02d:%02d\n",
                     localHour, localMinute,
                     currentSunsetMins / 60, currentSunsetMins % 60);
    }

    return inWindow;
}

void SunsetCalculator::markSunsetPlayed() {
    xSemaphoreTake(mutex, portMAX_DELAY);
    sunsetPlayedToday = true;
    xSemaphoreGive(mutex);
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
