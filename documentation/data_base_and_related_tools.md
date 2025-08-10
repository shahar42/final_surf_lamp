#frame word
database.py
libraries - psycopg2, DQLALchemy

app.py
framework - flask
libraies: flask_bcrypt, requsts(http), dotenv


# Database Schema and Agent Tools

## Database Tables

### 1. users Table
| Column Name       | Data Type    | Constraints                          | Description                              |
|-------------------|--------------|--------------------------------------|------------------------------------------|
| user_id           | INTEGER      | PRIMARY KEY, NOT NULL, AUTO_INCREMENT | A unique identifier for each user.       |
| username          | VARCHAR(255) | NOT NULL, UNIQUE                     | The user's chosen username.              |
| password_hash     | TEXT         | NOT NULL                            | The hashed and salted password.          |
| email             | VARCHAR(255) | NOT NULL, UNIQUE                     | The user's email address.                |
| location          | VARCHAR(255) | NOT NULL                            | The user's physical location.            |
| theme             | VARCHAR(50)  | NOT NULL                            | The user's preferred theme.              |
| preferred_output  | VARCHAR(50)  | NOT NULL                            | The user's preferred unit for output.    |

### 2. lamps Table
| Column Name   | Data Type   | Constraints                                              | Description                                              |
|---------------|-------------|----------------------------------------------------------|----------------------------------------------------------|
| lamp_id       | INTEGER     | PRIMARY KEY, NOT NULL                                    | The unique ID of the IoT device.                         |
| user_id       | INTEGER     | FOREIGN KEY REFERENCES users(user_id), NOT NULL          | Links this lamp to a specific user.                      |
| arduino_id    | INTEGER     | NOT NULL, UNIQUE                                         | The unique ID of the Arduino board.                      |
| last_updated  | TIMESTAMP   | DEFAULT CURRENT_TIMESTAMP, ON UPDATE CURRENT_TIMESTAMP   | The timestamp of the last time this lamp's record was updated. |

### 3. daily_usage Table
| Column Name   | Data Type   | Constraints                                              | Description                                              |
|---------------|-------------|----------------------------------------------------------|----------------------------------------------------------|
| usage_id      | INTEGER     | PRIMARY KEY, NOT NULL, AUTO_INCREMENT                    | A unique ID for each website URL.                        |
| website_url   | VARCHAR(255)| NOT NULL, UNIQUE                                         | The URL of the website.                                  |
| last_updated  | TIMESTAMP   | DEFAULT CURRENT_TIMESTAMP, ON UPDATE CURRENT_TIMESTAMP   | The timestamp of the last time the record was updated.   |

### 4. location_websites Table
| Column Name   | Data Type   | Constraints                                              | Description                                              |
|---------------|-------------|----------------------------------------------------------|----------------------------------------------------------|
| location      | VARCHAR(255)| PRIMARY KEY, NOT NULL                                    | The location the user entered.                           |
| usage_id      | INTEGER     | FOREIGN KEY REFERENCES daily_usage(usage_id), NOT NULL, UNIQUE | The ID of the corresponding website usage record. |

### 5. usage_lamps Table
| Column Name   | Data Type   | Constraints                                              | Description                                              |
|---------------|-------------|----------------------------------------------------------|----------------------------------------------------------|
| usage_id      | INTEGER     | PRIMARY KEY, FOREIGN KEY REFERENCES daily_usage(usage_id)| Links to the usage record.                               |
| lamp_id       | INTEGER     | PRIMARY KEY, FOREIGN KEY REFERENCES lamps(lamp_id)       | Links to the lamp.                                       |
| api_key       | TEXT        | NULL                                                     | The API key for this specific lamp/website combination.  |
| http_endpoint | TEXT        | NOT NULL                                                 | The HTTP endpoint for this specific lamp/website combination. |

## Agent Tools

### 1. GetAllLampIDs
**Purpose**: To get a complete list of all active lamp_ids to begin the processing loop.  
**Input Parameters**: None.  
**Output**: A list of integers, where each integer is a lamp_id.

### 2. GetLampDetails
**Purpose**: To retrieve all the necessary data for a specific lamp, including its Arduino ID and the websites it is linked to.  
**Input Parameters**: lamp_id (integer).  
**Output**: A structured object containing the arduino_id, and a list of dictionaries, where each dictionary holds the website_url, api_key, and http_endpoint for each associated website.

### 3. FetchWebsiteData
**Purpose**: To retrieve raw data from a website's API.  
**Input Parameters**: api_key (string), http_endpoint (string).  
**Output**: The raw data from the API call (e.g., a JSON object).

### 4. SendToArduino
**Purpose**: To translate raw data and send it to the correct Arduino device.  
**Input Parameters**: arduino_id (integer), raw_data (any), preferred_output (string).  
**Output**: A boolean indicating success or failure.

### 5. UpdateLampTimestamp
**Purpose**: To update the last_updated timestamp for a specific lamp after its processing is complete.  
**Input Parameters**: lamp_id (integer).  
**Output**: A boolean indicating success or failure.
