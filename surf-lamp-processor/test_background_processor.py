# test_background_processor.py
"""
Test runner for the background processor
Run this locally to test the complete loop
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """Setup environment variables for testing"""
    print("🔧 Setting up test environment...")
    
    # Check if DATABASE_URL is set
    if not os.environ.get('DATABASE_URL'):
        print("❌ DATABASE_URL environment variable not set!")
        print("Please set it to your Supabase connection string:")
        print("export DATABASE_URL='postgresql://postgres:[password]@[host]:[port]/postgres'")
        return False
    
    # Set test mode
    os.environ['TEST_MODE'] = 'true'
    
    print("✅ Environment setup complete")
    print(f"   DATABASE_URL: {os.environ.get('DATABASE_URL')[:50]}...")
    print(f"   TEST_MODE: {os.environ.get('TEST_MODE')}")
    
    return True

def run_test():
    """Run the background processor test - completely data-driven"""
    print("\n🚀 Starting Background Processor Test...")
    print("📋 This test will make REAL API calls using data from your database")
    print("⚠️  Make sure you have API endpoints configured in usage_lamps table")
    print("="*60)
    
    try:
        # Import and run the background processor
        from background_processor import run_once
        
        print("📦 Background processor imported successfully")
        
        # Run the test
        success = run_once()
        
        if success:
            print("\n🎉 TEST COMPLETED SUCCESSFULLY!")
            print("✅ All components working correctly")
        else:
            print("\n❌ TEST FAILED!")
            print("Check the logs above for error details")
            
        return success
        
    except ImportError as e:
        print(f"❌ Failed to import background_processor: {e}")
        print("Make sure background_processor.py is in the same directory")
        return False
    except Exception as e:
        print(f"💥 Test crashed: {e}")
        return False

def check_log_file():
    """Check if log file was created and show contents"""
    log_file = Path("lamp_processor.log")
    
    if log_file.exists():
        print(f"\n📋 Log file created: {log_file}")
        print("📄 Recent log entries:")
        print("-" * 40)
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                # Show last 20 lines
                for line in lines[-20:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"❌ Failed to read log file: {e}")
    else:
        print("⚠️  No log file found")

def main():
    """Main test function"""
    print("🧪 Background Processor Test Suite")
    print("="*60)
    
    # Step 1: Setup environment
    if not setup_environment():
        sys.exit(1)
    
    # Step 2: Run the test
    success = run_test()
    
    # Step 3: Check logs
    check_log_file()
    
    # Step 4: Final result
    print("\n" + "="*60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("Your background processor is ready for deployment.")
        print("\nNext steps:")
        print("1. Review the logs above")
        print("2. When ready, uncomment the real API calls")
        print("3. Deploy to Render as a Background Worker")
    else:
        print("❌ TESTS FAILED!")
        print("Please fix the issues above before deploying.")
    
    print("="*60)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
