
import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys

# Add the directory of the current script to the path, so we can import background_processor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Now, import the target function and other dependencies
from background_processor import process_all_lamps

class TestApiPriority(unittest.TestCase):

    @patch('background_processor.update_current_conditions')
    @patch('background_processor.update_lamp_timestamp')
    @patch('background_processor.get_lamps_for_location')
    @patch('background_processor.get_location_based_configs')
    @patch('background_processor.requests.get')
    @patch('background_processor.get_endpoint_config')
    @patch('background_processor.test_database_connection')
    def test_api_failover_priority(self, mock_test_db_conn, mock_get_endpoint_config, mock_requests_get, mock_get_configs, mock_get_lamps, mock_update_ts, mock_update_cond):
        """
        Tests that process_all_lamps correctly fails over to a lower priority API
        when a higher priority one fails for a specific location.
        """
        print("🧪 Running test: test_api_failover_priority")

        # 1. Mock dependencies of process_all_lamps
        mock_test_db_conn.return_value = True # Simulate successful DB connection

        # Mock to return our specific test location
        location = "Test_Location_Failover"
        api_endpoints = [
            {'http_endpoint': 'http://api.priority1.com/fail', 'priority': 1, 'api_key': None, 'website_url': 'http://api.priority1.com'},
            {'http_endpoint': 'http://api.priority2.com/success', 'priority': 2, 'api_key': None, 'website_url': 'http://api.priority2.com'}
        ]
        mock_get_configs.return_value = {
            location: {'endpoints': api_endpoints}
        }

        # Mock to return a dummy lamp for our location
        mock_get_lamps.return_value = [{'lamp_id': 999, 'arduino_id': 9999}]

        # Mock the endpoint configuration mapping
        mock_get_endpoint_config.return_value = {
            'wave_height_m': ['hourly', 'wave_height', 0],
            'wave_period_s': ['hourly', 'wave_period', 0]
        }

        # 2. Configure Mock API Responses (same as before)
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.raise_for_status.side_effect = Exception("API Failed")

        mock_response_success = MagicMock()
        mock_response_success.status_code = 200
        # Simulate a simplified response for the fields the processor uses
        mock_response_success.json.return_value = {
            "hourly": {
                "time": ["2025-09-23T12:00"],
                "wave_height": [1.5], # wave_height_m from priority 2
                "wave_period": [8.0]  # wave_period_s from priority 2
            }
        }
        
        mock_requests_get.side_effect = [
            mock_response_fail,
            mock_response_success
        ]

        # 3. Run the main processing function
        process_all_lamps()

        # 4. Assertions
        # Assert that requests.get was called twice, in the correct priority order
        self.assertEqual(mock_requests_get.call_count, 2, "Should have called the API twice")
        calls = mock_requests_get.call_args_list
        self.assertEqual(calls[0], call('http://api.priority1.com/fail', headers={'User-Agent': 'SurfLamp-Agent/1.0'}, timeout=15))
        self.assertEqual(calls[1], call('http://api.priority2.com/success', headers={'User-Agent': 'SurfLamp-Agent/1.0'}, timeout=15))
        print("✅ Asserted that APIs were called in the correct priority order.")

        # Assert that the database was updated with data from the priority 2 API
        mock_update_cond.assert_called_once()
        update_call_args = mock_update_cond.call_args[0]
        lamp_id_updated = update_call_args[0]
        saved_data = update_call_args[1]
        
        self.assertEqual(lamp_id_updated, 999)
        self.assertEqual(saved_data.get('wave_height_m'), 1.5)
        self.assertEqual(saved_data.get('wave_period_s'), 8.0)
        print("✅ Asserted that the database was updated with data from the priority 2 API.")
        
        print("🎉 Test Passed!")

if __name__ == '__main__':
    unittest.main()
