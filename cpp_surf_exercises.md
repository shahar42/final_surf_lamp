# C++ Surf Lamp Learning Exercises (C++98)

## Overview
These exercises teach advanced C++ concepts (abstract classes, virtual functions, templates, specialization) while connecting to your Surf Lamp system. All exercises are **read-only** - they query your database but never modify system state.

**C++ Standard:** C++98 (compatible with older compilers)
**Database:** PostgreSQL via libpqxx library
**Focus:** Learning through real surfing data you care about!

---

## Setup Instructions

### Prerequisites
```bash
# Install PostgreSQL C++ library
sudo apt-get install libpqxx-dev

# Compile example (single file)
g++ -Wall -o my_program my_program.cpp -lpqxx -lpq

# Compile with multiple files
g++ -Wall -o analyzer main.cpp surf_analyzer.cpp database.cpp -lpqxx -lpq
```

### Database Connection String
Use your Supabase connection details:
```cpp
std::string connString =
    "host=YOUR_HOST "
    "port=5432 "
    "dbname=postgres "
    "user=postgres "
    "password=YOUR_PASSWORD";
```

---

## Exercise 1: Surf Data Analyzer (Abstract Classes & Virtual Functions)

### Learning Goals
- Pure virtual functions
- Abstract base classes
- Polymorphism (runtime binding)
- Virtual destructors
- Inheritance hierarchies

### The Problem
Build an analytics system that can analyze surf data in different ways. You want to easily add new analysis types without modifying existing code.

### Architecture Diagram
```
      SurfAnalyzer (abstract)
           /    |    \
          /     |     \
    WavePattern WindTrend OptimalSurfTime
      Analyzer  Analyzer    Analyzer
```

### Starter Code

**surf_data.h** - Data structure
```cpp
#ifndef SURF_DATA_H
#define SURF_DATA_H

#include <string>

// POD struct for surf conditions
struct SurfData {
    int lamp_id;
    double wave_height_m;
    double wave_period_s;
    double wind_speed_mps;
    int wind_direction_deg;
    std::string location;
    std::string timestamp;

    SurfData()
        : lamp_id(0), wave_height_m(0.0), wave_period_s(0.0),
          wind_speed_mps(0.0), wind_direction_deg(0) {}
};

#endif
```

**surf_analyzer.h** - Abstract base class
```cpp
#ifndef SURF_ANALYZER_H
#define SURF_ANALYZER_H

#include <vector>
#include <string>
#include "surf_data.h"

// Abstract base class for surf analysis strategies
class SurfAnalyzer {
public:
    // Virtual destructor is CRITICAL for polymorphism
    virtual ~SurfAnalyzer() {}

    // Pure virtual functions - must be implemented by derived classes
    virtual void analyze(const std::vector<SurfData>& data) = 0;
    virtual std::string getReport() const = 0;
    virtual std::string getAnalyzerName() const = 0;

protected:
    std::string report;  // Shared storage for all analyzers
};

#endif
```

**wave_pattern_analyzer.h** - Concrete implementation #1
```cpp
#ifndef WAVE_PATTERN_ANALYZER_H
#define WAVE_PATTERN_ANALYZER_H

#include "surf_analyzer.h"

class WavePatternAnalyzer : public SurfAnalyzer {
public:
    WavePatternAnalyzer();
    virtual ~WavePatternAnalyzer();

    // Override pure virtual functions
    virtual void analyze(const std::vector<SurfData>& data);
    virtual std::string getReport() const;
    virtual std::string getAnalyzerName() const;

private:
    double calculateAverage(const std::vector<SurfData>& data);
    double findMax(const std::vector<SurfData>& data);
    double findMin(const std::vector<SurfData>& data);
};

#endif
```

**wave_pattern_analyzer.cpp** - YOUR TASK: Implement this!
```cpp
#include "wave_pattern_analyzer.h"
#include <sstream>
#include <algorithm>
#include <numeric>

WavePatternAnalyzer::WavePatternAnalyzer() {
    report = "";
}

WavePatternAnalyzer::~WavePatternAnalyzer() {
    // Cleanup if needed
}

void WavePatternAnalyzer::analyze(const std::vector<SurfData>& data) {
    // TODO: Implement analysis logic
    // 1. Calculate average wave height
    // 2. Find max and min wave height
    // 3. Determine if conditions are improving or worsening
    // 4. Count how many readings are above 1.5m (good surfing)
    // 5. Build a text report

    std::ostringstream oss;
    oss << "=== Wave Pattern Analysis ===" << std::endl;

    if (data.empty()) {
        oss << "No data available" << std::endl;
        report = oss.str();
        return;
    }

    double avg = calculateAverage(data);
    double max = findMax(data);
    double min = findMin(data);

    oss << "Average wave height: " << avg << "m" << std::endl;
    oss << "Max wave height: " << max << "m" << std::endl;
    oss << "Min wave height: " << min << "m" << std::endl;

    // TODO: Add trend analysis (improving/worsening)
    // TODO: Add surfability count (waves > 1.5m)

    report = oss.str();
}

std::string WavePatternAnalyzer::getReport() const {
    return report;
}

std::string WavePatternAnalyzer::getAnalyzerName() const {
    return "Wave Pattern Analyzer";
}

double WavePatternAnalyzer::calculateAverage(const std::vector<SurfData>& data) {
    // TODO: Implement average calculation
    // Hint: Loop through data, sum wave_height_m, divide by count
    double sum = 0.0;
    for (size_t i = 0; i < data.size(); ++i) {
        sum += data[i].wave_height_m;
    }
    return data.empty() ? 0.0 : sum / data.size();
}

double WavePatternAnalyzer::findMax(const std::vector<SurfData>& data) {
    // TODO: Implement max finding
    // Hint: Use std::max_element or manual loop
    return 0.0;  // Replace with actual implementation
}

double WavePatternAnalyzer::findMin(const std::vector<SurfData>& data) {
    // TODO: Implement min finding
    return 0.0;  // Replace with actual implementation
}
```

