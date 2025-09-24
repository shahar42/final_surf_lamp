#!/usr/bin/env python3
"""
Test Render deployment configuration
"""

import os
import sys

def test_deployment_readiness():
    """Test if deployment is ready"""
    print("🧪 Testing Render deployment readiness...")

    tests_passed = 0
    total_tests = 6

    # Test 1: Check required files exist
    required_files = [
        'render_monitoring_service.py',
        'surf_lamp_insights.py',
        'requirements.txt',
        'render.yaml'
    ]

    missing_files = []
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file} exists")
            tests_passed += 1
        else:
            print(f"❌ {file} missing")
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False

    # Test 2: Check requirements.txt
    try:
        with open('requirements.txt', 'r') as f:
            content = f.read()
            if 'google-generativeai' in content and 'schedule' in content:
                print("✅ requirements.txt has required packages")
                tests_passed += 1
            else:
                print("❌ requirements.txt missing required packages")
    except Exception as e:
        print(f"❌ Error reading requirements.txt: {e}")

    # Test 3: Test imports
    try:
        sys.path.append('./render-mcp-server')
        from surf_lamp_insights import SurfLampInsights
        import schedule
        print("✅ All imports work")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Import error: {e}")

    print(f"\n📊 Test Results: {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        print("🎉 Deployment is ready!")
        print("\n📋 Next steps:")
        print("1. Get Gmail app password from https://myaccount.google.com/apppasswords")
        print("2. Create Background Worker service on Render")
        print("3. Set environment variables (see RENDER_DEPLOYMENT.md)")
        print("4. Deploy and monitor logs")
        return True
    else:
        print("❌ Deployment not ready - fix issues above")
        return False

if __name__ == "__main__":
    test_deployment_readiness()