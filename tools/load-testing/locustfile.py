"""Locust load test - simulates 1000 Arduinos polling API"""

# TODO: from locust import HttpUser, task, between

# Arduino IDs: 10001-11000
ARDUINO_IDS = list(range(10001, 11001))

class ArduinoSimulator:  # TODO: (HttpUser)
    """Simulates Arduino ESP32 polling behavior"""
    # wait_time = between(780, 820)  # 13 min ± variance

    def on_start(self):
        """Assign unique Arduino ID to each user"""
        # TODO: self.arduino_id = random.choice(ARDUINO_IDS)
        # TODO: ARDUINO_IDS.remove(self.arduino_id)
        pass

    # @task
    def poll_surf_data(self):
        """GET /api/arduino/<id>/data"""
        # TODO: self.client.get(f"/api/arduino/{self.arduino_id}/data")
        # TODO: Validate JSON response fields
        # TODO: Track response times
        pass

# TODO: Add event listeners for metrics collection