**wind_trend_analyzer.h** - Concrete implementation #2
```cpp
#ifndef WIND_TREND_ANALYZER_H
#define WIND_TREND_ANALYZER_H

#include "surf_analyzer.h"

class WindTrendAnalyzer : public SurfAnalyzer {
public:
    WindTrendAnalyzer();
    virtual ~WindTrendAnalyzer();

    virtual void analyze(const std::vector<SurfData>& data);
    virtual std::string getReport() const;
    virtual std::string getAnalyzerName() const;

private:
    std::string getWindDirectionName(int degrees);
    bool isOffshore(int degrees, const std::string& location);
};

#endif
```

**wind_trend_analyzer.cpp** - YOUR TASK: Implement this!
```cpp
#include "wind_trend_analyzer.h"
#include <sstream>

WindTrendAnalyzer::WindTrendAnalyzer() {
    report = "";
}

WindTrendAnalyzer::~WindTrendAnalyzer() {
}

void WindTrendAnalyzer::analyze(const std::vector<SurfData>& data) {
    // TODO: Implement wind analysis
    // 1. Calculate average wind speed
    // 2. Determine dominant wind direction
    // 3. Count offshore vs onshore winds (offshore is good for surfing!)
    // 4. Analyze wind speed trends (increasing/decreasing)

    std::ostringstream oss;
    oss << "=== Wind Trend Analysis ===" << std::endl;

    if (data.empty()) {
        oss << "No data available" << std::endl;
        report = oss.str();
        return;
    }

    // TODO: Implement analysis

    report = oss.str();
}

std::string WindTrendAnalyzer::getReport() const {
    return report;
}

std::string WindTrendAnalyzer::getAnalyzerName() const {
    return "Wind Trend Analyzer";
}

std::string WindTrendAnalyzer::getWindDirectionName(int degrees) {
    // TODO: Convert degrees to cardinal directions
    // N (0-45, 315-360), E (45-135), S (135-225), W (225-315)
    if (degrees < 45 || degrees >= 315) return "North";
    if (degrees >= 45 && degrees < 135) return "East";
    if (degrees >= 135 && degrees < 225) return "South";
    return "West";
}

bool WindTrendAnalyzer::isOffshore(int degrees, const std::string& location) {
    // TODO: Determine if wind is offshore for given location
    // Offshore wind = wind blowing FROM land TO sea (good for surfing!)
    // For Israeli coast (faces west): East wind (90-180 degrees) is offshore

    // Hint: You need to know which direction the beach faces
    return false;  // Replace with actual logic
}
```

**main.cpp** - Demonstrates polymorphism
```cpp
#include <iostream>
#include <vector>
#include "surf_analyzer.h"
#include "wave_pattern_analyzer.h"
#include "wind_trend_analyzer.h"
#include "surf_data.h"

// Database fetching will be added in next section
std::vector<SurfData> loadSampleData() {
    std::vector<SurfData> data;

    SurfData sample1;
    sample1.wave_height_m = 1.2;
    sample1.wave_period_s = 6.5;
    sample1.wind_speed_mps = 3.5;
    sample1.wind_direction_deg = 120;  // Offshore for Israel
    sample1.location = "Hadera, Israel";
    data.push_back(sample1);

    SurfData sample2;
    sample2.wave_height_m = 1.8;
    sample2.wave_period_s = 7.2;
    sample2.wind_speed_mps = 4.0;
    sample2.wind_direction_deg = 110;
    sample2.location = "Hadera, Israel";
    data.push_back(sample2);

    return data;
}

int main() {
    std::cout << "Surf Lamp Data Analyzer" << std::endl;
    std::cout << "======================" << std::endl << std::endl;

    // Load data
    std::vector<SurfData> surfData = loadSampleData();

    // Create array of analyzer pointers (polymorphism!)
    std::vector<SurfAnalyzer*> analyzers;
    analyzers.push_back(new WavePatternAnalyzer());
    analyzers.push_back(new WindTrendAnalyzer());

    // Run all analyzers polymorphically
    for (size_t i = 0; i < analyzers.size(); ++i) {
        SurfAnalyzer* analyzer = analyzers[i];

        std::cout << "Running: " << analyzer->getAnalyzerName() << std::endl;
        analyzer->analyze(surfData);
        std::cout << analyzer->getReport() << std::endl;
    }

    // Clean up (important!)
    for (size_t i = 0; i < analyzers.size(); ++i) {
        delete analyzers[i];
    }
    analyzers.clear();

    return 0;
}
```

### Your Tasks
1. Complete `calculateAverage()`, `findMax()`, `findMin()` in WavePatternAnalyzer
2. Implement full wind analysis in WindTrendAnalyzer
3. Add trend detection (improving/worsening conditions)
4. Create a third analyzer: `OptimalSurfTimeAnalyzer` that finds best surfing windows
5. Experiment with adding/removing analyzers without changing main()

### Key Learning Points
- **Pure virtual functions** force derived classes to implement behavior
- **Polymorphism** allows treating different analyzers uniformly
- **Virtual destructors** ensure proper cleanup through base pointers
- **Abstract classes** define interfaces without implementation

---

## Exercise 2: Database Connection Manager (Singleton Pattern & RAII)

### Learning Goals
- Singleton pattern
- RAII (Resource Acquisition Is Initialization)
- Copy constructor and assignment operator control
- Connection pooling basics

### The Problem
You need ONE database connection shared across your entire program. Multiple connections waste resources and can cause connection limits.

### Starter Code

**database_manager.h**
```cpp
#ifndef DATABASE_MANAGER_H
#define DATABASE_MANAGER_H

#include <pqxx/pqxx>
#include <vector>
#include <string>
#include "surf_data.h"

// Singleton class for managing database connection
class DatabaseManager {
public:
    // Get the single instance (lazy initialization)
    static DatabaseManager& getInstance();

    // Query methods
    std::vector<SurfData> fetchRecentConditions(const std::string& location, int hours);
    std::vector<SurfData> fetchAllLocations();
    bool testConnection();

    // Connection info
    std::string getConnectionStatus() const;

private:
    // Private constructor (singleton pattern)
    DatabaseManager();

    // Private destructor
    ~DatabaseManager();

    // Disable copying (C++98 way)
    DatabaseManager(const DatabaseManager&);
    DatabaseManager& operator=(const DatabaseManager&);

    // Connection
    pqxx::connection* conn;
    bool connected;

    // Helper methods
    SurfData parseSurfData(const pqxx::result::const_iterator& row);
    void connect();
    void disconnect();
};

#endif
```

