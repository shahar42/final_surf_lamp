# arduino_transport.py
"""
Arduino communication transport layer
Supports both real HTTP communication and mock logging for development
"""

import logging
import json
import requests
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class ArduinoTransport:
    """Abstract base for Arduino communication"""
    
    def send_data(self, arduino_id, arduino_ip, formatted_data, headers):
        """
        Send data to Arduino device
        
        Returns:
            tuple: (success: bool, status_code: int, response_text: str)
        """
        raise NotImplementedError

class HTTPTransport(ArduinoTransport):
    """Real HTTP transport to Arduino devices"""
    
    def send_data(self, arduino_id, arduino_ip, formatted_data, headers):
        try:
            arduino_url = f"http://{arduino_ip}/api/update"
            logger.info(f"📤 POST URL: {arduino_url}")
            logger.info(f"📤 POST Headers: {headers}")
            logger.info(f"📤 POST Data: {json.dumps(formatted_data, indent=2)}")
            
            response = requests.post(
                arduino_url, 
                json=formatted_data, 
                headers=headers, 
                timeout=5
            )
            
            logger.info(f"📥 Arduino response status: {response.status_code}")
            logger.info(f"📥 Arduino response body: {response.text}")
            
            return response.status_code == 200, response.status_code, response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ HTTP request failed: {e}")
            return False, 0, str(e)

class MockTransport(ArduinoTransport):
    """Mock transport with rich logging for development"""
    
    def send_data(self, arduino_id, arduino_ip, formatted_data, headers):
        logger.info("🤖 ======= ARDUINO COMMUNICATION SIMULATION =======")
        logger.info(f"📡 Target: Arduino {arduino_id}")
        logger.info(f"📍 IP Address: {arduino_ip or 'NOT_SET'}")
        logger.info(f"📤 URL: http://{arduino_ip or 'IP_MISSING'}/api/update")
        logger.info(f"📤 Headers: {json.dumps(headers, indent=2)}")
        logger.info(f"📤 Payload:")
        logger.info(json.dumps(formatted_data, indent=2))
        logger.info(f"📅 Timestamp: {datetime.now().isoformat()}")
        logger.info("✅ [MOCK] Simulated successful Arduino response (200 OK)")
        logger.info("=" * 55)
        
        # Return same format as real HTTP transport
        return True, 200, '{"status": "ok", "mock": true}'

def get_arduino_transport():
    """Get the appropriate transport based on environment variable"""
    transport_mode = os.environ.get('ARDUINO_TRANSPORT', 'http').lower()
    
    if transport_mode == 'mock':
        logger.info("🧪 Using MOCK Arduino transport (logging only)")
        return MockTransport()
    else:
        logger.info("📡 Using HTTP Arduino transport (real communication)")
        return HTTPTransport()
