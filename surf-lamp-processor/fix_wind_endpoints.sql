-- Fix existing database entries to use OpenWeatherMap for wind data
-- Replace Open-Meteo wind endpoints with OpenWeatherMap

-- Tel Aviv wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Tel Aviv&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=32.0853%';

-- Hadera wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Hadera&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=32.4365%';

-- Ashdod wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Ashdod&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=31.7939%';

-- Haifa wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Haifa&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=32.7940%';

-- Netanya wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Netanya&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=32.3215%';

-- Nahariya wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Nahariya&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=33.006%';

-- Ashkelon wind endpoints
UPDATE usage_lamps
SET http_endpoint = 'http://api.openweathermap.org/data/2.5/weather?q=Ashkelon&appid=d6ef64df6585b7e88e51c221bbd41c2b'
WHERE http_endpoint LIKE '%api.open-meteo.com%'
AND http_endpoint LIKE '%latitude=31.6699%';