**database_manager.cpp** - YOUR TASK: Complete implementation
```cpp
#include "database_manager.h"
#include <iostream>
#include <sstream>

// Static instance getter (Meyer's Singleton)
DatabaseManager& DatabaseManager::getInstance() {
    static DatabaseManager instance;  // Created once, destroyed at program end
    return instance;
}

// Private constructor
DatabaseManager::DatabaseManager() : conn(NULL), connected(false) {
    connect();
}

// Private destructor
DatabaseManager::~DatabaseManager() {
    disconnect();
}

void DatabaseManager::connect() {
    try {
        // TODO: Replace with your actual connection string
        std::string connString =
            "host=YOUR_SUPABASE_HOST "
            "port=5432 "
            "dbname=postgres "
            "user=postgres "
            "password=YOUR_PASSWORD";

        conn = new pqxx::connection(connString);

        if (conn->is_open()) {
            connected = true;
            std::cout << "Database connected successfully!" << std::endl;
        } else {
            connected = false;
            std::cerr << "Failed to open database connection" << std::endl;
        }

    } catch (const std::exception& e) {
        std::cerr << "Database connection error: " << e.what() << std::endl;
        connected = false;
        conn = NULL;
    }
}

void DatabaseManager::disconnect() {
    if (conn != NULL) {
        delete conn;
        conn = NULL;
        connected = false;
        std::cout << "Database disconnected" << std::endl;
    }
}

bool DatabaseManager::testConnection() {
    if (!connected || conn == NULL) {
        return false;
    }

    try {
        pqxx::work txn(*conn);
        pqxx::result r = txn.exec("SELECT 1");
        return true;
    } catch (const std::exception& e) {
        std::cerr << "Connection test failed: " << e.what() << std::endl;
        return false;
    }
}

std::string DatabaseManager::getConnectionStatus() const {
    std::ostringstream oss;
    oss << "Connection: " << (connected ? "ACTIVE" : "INACTIVE");
    if (conn != NULL && connected) {
        oss << " | Database: " << conn->dbname();
    }
    return oss.str();
}

std::vector<SurfData> DatabaseManager::fetchRecentConditions(
    const std::string& location,
    int hours
) {
    std::vector<SurfData> results;

    if (!connected || conn == NULL) {
        std::cerr << "Database not connected!" << std::endl;
        return results;
    }

    try {
        pqxx::work txn(*conn);

        // SQL query to fetch recent conditions for a location
        std::ostringstream query;
        query << "SELECT "
              << "  cc.lamp_id, "
              << "  cc.wave_height_m, "
              << "  cc.wave_period_s, "
              << "  cc.wind_speed_mps, "
              << "  cc.wind_direction_deg, "
              << "  u.location, "
              << "  cc.last_updated "
              << "FROM current_conditions cc "
              << "JOIN lamps l ON cc.lamp_id = l.lamp_id "
              << "JOIN users u ON l.user_id = u.user_id "
              << "WHERE u.location = " << txn.quote(location) << " "
              << "  AND cc.last_updated > NOW() - INTERVAL '" << hours << " hours' "
              << "ORDER BY cc.last_updated DESC";

        pqxx::result r = txn.exec(query.str());

        std::cout << "Query returned " << r.size() << " rows" << std::endl;

        for (pqxx::result::const_iterator row = r.begin(); row != r.end(); ++row) {
            results.push_back(parseSurfData(row));
        }

    } catch (const std::exception& e) {
        std::cerr << "Query error: " << e.what() << std::endl;
    }

    return results;
}

std::vector<SurfData> DatabaseManager::fetchAllLocations() {
    // TODO: Implement fetching data for all locations
    std::vector<SurfData> results;

    if (!connected || conn == NULL) {
        return results;
    }

    try {
        pqxx::work txn(*conn);

        // Query for all current conditions
        std::string query =
            "SELECT "
            "  cc.lamp_id, "
            "  cc.wave_height_m, "
            "  cc.wave_period_s, "
            "  cc.wind_speed_mps, "
            "  cc.wind_direction_deg, "
            "  u.location, "
            "  cc.last_updated "
            "FROM current_conditions cc "
            "JOIN lamps l ON cc.lamp_id = l.lamp_id "
            "JOIN users u ON l.user_id = u.user_id "
            "ORDER BY u.location, cc.last_updated DESC";

        pqxx::result r = txn.exec(query);

        for (pqxx::result::const_iterator row = r.begin(); row != r.end(); ++row) {
            results.push_back(parseSurfData(row));
        }

    } catch (const std::exception& e) {
        std::cerr << "Query error: " << e.what() << std::endl;
    }

    return results;
}

SurfData DatabaseManager::parseSurfData(const pqxx::result::const_iterator& row) {
    SurfData data;

    // Parse each field (handle NULL values)
    data.lamp_id = row["lamp_id"].as<int>(0);
    data.wave_height_m = row["wave_height_m"].as<double>(0.0);
    data.wave_period_s = row["wave_period_s"].as<double>(0.0);
    data.wind_speed_mps = row["wind_speed_mps"].as<double>(0.0);
    data.wind_direction_deg = row["wind_direction_deg"].as<int>(0);
    data.location = row["location"].as<std::string>("");
    data.timestamp = row["last_updated"].as<std::string>("");

    return data;
}
```

**Updated main.cpp** - Now with real database queries!
```cpp
#include <iostream>
#include <vector>
#include "surf_analyzer.h"
#include "wave_pattern_analyzer.h"
#include "wind_trend_analyzer.h"
#include "database_manager.h"

int main() {
    std::cout << "Surf Lamp Real-Time Analyzer" << std::endl;
    std::cout << "============================" << std::endl << std::endl;

    // Get singleton instance
    DatabaseManager& db = DatabaseManager::getInstance();

    // Test connection
    std::cout << db.getConnectionStatus() << std::endl;
    if (!db.testConnection()) {
        std::cerr << "Cannot connect to database. Exiting." << std::endl;
        return 1;
    }
    std::cout << std::endl;

    // Fetch real data from Hadera
    std::cout << "Fetching surf conditions for Hadera, Israel (last 24 hours)..." << std::endl;
    std::vector<SurfData> surfData = db.fetchRecentConditions("Hadera, Israel", 24);

    if (surfData.empty()) {
        std::cout << "No data available. Try different location or time range." << std::endl;
        return 0;
    }

    std::cout << "Found " << surfData.size() << " data points" << std::endl << std::endl;

    // Run analysis
    std::vector<SurfAnalyzer*> analyzers;
    analyzers.push_back(new WavePatternAnalyzer());
    analyzers.push_back(new WindTrendAnalyzer());

    for (size_t i = 0; i < analyzers.size(); ++i) {
        std::cout << "Running: " << analyzers[i]->getAnalyzerName() << std::endl;
        analyzers[i]->analyze(surfData);
        std::cout << analyzers[i]->getReport() << std::endl;
    }

    // Cleanup
    for (size_t i = 0; i < analyzers.size(); ++i) {
        delete analyzers[i];
    }

    return 0;
}
```

