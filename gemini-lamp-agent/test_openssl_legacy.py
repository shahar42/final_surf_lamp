#!/usr/bin/env python3
"""
Test OpenSSL Legacy Provider Fix for Render PostgreSQL
Based on research from PostgreSQL and OpenSSL documentation
"""

import os
import ssl
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openssl_legacy_fix():
    """Test OpenSSL configuration fixes"""
    
    print("🔧 Testing OpenSSL Legacy Provider Solutions...")
    print("=" * 60)
    
    # Solution 1: Set OpenSSL environment variables
    print("Solution 1: Setting OpenSSL environment variables...")
    
    # Set security level to 0 to allow older TLS versions
    os.environ['OPENSSL_CONF'] = '/dev/null'  # Ignore system config temporarily
    
    # Set OpenSSL configuration programmatically
    ssl_context = ssl.create_default_context()
    ssl_context.set_ciphers('DEFAULT@SECLEVEL=0')  # Lower security level
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    print(f"✅ SSL Context created with security level 0")
    print(f"   Protocol: {ssl_context.protocol}")
    print(f"   Verify mode: {ssl_context.verify_mode}")
    
    # Solution 2: Test connection with modified SSL settings
    print("\nSolution 2: Testing psycopg2 with modified SSL...")
    
    try:
        # Connection string with SSL parameters for OpenSSL 3.0
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            sslmode='require',
            sslcert='',  # Disable client cert
            sslkey='',   # Disable client key
            sslrootcert='',  # Disable root cert verification
            connect_timeout=30,
            application_name='openssl3_legacy_test'
        )
        
        print("🎉 SUCCESS: Connection worked with SSL modifications!")
        
        # Test the connection
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        result = cursor.fetchone()
        print(f"   Database version: {result[0][:50]}...")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False

def create_openssl_config_fix():
    """Create a local OpenSSL config file with legacy provider enabled"""
    
    print("\nSolution 3: Creating OpenSSL config with legacy provider...")
    
    config_content = """
# OpenSSL Configuration for Legacy Provider Support
openssl_conf = openssl_init

[openssl_init]
providers = provider_sect

[provider_sect]
default = default_sect
legacy = legacy_sect

[default_sect]
activate = 1

[legacy_sect]
activate = 1

[req]
distinguished_name = req_distinguished_name

[req_distinguished_name]
"""
    
    config_file = 'openssl_legacy.cnf'
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"✅ Created {config_file}")
    print("💡 To use this config, set: export OPENSSL_CONF=$(pwd)/openssl_legacy.cnf")
    
    return config_file

def test_with_legacy_config():
    """Test connection with legacy OpenSSL config"""
    
    print("\nSolution 4: Testing with legacy OpenSSL config...")
    
    # Set the custom OpenSSL config
    config_file = os.path.abspath('openssl_legacy.cnf')
    original_config = os.environ.get('OPENSSL_CONF', '')
    
    try:
        os.environ['OPENSSL_CONF'] = config_file
        print(f"   Set OPENSSL_CONF to: {config_file}")
        
        # Test connection
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            sslmode='require',
            connect_timeout=30,
            application_name='legacy_config_test'
        )
        
        print("🎉 SUCCESS: Legacy config fixed the connection!")
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Failed with legacy config: {e}")
        return False
        
    finally:
        # Restore original config
        if original_config:
            os.environ['OPENSSL_CONF'] = original_config
        else:
            os.environ.pop('OPENSSL_CONF', None)

def main():
    print("🚀 OpenSSL 3.0 + PostgreSQL Compatibility Test")
    print("Based on research from PostgreSQL and OpenSSL communities")
    print("=" * 80)
    
    # Check current OpenSSL version
    print(f"OpenSSL version: {ssl.OPENSSL_VERSION}")
    print(f"Python SSL module: {ssl.OPENSSL_VERSION_INFO}")
    print()
    
    # Try different solutions
    solutions = [
        ("Environment Variables", test_openssl_legacy_fix),
        ("Legacy Config Creation", create_openssl_config_fix),
        ("Legacy Config Test", test_with_legacy_config)
    ]
    
    successful_solutions = []
    
    for name, func in solutions:
        print(f"Testing: {name}")
        try:
            result = func()
            if result == True:
                successful_solutions.append(name)
            print()
        except Exception as e:
            print(f"❌ {name} failed: {e}")
            print()
    
    # Summary
    print("=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if successful_solutions:
        print("✅ Successful solutions:")
        for solution in successful_solutions:
            print(f"   • {solution}")
        print("\n🎯 Recommendation: Use the first successful solution for your project")
    else:
        print("❌ No solutions worked - this confirms OpenSSL 3.0 incompatibility")
        print("🔄 Recommendation: Switch to Supabase or downgrade OpenSSL")

if __name__ == "__main__":
    main()
