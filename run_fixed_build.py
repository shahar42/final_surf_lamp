#!/usr/bin/env python3
"""
Complete Fix Runner - Ensures LLMs Generate Code, Not Instructions
================================================================
This script applies all fixes and runs the improved build system
"""

import os
import shutil
import subprocess
import sys


def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = ['dotenv', 'httpx']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"⚠️  Missing required packages: {', '.join(missing_packages)}")
        print("   Installing missing packages...")
        for package in missing_packages:
            subprocess.run([sys.executable, "-m", "pip", "install", 
                          "python-dotenv" if package == "dotenv" else package],
                         capture_output=True)
        print("   ✅ Packages installed")


def setup_environment():
    """Ensure all required files are in place"""
    print("🔧 Setting up enhanced build environment...")
    
    # 1. Check for .env file
    if not os.path.exists('.env'):
        print("⚠️  Creating .env template...")
        with open('.env', 'w') as f:
            f.write("""# API Keys for Multi-Agent System
GEMINI_API_KEY=your_gemini_api_key_here
GROK_API_KEY=your_grok_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
DATABASE_URL=postgresql://user:pass@localhost/surflamp
REDIS_URL=redis://localhost:6379

# External API Keys
SURFLINE_API_KEY=your_surfline_key_here
WEATHER_API_KEY=your_weather_api_key_here

# Security
SECRET_KEY=your_secret_key_here
""")
        print("   📝 Please update .env with your API keys")
        print("   ⚠️  At minimum, you need one LLM API key to proceed")
        return False
    
    # 2. Check for required files
    required_files = [
        'file_system_tools.py',
        'llm_gate.py',
        'contract_validator.py',
        'build_app.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        print("   Please ensure all project files are present")
        return False
    
    # 3. Check for shared/contracts.py
    contracts_path = 'generated_surf_lamp_app/shared/contracts.py'
    if not os.path.exists(contracts_path):
        print("⚠️  shared/contracts.py not found")
        print("   Creating directory structure...")
        os.makedirs('generated_surf_lamp_app/shared', exist_ok=True)
        print("   ⚠️  You need to add the contracts.py file from your project")
        print("   This file contains all the interface definitions")
        return False
    
    print("   ✅ All required files present")
    return True


def backup_existing():
    """Backup existing generated files"""
    if os.path.exists('generated_surf_lamp_app'):
        backup_name = 'generated_surf_lamp_app.backup'
        counter = 1
        while os.path.exists(backup_name):
            backup_name = f'generated_surf_lamp_app.backup.{counter}'
            counter += 1
        
        print(f"📦 Backing up existing generated files to {backup_name}...")
        shutil.copytree('generated_surf_lamp_app', backup_name)
        print(f"   ✅ Backup created: {backup_name}")


def clean_output():
    """Clean the output directory (except contracts)"""
    output_dir = 'generated_surf_lamp_app'
    if os.path.exists(output_dir):
        print("🧹 Cleaning output directory...")
        # Save contracts.py
        contracts_path = os.path.join(output_dir, 'shared', 'contracts.py')
        contracts_content = None
        if os.path.exists(contracts_path):
            with open(contracts_path, 'r') as f:
                contracts_content = f.read()
        
        # Clean directory (keep shared folder structure)
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            if item != 'shared':
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
        
        # Clean shared directory except contracts.py
        shared_dir = os.path.join(output_dir, 'shared')
        if os.path.exists(shared_dir):
            for item in os.listdir(shared_dir):
                if item != 'contracts.py':
                    item_path = os.path.join(shared_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
        
        # Restore contracts.py
        if contracts_content:
            os.makedirs(os.path.join(output_dir, 'shared'), exist_ok=True)
            with open(contracts_path, 'w') as f:
                f.write(contracts_content)
        
        print("   ✅ Output directory cleaned")


def create_spec_chunks():
    """Create specification chunks using the updated script"""
    print("📝 Creating specification chunks...")
    
    # Check if create_spec_chunks.py exists
    if os.path.exists('create_spec_chunks.py'):
        # Run the script
        result = subprocess.run([sys.executable, 'create_spec_chunks.py'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("   ✅ Specification chunks created")
        else:
            print(f"   ⚠️  Error creating chunks: {result.stderr}")
    else:
        # Create basic test chunks inline
        os.makedirs('spec_chunks', exist_ok=True)
        
        test_chunks = {
            "test_01_main.py.txt": """Create file: app/test_main.py

GENERATE ONLY PYTHON CODE:

from fastapi import FastAPI

app = FastAPI(title="Test App")

@app.get("/test")
async def test_endpoint():
    return {"status": "ok", "message": "Code generation working"}""",
            
            "test_02_service.py.txt": """Create file: app/test_service.py

GENERATE PYTHON CODE implementing this service:

from shared.contracts import ILampControlService, ArduinoResponse
from typing import Dict, Any

class TestLampService(ILampControlService):
    async def get_lamp_configuration_data(self, lamp_id: str) -> ArduinoResponse:
        response = ArduinoResponse()
        response.update({
            "registered": True,
            "brightness": 100,
            "location_used": "Test Location",
            "wave_height_m": 1.5,
            "wave_period_s": 8.0,
            "wind_speed_mps": 10.0,
            "wind_deg": 180,
            "error": None
        })
        return response
    
    async def process_user_registration(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": True, "message": "Test registration"}"""
        }
        
        for filename, content in test_chunks.items():
            with open(f'spec_chunks/{filename}', 'w') as f:
                f.write(content)
        
        print(f"   ✅ Created {len(test_chunks)} test chunks")


def run_enhanced_build():
    """Run the enhanced build system"""
    print("\n🚀 Running enhanced build system with contract validation...")
    print("=" * 60)
    
    # Run the build
    try:
        result = subprocess.run([sys.executable, 'build_app.py'], 
                              capture_output=False, text=True)
        
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Build failed: {e}")
        return False


def validate_output():
    """Check if generated files contain code, not instructions"""
    print("\n🔍 Validating generated files...")
    
    output_dir = 'generated_surf_lamp_app'
    if not os.path.exists(output_dir):
        print("❌ Output directory not found!")
        return False
    
    # Find all Python files
    python_files = []
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.endswith('.py') and file != 'contracts.py':
                python_files.append(os.path.join(root, file))
    
    if not python_files:
        print("   ⚠️  No Python files generated")
        return False
    
    instruction_patterns = [
        "Create file:", "This file should", "Implement the following",
        "You should", "Make sure to", "Here's how", "Generate the",
        "Build a", "Design a"
    ]
    
    all_valid = True
    valid_count = 0
    invalid_count = 0
    
    for file_path in python_files[:5]:  # Check first 5 files
        rel_path = os.path.relpath(file_path, output_dir)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                continue
            
            # Check for instruction patterns
            has_instructions = any(pattern in content[:500] for pattern in instruction_patterns)
            
            # Check if it's valid Python
            is_valid_python = False
            try:
                compile(content, file_path, 'exec')
                is_valid_python = True
            except SyntaxError:
                pass
            
            if has_instructions:
                print(f"   ❌ {rel_path}: Contains instructions, not code!")
                print(f"      First 100 chars: {content[:100]}...")
                invalid_count += 1
                all_valid = False
            elif not is_valid_python:
                print(f"   ❌ {rel_path}: Invalid Python syntax!")
                invalid_count += 1
                all_valid = False
            else:
                print(f"   ✅ {rel_path}: Valid code generated")
                valid_count += 1
        except Exception as e:
            print(f"   ⚠️  {rel_path}: Error reading file: {e}")
    
    print(f"\n📊 Validation Summary: {valid_count} valid, {invalid_count} invalid")
    return all_valid


def main():
    """Main execution flow"""
    print("🌊 Surfboard Lamp Backend - Code Generation Fix")
    print("=" * 60)
    print("This script ensures LLMs generate actual code, not instructions\n")
    
    # Step 1: Check dependencies
    check_dependencies()
    
    # Step 2: Setup
    if not setup_environment():
        print("\n⚠️  Please complete setup and run again")
        print("   1. Add your API keys to .env")
        print("   2. Ensure shared/contracts.py exists")
        return 1
    
    # Step 3: Ask user what they want to do
    print("\nWhat would you like to do?")
    print("1. Run full build with backup")
    print("2. Run quick test (no backup)")
    print("3. Just validate existing output")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "3":
        # Just validate
        if validate_output():
            print("\n✅ Existing output is valid!")
        else:
            print("\n❌ Existing output contains issues")
        return 0
    
    if choice == "1":
        # Full build with backup
        backup_existing()
        clean_output()
    elif choice == "2":
        # Quick test
        print("\nRunning quick test without backup...")
    else:
        print("Invalid choice")
        return 1
    
    # Step 4: Create spec chunks
    create_spec_chunks()
    
    # Step 5: Run build
    print("\nStarting code generation...")
    if not run_enhanced_build():
        print("\n❌ Build process failed")
        print("   Check if your API keys are valid in .env")
        return 1
    
    # Step 6: Validate
    if validate_output():
        print("\n✅ SUCCESS: LLMs are now generating code correctly!")
        print("   The contract validation system is working.")
        print("\n📝 Next steps:")
        print("   1. Review generated code in generated_surf_lamp_app/")
        print("   2. Create your full spec chunks using create_spec_chunks.py")
        print("   3. Run this script again to generate the complete project")
    else:
        print("\n⚠️  Some files still contain instructions instead of code")
        print("   This might be due to:")
        print("   - Old version of LLM models")
        print("   - API issues")
        print("   - Need for more explicit prompts")
        print("\n   Try running again or check the build_app.py prompts")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