### Your Tasks
1. Fill in your actual Supabase connection string
2. Test the singleton pattern (try getting instance multiple times)
3. Implement error handling for disconnections
4. Add a method to fetch historical data for a specific lamp_id
5. Verify only ONE connection exists (add debug prints in constructor)

### Key Learning Points
- **Singleton pattern** ensures single instance across program
- **RAII** - connection managed through constructor/destructor
- **Private copy constructor** prevents accidental copying
- **Resource management** - always delete what you new

---

## Exercise 3: Template-Based Metric Comparator

### Learning Goals
- Template classes
- Template functions
- Function templates with type deduction
- Template specialization
- STL algorithms with templates

### The Problem
You want to compare ANY surf metric (wave height, wind speed, period) across locations generically, without writing duplicate code.

### Starter Code

**metric_comparator.h**
```cpp
#ifndef METRIC_COMPARATOR_H
#define METRIC_COMPARATOR_H

#include <map>
#include <string>
#include <algorithm>
#include <numeric>
#include <iostream>

// Template class for comparing metrics across locations
template<typename T>
class MetricComparator {
public:
    MetricComparator(const std::string& metricName);

    // Add a location's metric value
    void addLocation(const std::string& location, const T& value);

    // Get best/worst locations
    std::string getBestLocation() const;
    std::string getWorstLocation() const;

    // Statistics
    double getAverage() const;
    T getMax() const;
    T getMin() const;

    // Display results
    void printComparison() const;

private:
    std::string metricName;
    std::map<std::string, T> locationData;
};

// Template implementation MUST be in header for C++98

template<typename T>
MetricComparator<T>::MetricComparator(const std::string& name)
    : metricName(name) {
}

template<typename T>
void MetricComparator<T>::addLocation(const std::string& location, const T& value) {
    locationData[location] = value;
}

template<typename T>
std::string MetricComparator<T>::getBestLocation() const {
    if (locationData.empty()) {
        return "No data";
    }

    // Find location with maximum value
    typename std::map<std::string, T>::const_iterator maxIt = locationData.begin();
    typename std::map<std::string, T>::const_iterator it;

    for (it = locationData.begin(); it != locationData.end(); ++it) {
        if (it->second > maxIt->second) {
            maxIt = it;
        }
    }

    return maxIt->first;
}

template<typename T>
std::string MetricComparator<T>::getWorstLocation() const {
    if (locationData.empty()) {
        return "No data";
    }

    // TODO: Implement finding minimum value location
    // Similar to getBestLocation but find minimum
    typename std::map<std::string, T>::const_iterator minIt = locationData.begin();

    // YOUR CODE HERE

    return minIt->first;
}

template<typename T>
double MetricComparator<T>::getAverage() const {
    if (locationData.empty()) {
        return 0.0;
    }

    T sum = T();  // Default constructor (0 for numeric types)
    typename std::map<std::string, T>::const_iterator it;

    for (it = locationData.begin(); it != locationData.end(); ++it) {
        sum += it->second;
    }

    return static_cast<double>(sum) / locationData.size();
}

template<typename T>
T MetricComparator<T>::getMax() const {
    if (locationData.empty()) {
        return T();
    }

    T maxVal = locationData.begin()->second;
    typename std::map<std::string, T>::const_iterator it;

    for (it = locationData.begin(); it != locationData.end(); ++it) {
        if (it->second > maxVal) {
            maxVal = it->second;
        }
    }

    return maxVal;
}

template<typename T>
T MetricComparator<T>::getMin() const {
    // TODO: Implement minimum value finding
    return T();
}

template<typename T>
void MetricComparator<T>::printComparison() const {
    std::cout << "=== " << metricName << " Comparison ===" << std::endl;

    if (locationData.empty()) {
        std::cout << "No data available" << std::endl;
        return;
    }

    std::cout << "Best location: " << getBestLocation()
              << " (" << getMax() << ")" << std::endl;
    std::cout << "Worst location: " << getWorstLocation()
              << " (" << getMin() << ")" << std::endl;
    std::cout << "Average: " << getAverage() << std::endl;
    std::cout << std::endl;

    std::cout << "All locations:" << std::endl;
    typename std::map<std::string, T>::const_iterator it;
    for (it = locationData.begin(); it != locationData.end(); ++it) {
        std::cout << "  " << it->first << ": " << it->second << std::endl;
    }
    std::cout << std::endl;
}

#endif
```

