#!/usr/bin/env python3
"""
Comprehensive Supabase Connection Tester
Tests multiple connection string combinations for Supabase with detailed diagnostics.
Designed to identify the correct configuration for connecting to Supabase from an IPv4 environment.
"""

import psycopg2
from sqlalchemy import create_engine, text
import time
import os
import socket
import ssl
import urllib.parse
import logging
from typing import List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Project-specific configuration
PASSWORD = "UzDQ3nlJ5ICXOyrQ"  # Replace with your actual password if different
PROJECT_REF = "onrzyewvkcugpmjdbfu"
HOST = "aws-0-us-east-1.pooler.supabase.com"  # Supavisor pooler hostname
DIRECT_HOST = f"db.{PROJECT_REF}.supabase.co"  # Direct connection hostname
DEFAULT_DB = "postgres"

def check_dns_resolution(host: str) -> bool:
    """Check if the hostname resolves to an IP address."""
    try:
        ip = socket.gethostbyname(host)
        logger.info(f"DNS resolution for {host}: {ip}")
        return True
    except socket.gaierror as e:
        logger.error(f"DNS resolution failed for {host}: {e}")
        return False

def check_port_connectivity(host: str, port: int) -> bool:
    """Check if the host and port are reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        sock.close()
        logger.info(f"Port {port} is reachable on {host}")
        return True
    except Exception as e:
        logger.error(f"Port {port} connectivity failed for {host}: {e}")
        return False

def url_encode_password(password: str) -> str:
    """URL-encode the password to handle special characters."""
    return urllib.parse.quote(password)

def test_psycopg2_connection(conn_string: str, description: str) -> bool:
    """Test connection using psycopg2."""
    logger.info(f"\nTesting {description}")
    safe_conn_string = conn_string.replace(PASSWORD, "[PASSWORD]")
    logger.info(f"Connection string: {safe_conn_string}")

    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info(f"✅ SUCCESS: psycopg2 connection worked! Result: {result}")
        return True
    except psycopg2.OperationalError as e:
        logger.error(f"❌ FAILED: psycopg2 OperationalError: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ FAILED: psycopg2 unexpected error: {type(e).__name__}: {e}")
        return False

def test_sqlalchemy_connection(conn_string: str, description: str) -> bool:
    """Test connection using SQLAlchemy."""
    logger.info(f"Testing SQLAlchemy for {description}")
    try:
        engine = create_engine(conn_string)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1")).fetchone()
        logger.info(f"✅ SUCCESS: SQLAlchemy connection worked! Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ FAILED: SQLAlchemy error: {type(e).__name__}: {e}")
        return False

def test_ssl_connection(conn_string: str, description: str, cert_path: str = None) -> bool:
    """Test connection with explicit SSL configuration."""
    logger.info(f"Testing SSL connection for {description}")
    safe_conn_string = conn_string.replace(PASSWORD, "[PASSWORD]")
    logger.info(f"Connection string: {safe_conn_string}")

    try:
        kwargs = {"sslmode": "require"}
        if cert_path and os.path.exists(cert_path):
            kwargs["sslrootcert"] = cert_path
            logger.info(f"Using SSL root certificate: {cert_path}")
        else:
            logger.warning("No SSL root certificate provided; using default verification")

        conn = psycopg2.connect(conn_string, **kwargs)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        logger.info(f"✅ SUCCESS: SSL psycopg2 connection worked! Result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ FAILED: SSL connection error: {type(e).__name__}: {e}")
        return False

def main():
    logger.info("🚀 Starting Comprehensive Supabase Connection Test")
    logger.info("=" * 60)

    # Check DNS resolution for hosts
    logger.info("🔍 Checking DNS resolution")
    check_dns_resolution(HOST)
    check_dns_resolution(DIRECT_HOST)

    # Check port connectivity
    logger.info("\n🔍 Checking port connectivity")
    check_port_connectivity(HOST, 5432)  # Session mode
    check_port_connectivity(HOST, 6543)  # Transaction mode
    check_port_connectivity(DIRECT_HOST, 5432)  # Direct connection

    # URL-encode password in case of special characters
    encoded_password = url_encode_password(PASSWORD)

    # Test configurations: (username, host, port, dbname, ssl_params, description, test_ssl)
    test_configs: List[Tuple[str, str, str, str, str, str, bool]] = [
        # Supavisor Session Mode (recommended for Render)
        ("postgres", HOST, "5432", DEFAULT_DB, "?sslmode=require", "Supavisor Session Mode (default user)", True),
        (f"postgres.{PROJECT_REF}", HOST, "5432", DEFAULT_DB, "?sslmode=require", "Supavisor Session Mode (tenant user)", True),
        ("postgres", HOST, "5432", DEFAULT_DB, "", "Supavisor Session Mode (no SSL)", False),
        (f"postgres.{PROJECT_REF}", HOST, "5432", DEFAULT_DB, "", "Supavisor Session Mode (tenant user, no SSL)", False),

        # Supavisor Transaction Mode (less likely for your app)
        ("postgres", HOST, "6543", DEFAULT_DB, "?sslmode=require", "Supavisor Transaction Mode (default user)", True),
        (f"postgres.{PROJECT_REF}", HOST, "6543", DEFAULT_DB, "?sslmode=require", "Supavisor Transaction Mode (tenant user)", True),
        ("postgres", HOST, "6543", DEFAULT_DB, "", "Supavisor Transaction Mode (no SSL)", False),
        (f"postgres.{PROJECT_REF}", HOST, "6543", DEFAULT_DB, "", "Supavisor Transaction Mode (tenant user, no SSL)", False),

        # Direct Connection (IPv6, should fail on Render but may work locally)
        ("postgres", DIRECT_HOST, "5432", DEFAULT_DB, "?sslmode=require", "Direct Connection (default user)", True),
        ("postgres", DIRECT_HOST, "5432", DEFAULT_DB, "", "Direct Connection (no SSL)", False),

        # Custom database name (if you created one)
        ("postgres", HOST, "5432", "surf_lamp_db", "?sslmode=require", "Supavisor Session Mode (custom db)", True),
        (f"postgres.{PROJECT_REF}", HOST, "5432", "surf_lamp_db", "?sslmode=require", "Supavisor Session Mode (tenant user, custom db)", True),
    ]

    successful_connections = []

    # Optional: Path to Supabase SSL root certificate (download from dashboard)
    cert_path = "supabase-ca.pem"  # Set to None if not available

    for i, (user, host, port, dbname, ssl_params, description, test_ssl) in enumerate(test_configs, 1):
        conn_string = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}{ssl_params}"
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST {i}: {description}")
        logger.info(f"{'='*60}")

        # Test psycopg2
        psycopg2_success = test_psycopg2_connection(conn_string, description)

        # Test SQLAlchemy if psycopg2 succeeds
        if psycopg2_success:
            sqlalchemy_success = test_sqlalchemy_connection(conn_string, description)
            if sqlalchemy_success:
                successful_connections.append((conn_string, description))

        # Test SSL explicitly if specified
        if test_ssl:
            ssl_success = test_ssl_connection(conn_string, description, cert_path)
            if ssl_success and not psycopg2_success:
                successful_connections.append((conn_string, f"{description} (SSL-specific)"))

        time.sleep(1)  # Avoid overwhelming the server

    # Summarize results
    logger.info(f"\n{'='*60}")
    logger.info("🎉 TEST RESULTS SUMMARY")
    logger.info(f"{'='*60}")

    if successful_connections:
        logger.info(f"✅ Found {len(successful_connections)} working connection(s):")
        for i, (conn_string, description) in enumerate(successful_connections, 1):
            safe_conn = conn_string.replace(encoded_password, "[PASSWORD]")
            logger.info(f"\n{i}. {description}")
            logger.info(f"   {safe_conn}")
        logger.info("\n🚀 RECOMMENDED: Use the first working Session Mode connection in your Render DATABASE_URL")
    else:
        logger.error("❌ No working connections found.")
        logger.info("\n🔍 Debug suggestions:")
        logger.info("   1. Verify password in Supabase dashboard (Settings > Database > Connection Info)")
        logger.info("   2. Check username format in Connect > Connection Pooling > Session mode")
        logger.info("   3. Ensure project is active and region is us-east-1")
        logger.info("   4. Check Network Restrictions/Bans in Supabase dashboard")
        logger.info("   5. Test with psql: psql 'postgresql://postgres:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require'")
        logger.info("   6. Download SSL root certificate from Supabase dashboard if SSL errors occur")
        logger.info("   7. Contact Supabase support with project ID: onrzyewvkcugpmjdbfu")

if __name__ == "__main__":
    main()
