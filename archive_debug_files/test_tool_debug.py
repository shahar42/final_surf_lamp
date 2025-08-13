#!/usr/bin/env python3
"""
EXTREME DEBUG VERSION - PostgreSQL Connection Debugging (FIXED)
This script will log EVERYTHING to help diagnose the SSL connection issue
"""

import os
import sys
import time
import socket
import ssl
import logging
import psycopg2
import psycopg2.extensions
from dotenv import load_dotenv
import subprocess
import platform

# Configure EXTREME logging
def setup_extreme_logging():
    """Setup extremely detailed logging to file"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create file handler
    file_handler = logging.FileHandler('log.txt', mode='w')
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler  
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # Create detailed formatter
    detailed_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)8s | %(name)20s | %(funcName)20s:%(lineno)4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(detailed_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_system_info(logger):
    """Log comprehensive system information"""
    logger.info("=" * 100)
    logger.info("SYSTEM INFORMATION COLLECTION STARTING")
    logger.info("=" * 100)
    
    # Python and system info
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Architecture: {platform.architecture()}")
    logger.info(f"Machine: {platform.machine()}")
    logger.info(f"Processor: {platform.processor()}")
    
    # Network info
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info(f"Local hostname: {hostname}")
        logger.info(f"Local IP: {local_ip}")
    except Exception as e:
        logger.error(f"Failed to get local network info: {e}")
    
    # psycopg2 version info
    logger.info(f"psycopg2 version: {psycopg2.__version__}")
    logger.info(f"psycopg2 libpq version: {psycopg2.__libpq_version__}")
    
    # SSL/TLS info (FIXED)
    logger.info(f"Python SSL version: {ssl.OPENSSL_VERSION}")
    try:
        logger.info(f"SSL/TLS supported: {ssl.HAS_TLSv1_3}")
        logger.info(f"SSL default ciphers: {len(ssl.get_default_verify_paths().cafile) if ssl.get_default_verify_paths().cafile else 'None'}")
    except Exception as e:
        logger.error(f"SSL info error: {e}")
    
    # Check if we can resolve the hostname
    try:
        host = os.getenv('DB_HOST')
        logger.info(f"Attempting to resolve hostname: {host}")
        ip_addresses = socket.gethostbyname_ex(host)
        logger.info(f"Hostname resolution successful: {ip_addresses}")
        
        for ip in ip_addresses[2]:
            logger.info(f"Resolved IP address: {ip}")
    except Exception as e:
        logger.error(f"Hostname resolution failed: {e}")

def log_environment_variables(logger):
    """Log all environment variables (safely)"""
    logger.info("=" * 50)
    logger.info("ENVIRONMENT VARIABLES")
    logger.info("=" * 50)
    
    env_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == 'DB_PASSWORD':
                logger.info(f"{var}: {'*' * len(value)} (length: {len(value)})")
            else:
                logger.info(f"{var}: {value}")
        else:
            logger.error(f"{var}: NOT SET!")

def test_network_connectivity(logger):
    """Test basic network connectivity to the database server"""
    logger.info("=" * 50)
    logger.info("NETWORK CONNECTIVITY TESTING")
    logger.info("=" * 50)
    
    host = os.getenv('DB_HOST')
    port = int(os.getenv('DB_PORT', 5432))
    
    # Test 1: Basic TCP connection
    logger.info(f"Testing TCP connection to {host}:{port}")
    start_time = time.time()
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((host, port))
        connect_time = time.time() - start_time
        
        if result == 0:
            logger.info(f"✅ TCP connection successful in {connect_time:.3f} seconds")
            
            # Get socket info
            local_addr = sock.getsockname()
            remote_addr = sock.getpeername()
            logger.info(f"Local address: {local_addr}")
            logger.info(f"Remote address: {remote_addr}")
            
        else:
            logger.error(f"❌ TCP connection failed with error code: {result}")
        
        sock.close()
        
    except Exception as e:
        logger.error(f"❌ TCP connection exception: {e}")
    
    # Test 2: SSL connection test
    logger.info(f"Testing SSL connection to {host}:{port}")
    try:
        context = ssl.create_default_context()
        
        # Log SSL context info
        logger.info(f"SSL protocol: {context.protocol}")
        logger.info(f"SSL verify mode: {context.verify_mode}")
        logger.info(f"SSL check hostname: {context.check_hostname}")
        
        with socket.create_connection((host, port), timeout=10) as sock:
            logger.info("Raw socket connection established")
            
            with context.wrap_socket(sock, server_hostname=host) as ssl_sock:
                logger.info("SSL handshake completed successfully")
                
                # Get SSL info
                ssl_info = ssl_sock.getpeercert()
                logger.info(f"SSL certificate subject: {ssl_info.get('subject', 'Unknown')}")
                logger.info(f"SSL certificate issuer: {ssl_info.get('issuer', 'Unknown')}")
                logger.info(f"SSL cipher: {ssl_sock.cipher()}")
                logger.info(f"SSL version: {ssl_sock.version()}")
                
    except Exception as e:
        logger.error(f"❌ SSL connection failed: {e}")
        logger.error(f"SSL error type: {type(e).__name__}")

def test_psycopg2_connection_variants(logger):
    """Test multiple psycopg2 connection approaches with detailed logging"""
    logger.info("=" * 50)
    logger.info("PSYCOPG2 CONNECTION VARIANTS TESTING")
    logger.info("=" * 50)
    
    host = os.getenv('DB_HOST')
    port = os.getenv('DB_PORT')
    database = os.getenv('DB_NAME')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    
    # Connection variant 1: Individual parameters with SSL
    logger.info("Testing Connection Variant 1: Individual parameters with sslmode=require")
    try:
        start_time = time.time()
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='require',
            connect_timeout=30,
            application_name='debug_test_v1'
        )
        
        connect_time = time.time() - start_time
        logger.info(f"✅ Variant 1 SUCCESS in {connect_time:.3f} seconds")
        
        # Test the connection
        cursor = conn.cursor()
        cursor.execute("SELECT version(), current_timestamp, inet_server_addr(), inet_server_port()")
        result = cursor.fetchone()
        logger.info(f"Database version: {result[0]}")
        logger.info(f"Server timestamp: {result[1]}")
        logger.info(f"Server IP: {result[2]}")
        logger.info(f"Server port: {result[3]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Variant 1 FAILED: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        if hasattr(e, 'pgcode'):
            logger.error(f"PostgreSQL error code: {e.pgcode}")
        if hasattr(e, 'pgerror'):
            logger.error(f"PostgreSQL error message: {e.pgerror}")
    
    # Connection variant 2: URL format
    logger.info("Testing Connection Variant 2: Full URL format")
    try:
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        logger.info(f"Connection URL (password masked): postgresql://{user}:****@{host}:{port}/{database}")
        
        start_time = time.time()
        conn = psycopg2.connect(url)
        connect_time = time.time() - start_time
        
        logger.info(f"✅ Variant 2 SUCCESS in {connect_time:.3f} seconds")
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Variant 2 FAILED: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
    
    # Connection variant 3: SSL prefer
    logger.info("Testing Connection Variant 3: sslmode=prefer")
    try:
        start_time = time.time()
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='prefer',
            connect_timeout=30,
            application_name='debug_test_v3'
        )
        
        connect_time = time.time() - start_time
        logger.info(f"✅ Variant 3 SUCCESS in {connect_time:.3f} seconds")
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Variant 3 FAILED: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
    
    # Connection variant 4: SSL disable (for testing)
    logger.info("Testing Connection Variant 4: sslmode=disable (testing only)")
    try:
        start_time = time.time()
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            sslmode='disable',
            connect_timeout=30,
            application_name='debug_test_v4'
        )
        
        connect_time = time.time() - start_time
        logger.info(f"✅ Variant 4 SUCCESS in {connect_time:.3f} seconds")
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Variant 4 FAILED: {e}")
        logger.error(f"Exception type: {type(e).__name__}")

def test_ping_and_traceroute(logger):
    """Test network path to the database server"""
    logger.info("=" * 50)
    logger.info("NETWORK PATH TESTING")
    logger.info("=" * 50)
    
    host = os.getenv('DB_HOST')
    
    # Test ping
    logger.info(f"Testing ping to {host}")
    try:
        if platform.system() == "Linux":
            result = subprocess.run(['ping', '-c', '4', host], 
                                  capture_output=True, text=True, timeout=15)
            logger.info(f"Ping exit code: {result.returncode}")
            logger.info(f"Ping stdout:\n{result.stdout}")
            if result.stderr:
                logger.error(f"Ping stderr:\n{result.stderr}")
        else:
            logger.info("Ping test skipped (not on Linux)")
            
    except Exception as e:
        logger.error(f"Ping test failed: {e}")

def run_comprehensive_debug():
    """Run all debug tests"""
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logger = setup_extreme_logging()
    
    logger.info("🚀 STARTING COMPREHENSIVE DATABASE CONNECTION DEBUG")
    logger.info(f"Debug started at: {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    
    try:
        # Run all tests
        log_system_info(logger)
        log_environment_variables(logger)
        test_ping_and_traceroute(logger)
        test_network_connectivity(logger)
        test_psycopg2_connection_variants(logger)
        
    except Exception as e:
        logger.error(f"Debug script failed: {e}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
    
    logger.info("🏁 COMPREHENSIVE DEBUG COMPLETED")
    logger.info("Check log.txt for complete details")
    print("\n" + "="*60)
    print("🔍 DEBUG COMPLETE! Check log.txt for detailed analysis")
    print("="*60)

if __name__ == "__main__":
    run_comprehensive_debug()