**location_comparator.cpp** - Usage example
```cpp
#include <iostream>
#include <vector>
#include <map>
#include "metric_comparator.h"
#include "database_manager.h"
#include "surf_data.h"

// Helper function to group data by location
std::map<std::string, std::vector<SurfData> > groupByLocation(
    const std::vector<SurfData>& allData
) {
    std::map<std::string, std::vector<SurfData> > grouped;

    for (size_t i = 0; i < allData.size(); ++i) {
        grouped[allData[i].location].push_back(allData[i]);
    }

    return grouped;
}

// Calculate average wave height for a location
double calculateAverageWaveHeight(const std::vector<SurfData>& data) {
    if (data.empty()) return 0.0;

    double sum = 0.0;
    for (size_t i = 0; i < data.size(); ++i) {
        sum += data[i].wave_height_m;
    }
    return sum / data.size();
}

// TODO: Implement similar functions for wind speed and wave period

int main() {
    std::cout << "Multi-Location Surf Comparison" << std::endl;
    std::cout << "==============================" << std::endl << std::endl;

    // Get database instance
    DatabaseManager& db = DatabaseManager::getInstance();

    // Fetch all locations
    std::cout << "Fetching surf data for all locations..." << std::endl;
    std::vector<SurfData> allData = db.fetchAllLocations();

    if (allData.empty()) {
        std::cout << "No data available" << std::endl;
        return 0;
    }

    std::cout << "Found " << allData.size() << " total data points" << std::endl << std::endl;

    // Group by location
    std::map<std::string, std::vector<SurfData> > grouped = groupByLocation(allData);

    std::cout << "Locations found: " << grouped.size() << std::endl;
    std::map<std::string, std::vector<SurfData> >::const_iterator it;
    for (it = grouped.begin(); it != grouped.end(); ++it) {
        std::cout << "  - " << it->first << " (" << it->second.size() << " readings)" << std::endl;
    }
    std::cout << std::endl;

    // Compare wave heights across locations
    MetricComparator<double> waveComparator("Wave Height (m)");

    for (it = grouped.begin(); it != grouped.end(); ++it) {
        double avgHeight = calculateAverageWaveHeight(it->second);
        waveComparator.addLocation(it->first, avgHeight);
    }

    waveComparator.printComparison();

    // TODO: Create wind speed comparator
    // TODO: Create wave period comparator
    // TODO: Create a comparator for "surfability score" (custom metric)

    return 0;
}
```

### Your Tasks
1. Complete `getWorstLocation()` and `getMin()` implementations
2. Implement wind speed and wave period comparison functions
3. Create a custom "surfability score" that combines wave height and wind
4. Try instantiating MetricComparator with int, double, float - watch type deduction work!
5. Add sorting to print locations ranked by metric

### Key Learning Points
- **Templates** allow writing code once for any type
- **Type deduction** happens at compile time
- **Template instantiation** creates actual code for each used type
- **STL compatibility** - templates work seamlessly with STL containers

---

## Exercise 4: Custom Iterator for Surf Data (Advanced Templates)

### Learning Goals
- Iterator design pattern
- Operator overloading
- Template-based filtering
- STL algorithm compatibility

### The Problem
You want to iterate through surf data with custom filters (e.g., only "good surfing conditions") without copying data.

### Starter Code

**surf_data_filter.h**
```cpp
#ifndef SURF_DATA_FILTER_H
#define SURF_DATA_FILTER_H

#include <vector>
#include "surf_data.h"

// Predicate function pointer type
typedef bool (*SurfPredicate)(const SurfData&);

// Custom iterator that filters surf data
class FilteredSurfIterator {
public:
    // Constructor
    FilteredSurfIterator(
        std::vector<SurfData>::const_iterator begin,
        std::vector<SurfData>::const_iterator end,
        SurfPredicate predicate
    );

    // Dereference operators
    const SurfData& operator*() const;
    const SurfData* operator->() const;

    // Increment operators
    FilteredSurfIterator& operator++();     // Prefix ++
    FilteredSurfIterator operator++(int);   // Postfix ++

    // Comparison operators
    bool operator==(const FilteredSurfIterator& other) const;
    bool operator!=(const FilteredSurfIterator& other) const;

private:
    std::vector<SurfData>::const_iterator current;
    std::vector<SurfData>::const_iterator end;
    SurfPredicate filter;

    void advanceToNext();  // Move to next valid element
};

// Container class that provides filtered iteration
class FilteredSurfData {
public:
    FilteredSurfData(const std::vector<SurfData>& data, SurfPredicate predicate);

    FilteredSurfIterator begin() const;
    FilteredSurfIterator end() const;

    size_t count() const;  // Count filtered elements

private:
    const std::vector<SurfData>& data;
    SurfPredicate filter;
};

// Common filter predicates
bool isGoodSurfing(const SurfData& data);
bool isOffshoreWind(const SurfData& data);
bool isBigWaves(const SurfData& data);
bool isLightWind(const SurfData& data);

#endif
```

**surf_data_filter.cpp** - YOUR TASK: Implement this!
```cpp
#include "surf_data_filter.h"

// FilteredSurfIterator implementation

FilteredSurfIterator::FilteredSurfIterator(
    std::vector<SurfData>::const_iterator begin,
    std::vector<SurfData>::const_iterator end,
    SurfPredicate predicate
) : current(begin), end(end), filter(predicate) {
    // Advance to first valid element
    advanceToNext();
}

const SurfData& FilteredSurfIterator::operator*() const {
    return *current;
}

const SurfData* FilteredSurfIterator::operator->() const {
    return &(*current);
}

FilteredSurfIterator& FilteredSurfIterator::operator++() {
    // Prefix increment
    if (current != end) {
        ++current;
        advanceToNext();
    }
    return *this;
}

FilteredSurfIterator FilteredSurfIterator::operator++(int) {
    // Postfix increment
    FilteredSurfIterator temp = *this;
    ++(*this);
    return temp;
}

bool FilteredSurfIterator::operator==(const FilteredSurfIterator& other) const {
    return current == other.current;
}

bool FilteredSurfIterator::operator!=(const FilteredSurfIterator& other) const {
    return current != other.current;
}

void FilteredSurfIterator::advanceToNext() {
    // TODO: Implement advancing to next element that matches filter
    // Loop until we find an element where filter returns true, or reach end

    while (current != end && !filter(*current)) {
        ++current;
    }
}

// FilteredSurfData implementation

FilteredSurfData::FilteredSurfData(
    const std::vector<SurfData>& dataVec,
    SurfPredicate predicate
) : data(dataVec), filter(predicate) {
}

FilteredSurfIterator FilteredSurfData::begin() const {
    return FilteredSurfIterator(data.begin(), data.end(), filter);
}

FilteredSurfIterator FilteredSurfData::end() const {
    return FilteredSurfIterator(data.end(), data.end(), filter);
}

size_t FilteredSurfData::count() const {
    // TODO: Count how many elements pass the filter
    size_t cnt = 0;
    FilteredSurfIterator it = begin();
    FilteredSurfIterator endIt = end();

    while (it != endIt) {
        ++cnt;
        ++it;
    }

    return cnt;
}

// Predicate implementations

bool isGoodSurfing(const SurfData& data) {
    // Good surfing: waves > 1.0m, wind < 7 m/s
    return data.wave_height_m > 1.0 && data.wind_speed_mps < 7.0;
}

bool isOffshoreWind(const SurfData& data) {
    // TODO: Implement offshore wind check
    // For Israeli coast: East wind (45-180 degrees) is offshore
    return data.wind_direction_deg >= 45 && data.wind_direction_deg <= 180;
}

bool isBigWaves(const SurfData& data) {
    // TODO: Implement big wave check (> 2.0m)
    return data.wave_height_m > 2.0;
}

bool isLightWind(const SurfData& data) {
    // TODO: Implement light wind check (< 5 m/s)
    return data.wind_speed_mps < 5.0;
}
```

