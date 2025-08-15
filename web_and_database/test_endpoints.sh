#!/bin/bash

echo "🌊 Testing Weather API Endpoints"
echo "================================"

# Array of endpoints to test
endpoints=(
    "http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    "http://api.openweathermap.org/data/2.5/weather?q=Tel+Aviv&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    "http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    "http://api.openweathermap.org/data/2.5/weather?q=Haifa&appid=d6ef64df6585b7e88e51c221bbd41c2b"
    "http://api.openweathermap.org/data/2.5/weather?q=Netanya&appid=d6ef64df6585b7e88e51c221bbd41c2b"
)

# Location names for display
locations=("Hadera" "Tel Aviv" "Ashdod" "Haifa" "Netanya")

# Test each endpoint
for i in "${!endpoints[@]}"; do
    echo ""
    echo "Testing ${locations[$i]}..."
    echo "URL: ${endpoints[$i]}"
    
    response=$(curl -s -w "%{http_code}" "${endpoints[$i]}")
    http_code="${response: -3}"
    json_data="${response%???}"
    
    if [ "$http_code" = "200" ]; then
        echo "✅ Status: $http_code (SUCCESS)"
        # Extract basic weather info
        temp=$(echo "$json_data" | grep -o '"temp":[0-9.]*' | cut -d':' -f2)
        weather=$(echo "$json_data" | grep -o '"main":"[^"]*' | cut -d'"' -f4)
        if [ -n "$temp" ] && [ -n "$weather" ]; then
            temp_celsius=$(echo "$temp - 273.15" | bc 2>/dev/null || echo "N/A")
            echo "📊 Weather: $weather, Temp: ${temp_celsius}°C"
        fi
    else
        echo "❌ Status: $http_code (FAILED)"
        echo "Response: $json_data"
    fi
    echo "----------------------------------------"
done

echo ""
echo "🏁 Testing completed!"