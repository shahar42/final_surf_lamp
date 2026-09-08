# API response fixtures

Trimmed but structurally faithful samples of each upstream weather API the
processor consumes. Hourly arrays cover 2026-01-15 00:00..23:00 UTC so tests
freeze time inside that day and pick a known index.

| File | Source | Used for |
|---|---|---|
| open_meteo_marine.json | marine-api.open-meteo.com | wave height / period |
| open_meteo_forecast.json | api.open-meteo.com | wind speed (m/s) / direction |
| openweathermap_weather.json | api.openweathermap.org | wind fallback |
| isramar_station.json | isramar.ocean.org.il | custom wave extraction |