**filter_demo.cpp** - Usage demonstration
```cpp
#include <iostream>
#include "surf_data_filter.h"
#include "database_manager.h"

int main() {
    std::cout << "Surf Data Filtering Demo" << std::endl;
    std::cout << "========================" << std::endl << std::endl;

    DatabaseManager& db = DatabaseManager::getInstance();

    // Fetch all data for Hadera
    std::vector<SurfData> allData = db.fetchRecentConditions("Hadera, Israel", 48);

    std::cout << "Total data points: " << allData.size() << std::endl << std::endl;

    // Filter for good surfing conditions
    FilteredSurfData goodSurfing(allData, isGoodSurfing);

    std::cout << "Good surfing conditions: " << goodSurfing.count() << std::endl;
    std::cout << "Details:" << std::endl;

    // Iterate using custom iterator
    for (FilteredSurfIterator it = goodSurfing.begin();
         it != goodSurfing.end();
         ++it) {
        std::cout << "  Wave: " << it->wave_height_m << "m, "
                  << "Wind: " << it->wind_speed_mps << " m/s, "
                  << "Time: " << it->timestamp << std::endl;
    }
    std::cout << std::endl;

    // Filter for offshore wind
    FilteredSurfData offshoreConditions(allData, isOffshoreWind);

    std::cout << "Offshore wind conditions: " << offshoreConditions.count() << std::endl;
    for (FilteredSurfIterator it = offshoreConditions.begin();
         it != offshoreConditions.end();
         ++it) {
        std::cout << "  Direction: " << it->wind_direction_deg << " degrees, "
                  << "Speed: " << it->wind_speed_mps << " m/s" << std::endl;
    }
    std::cout << std::endl;

    // TODO: Try combining filters (good surfing AND offshore wind)

    return 0;
}
```

### Your Tasks
1. Complete the `advanceToNext()` method
2. Implement all predicate functions
3. Create a "combined predicate" that checks multiple conditions
4. Add reverse iteration capability
5. Make iterator work with STL algorithms (std::count_if, std::find_if)

### Key Learning Points
- **Operator overloading** makes custom types behave like built-in types
- **Iterator pattern** provides uniform way to traverse containers
- **Function pointers** enable strategy pattern in C++98
- **Const correctness** prevents accidental modification

---

## Exercise 5: Surf Report Generator (Template Specialization)

### Learning Goals
- Template specialization
- Function template overloading
- Compile-time vs runtime polymorphism
- String formatting techniques

### The Problem
Generate reports in different formats (text, HTML, CSV) using templates instead of inheritance.

### Starter Code

**report_generator.h**
```cpp
#ifndef REPORT_GENERATOR_H
#define REPORT_GENERATOR_H

#include <string>
#include <vector>
#include <sstream>
#include "surf_data.h"

// Format tag types (empty structs for compile-time dispatch)
struct TextFormat {};
struct HTMLFormat {};
struct CSVFormat {};

// Primary template
template<typename FormatType>
class ReportGenerator {
public:
    static std::string generateHeader(const std::string& title);
    static std::string generateFooter();
    static std::string formatSurfData(const SurfData& data);
    static std::string generateReport(
        const std::string& title,
        const std::vector<SurfData>& data
    );
};

// Specialization for Text format
template<>
class ReportGenerator<TextFormat> {
public:
    static std::string generateHeader(const std::string& title) {
        std::ostringstream oss;
        oss << "==================================" << std::endl;
        oss << title << std::endl;
        oss << "==================================" << std::endl;
        return oss.str();
    }

    static std::string generateFooter() {
        return "==================================" std::endl;
    }

    static std::string formatSurfData(const SurfData& data) {
        std::ostringstream oss;
        oss << "Location: " << data.location << std::endl;
        oss << "  Wave Height: " << data.wave_height_m << "m" << std::endl;
        oss << "  Wave Period: " << data.wave_period_s << "s" << std::endl;
        oss << "  Wind Speed: " << data.wind_speed_mps << " m/s" << std::endl;
        oss << "  Wind Direction: " << data.wind_direction_deg << " degrees" << std::endl;
        oss << "  Time: " << data.timestamp << std::endl;
        oss << "----------------------------------" << std::endl;
        return oss.str();
    }

    static std::string generateReport(
        const std::string& title,
        const std::vector<SurfData>& data
    ) {
        std::ostringstream oss;
        oss << generateHeader(title);

        for (size_t i = 0; i < data.size(); ++i) {
            oss << formatSurfData(data[i]);
        }

        oss << generateFooter();
        return oss.str();
    }
};

// TODO: Specialization for HTML format
template<>
class ReportGenerator<HTMLFormat> {
public:
    static std::string generateHeader(const std::string& title) {
        // TODO: Generate HTML header with <html>, <head>, <title>, <body>
        std::ostringstream oss;
        oss << "<!DOCTYPE html>" << std::endl;
        oss << "<html>" << std::endl;
        oss << "<head><title>" << title << "</title></head>" << std::endl;
        oss << "<body>" << std::endl;
        oss << "<h1>" << title << "</h1>" << std::endl;
        oss << "<table border='1'>" << std::endl;
        oss << "<tr><th>Location</th><th>Wave Height</th><th>Wave Period</th>"
            << "<th>Wind Speed</th><th>Wind Direction</th><th>Time</th></tr>" << std::endl;
        return oss.str();
    }

    static std::string generateFooter() {
        // TODO: Close HTML tags
        return "</table></body></html>";
    }

    static std::string formatSurfData(const SurfData& data) {
        // TODO: Format as HTML table row
        std::ostringstream oss;
        oss << "<tr>";
        oss << "<td>" << data.location << "</td>";
        // TODO: Complete other columns
        oss << "</tr>" << std::endl;
        return oss.str();
    }

    static std::string generateReport(
        const std::string& title,
        const std::vector<SurfData>& data
    ) {
        std::ostringstream oss;
        oss << generateHeader(title);

        for (size_t i = 0; i < data.size(); ++i) {
            oss << formatSurfData(data[i]);
        }

        oss << generateFooter();
        return oss.str();
    }
};

// TODO: Specialization for CSV format
template<>
class ReportGenerator<CSVFormat> {
public:
    static std::string generateHeader(const std::string& title) {
        // CSV header row
        return "Location,Wave Height (m),Wave Period (s),Wind Speed (m/s),Wind Direction (deg),Timestamp\n";
    }

    static std::string generateFooter() {
        return "";  // No footer for CSV
    }

    static std::string formatSurfData(const SurfData& data) {
        // TODO: Format as CSV row
        std::ostringstream oss;
        oss << data.location << ",";
        oss << data.wave_height_m << ",";
        // TODO: Complete other fields
        oss << std::endl;
        return oss.str();
    }

    static std::string generateReport(
        const std::string& title,
        const std::vector<SurfData>& data
    ) {
        std::ostringstream oss;
        oss << generateHeader(title);

        for (size_t i = 0; i < data.size(); ++i) {
            oss << formatSurfData(data[i]);
        }

        oss << generateFooter();
        return oss.str();
    }
};

#endif
```

**report_demo.cpp**
```cpp
#include <iostream>
#include <fstream>
#include "report_generator.h"
#include "database_manager.h"

// Template function that works with any format
template<typename FormatType>
void saveReport(
    const std::string& filename,
    const std::string& title,
    const std::vector<SurfData>& data
) {
    std::string report = ReportGenerator<FormatType>::generateReport(title, data);

    std::ofstream file(filename.c_str());
    if (file.is_open()) {
        file << report;
        file.close();
        std::cout << "Report saved to: " << filename << std::endl;
    } else {
        std::cerr << "Failed to open file: " << filename << std::endl;
    }
}

int main() {
    std::cout << "Surf Report Generator" << std::endl;
    std::cout << "=====================" << std::endl << std::endl;

    DatabaseManager& db = DatabaseManager::getInstance();

    // Fetch data
    std::vector<SurfData> data = db.fetchRecentConditions("Hadera, Israel", 24);

    if (data.empty()) {
        std::cout << "No data to generate reports" << std::endl;
        return 0;
    }

    std::cout << "Generating reports from " << data.size() << " data points..." << std::endl;

    // Generate text report
    saveReport<TextFormat>("surf_report.txt", "Hadera Surf Conditions", data);

    // Generate HTML report
    saveReport<HTMLFormat>("surf_report.html", "Hadera Surf Conditions", data);

    // Generate CSV report
    saveReport<CSVFormat>("surf_report.csv", "Hadera Surf Conditions", data);

    std::cout << std::endl << "All reports generated!" << std::endl;

    return 0;
}
```

### Your Tasks
1. Complete the HTML and CSV specializations
2. Add a JSON format specialization
3. Create a "Markdown" format specialization (for GitHub)
4. Add styling to HTML report (colors for good/bad conditions)
5. Implement a function template that auto-detects format from file extension

### Key Learning Points
- **Template specialization** allows different behavior for specific types
- **Compile-time polymorphism** (templates) vs runtime polymorphism (virtual functions)
- **Zero runtime overhead** - format chosen at compile time
- **Type tags** enable compile-time dispatch

---

## Exercise 6: Exception-Safe Surf Data Cache

### Learning Goals
- Exception safety (basic, strong, no-throw guarantees)
- RAII for automatic cleanup
- Copy-and-swap idiom
- Resource management without smart pointers

### The Problem
Create a cache that handles errors gracefully without leaking resources or corrupting data.

### Starter Code

**surf_cache.h**
```cpp
#ifndef SURF_CACHE_H
#define SURF_CACHE_H

#include <map>
#include <string>
#include <ctime>
#include "surf_data.h"

// Cache entry with timestamp
struct CacheEntry {
    SurfData data;
    time_t timestamp;

    CacheEntry() : timestamp(0) {}
    CacheEntry(const SurfData& d, time_t t) : data(d), timestamp(t) {}
};

class SurfCache {
public:
    SurfCache(int maxAgeSec = 300);  // Default 5 minute cache
    ~SurfCache();

    // Copy constructor and assignment (Rule of Three)
    SurfCache(const SurfCache& other);
    SurfCache& operator=(const SurfCache& other);

    // Cache operations
    void insert(const std::string& key, const SurfData& data);
    bool get(const std::string& key, SurfData& data) const;
    void clear();
    size_t size() const;

    // Maintenance
    void removeExpired();
    void setMaxAge(int seconds);

private:
    std::map<std::string, CacheEntry>* cache;  // Pointer for copy-and-swap
    int maxAge;

    bool isExpired(const CacheEntry& entry) const;
    void swap(SurfCache& other);  // No-throw swap
};

#endif
```

**surf_cache.cpp** - YOUR TASK: Implement exception-safe operations
```cpp
#include "surf_cache.h"
#include <iostream>

SurfCache::SurfCache(int maxAgeSec) : maxAge(maxAgeSec) {
    // RAII: Acquire resource in constructor
    cache = new std::map<std::string, CacheEntry>();
}

SurfCache::~SurfCache() {
    // RAII: Release resource in destructor
    delete cache;
    cache = NULL;
}

SurfCache::SurfCache(const SurfCache& other) : maxAge(other.maxAge) {
    // TODO: Implement copy constructor
    // Must be exception-safe!
    cache = new std::map<std::string, CacheEntry>(*other.cache);
}

SurfCache& SurfCache::operator=(const SurfCache& other) {
    // TODO: Implement assignment operator using copy-and-swap idiom
    // This provides strong exception guarantee!

    if (this != &other) {
        SurfCache temp(other);  // Copy
        swap(temp);             // Swap (no-throw)
    }                           // temp destroyed, old data cleaned up

    return *this;
}

void SurfCache::swap(SurfCache& other) {
    // No-throw swap - critical for exception safety
    std::map<std::string, CacheEntry>* tempCache = cache;
    cache = other.cache;
    other.cache = tempCache;

    int tempAge = maxAge;
    maxAge = other.maxAge;
    other.maxAge = tempAge;
}

void SurfCache::insert(const std::string& key, const SurfData& data) {
    // Exception safety: If anything throws, cache remains unchanged
    try {
        CacheEntry entry(data, std::time(NULL));
        (*cache)[key] = entry;  // operator[] provides strong guarantee
    } catch (const std::exception& e) {
        std::cerr << "Cache insert failed: " << e.what() << std::endl;
        throw;  // Re-throw to caller
    }
}

bool SurfCache::get(const std::string& key, SurfData& data) const {
    // No-throw guarantee - never throws exceptions
    try {
        std::map<std::string, CacheEntry>::const_iterator it = cache->find(key);

        if (it == cache->end()) {
            return false;  // Not found
        }

        if (isExpired(it->second)) {
            return false;  // Expired
        }

        data = it->second.data;
        return true;

    } catch (...) {
        return false;  // Swallow all exceptions for no-throw guarantee
    }
}

void SurfCache::clear() {
    cache->clear();
}

size_t SurfCache::size() const {
    return cache->size();
}

void SurfCache::removeExpired() {
    // TODO: Remove all expired entries
    // Must be exception-safe!

    std::map<std::string, CacheEntry>::iterator it = cache->begin();
    while (it != cache->end()) {
        if (isExpired(it->second)) {
            // Erase and get next iterator (safe in C++98)
            cache->erase(it++);
        } else {
            ++it;
        }
    }
}

void SurfCache::setMaxAge(int seconds) {
    maxAge = seconds;
}

bool SurfCache::isExpired(const CacheEntry& entry) const {
    time_t now = std::time(NULL);
    return (now - entry.timestamp) > maxAge;
}
```

**cache_demo.cpp**
```cpp
#include <iostream>
#include "surf_cache.h"
#include "database_manager.h"

int main() {
    std::cout << "Exception-Safe Cache Demo" << std::endl;
    std::cout << "==========================" << std::endl << std::endl;

    SurfCache cache(60);  // 1 minute cache

    DatabaseManager& db = DatabaseManager::getInstance();

    // Insert some data
    std::vector<SurfData> data = db.fetchRecentConditions("Hadera, Israel", 1);

    if (!data.empty()) {
        cache.insert("hadera", data[0]);
        std::cout << "Cached Hadera data" << std::endl;
    }

    // Retrieve from cache
    SurfData cached;
    if (cache.get("hadera", cached)) {
        std::cout << "Cache hit! Wave height: " << cached.wave_height_m << "m" << std::endl;
    } else {
        std::cout << "Cache miss" << std::endl;
    }

    // Test copy constructor
    std::cout << std::endl << "Testing copy constructor..." << std::endl;
    SurfCache cache2(cache);
    std::cout << "cache2 size: " << cache2.size() << std::endl;

    // Test assignment operator
    std::cout << "Testing assignment operator..." << std::endl;
    SurfCache cache3(30);
    cache3 = cache;
    std::cout << "cache3 size: " << cache3.size() << std::endl;

    // Test expiration
    std::cout << std::endl << "Waiting for cache expiration..." << std::endl;
    // In real test, would sleep for 61 seconds

    return 0;
}
```

### Your Tasks
1. Implement proper copy constructor
2. Complete the removeExpired() method
3. Test exception safety by throwing exceptions during insert
4. Add statistics (hits, misses, expiration count)
5. Implement a "refresh" method that updates expired entries from database

### Key Learning Points
- **Rule of Three** - destructor, copy constructor, assignment operator
- **Copy-and-swap idiom** provides strong exception guarantee
- **RAII** ensures cleanup even with exceptions
- **Exception safety levels** - basic, strong, no-throw

---

## Bonus Exercise: Command-Line Surf Monitor

### Goal
Create a complete CLI tool that combines all concepts:

**Features:**
- Real-time monitoring of surf conditions
- Multiple output formats (text, HTML, CSV)
- Configurable filters and alerts
- Exception-safe caching
- Polymorphic analysis engines

**Usage:**
```bash
# Monitor Hadera with good surfing filter
./surf_monitor --location "Hadera, Israel" --filter good_surfing

# Generate HTML report for all locations
./surf_monitor --all-locations --format html --output report.html

# Analyze trends for last 48 hours
./surf_monitor --location "Tel Aviv, Israel" --analyze --hours 48
```

This combines:
- Abstract analyzers (Exercise 1)
- Singleton database manager (Exercise 2)
- Template comparators (Exercise 3)
- Custom iterators (Exercise 4)
- Template report generators (Exercise 5)
- Exception-safe cache (Exercise 6)

---

## Compilation Tips

### Makefile Example
```makefile
CXX = g++
CXXFLAGS = -Wall -Wextra -pedantic
LDFLAGS = -lpqxx -lpq

# Exercise 1
analyzer: main.o surf_analyzer.o wave_pattern_analyzer.o wind_trend_analyzer.o
	$(CXX) -o analyzer $^ $(LDFLAGS)

# Exercise 2
db_test: db_main.o database_manager.o surf_analyzer.o wave_pattern_analyzer.o
	$(CXX) -o db_test $^ $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $<

clean:
	rm -f *.o analyzer db_test

.PHONY: clean
```

### Common Compiler Errors and Solutions

**Error: undefined reference to vtable**
- Solution: Implement ALL pure virtual functions in derived classes

**Error: template must be a complete type**
- Solution: Put template implementation in header file (C++98 requirement)

**Error: no matching function for call**
- Solution: Check template argument types match exactly

---

## Learning Path Recommendation

1. **Week 1-2**: Exercise 1 (Abstract classes) + Exercise 2 (Database)
2. **Week 3**: Exercise 3 (Templates basics)
3. **Week 4**: Exercise 4 (Iterators)
4. **Week 5**: Exercise 5 (Template specialization)
5. **Week 6**: Exercise 6 (Exception safety)
6. **Week 7+**: Bonus command-line tool

Take your time - these are advanced concepts! Each exercise builds on previous ones.

---

## Getting Help

When stuck:
1. Check compiler error messages carefully
2. Use `std::cout` to debug template instantiation
3. Draw class diagrams on paper
4. Test small pieces before combining
5. Ask specific questions about concepts you don't understand

**Remember:** You're learning C++ through something you love (surfing)! Each exercise makes you a better C++ programmer while working with real surf data. How cool is that?

Happy coding and happy surfing! 🏄‍♂️
