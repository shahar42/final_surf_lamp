#!/usr/bin/env python3
"""
Flask Database-First Multi-Agent Build System
============================================

Builds the Surfboard Lamp Flask backend using the Database-First approach:
1. Database LLM creates schema + tools contract
2. Tools LLM implements agent tools  
3. Flask LLM creates web application
4. Infrastructure LLM handles config
5. Background processing for lamp updates

Dependencies flow: Database → Contract → Tools → Flask → Config → Background
"""

import os
import asyncio
from dotenv import load_dotenv
from file_system_tools import create_directory, create_or_write_file, read_document_chunk
from llm_gate import query_gemini_flash, query_grok, query_openai, query_gemini_pro
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()


class FlaskOrchestrator:
    """Orchestrator for Flask Database-First architecture"""
    
    def __init__(self):
        # LLM assignments for Flask chunks
        self.chunk_assignments = {
            "01_database_foundation.txt": "Gemini",   # Database + contract specialist
            "02_agent_tools.txt": "Grok",             # Tools implementation specialist  
            "03_flask_app.txt": "ChatGPT",            # Web framework specialist
            "04_config_setup.txt": "ChatGPT",         # Infrastructure specialist
            "05_database_setup.txt": "Gemini",        # Database operations specialist
            "06_background_processing.txt": "Grok"    # Background services specialist
        }
    
    async def run_specialist(self, specialist: str, chunk_content: str, chunk_name: str, project_context: str = "") -> str:
        """Generate code using the appropriate LLM specialist with project context"""
        
        # Prepend project context to chunk content for better LLM understanding
        if project_context:
            enhanced_content = f"""PROJECT CONTEXT (for your reference):
{project_context}

YOUR SPECIFIC TASK:
{chunk_content}"""
        else:
            enhanced_content = chunk_content
        
        # Create domain-specific prompts that demand code generation
        if specialist == "Gemini":
            if "overview" in chunk_name:
                system_prompt = """You are a technical documentation specialist. Generate ONLY markdown documentation files.

CRITICAL: Your response must be valid markdown that can be saved directly to .md files.

REQUIREMENTS:
- Create clear, comprehensive documentation
- Include setup instructions, architecture diagrams, API docs
- Use proper markdown formatting
- NO code blocks unless showing examples
- Start immediately with markdown content

Generate ONLY markdown documentation now:"""
            else:
                system_prompt = """You are a database specialist. Generate ONLY executable SQL/Python code.

CRITICAL: Your response must be valid SQL and Python code that can be saved and executed.

REQUIREMENTS:
- Create SQLAlchemy models with proper relationships
- Generate PostgreSQL schema with constraints
- Include database connection and setup code
- Include tools contract interface definitions
- NO markdown formatting, NO explanations
- Start immediately with imports or SQL statements

Generate ONLY executable database code now:"""
        
        elif specialist == "Grok":
            system_prompt = """You are a Python backend specialist. Generate ONLY executable Python code.

CRITICAL: Your response must be valid Python code that can be saved to .py files and executed.

REQUIREMENTS:
- Import all necessary libraries (requests, SQLAlchemy, logging, etc.)
- Implement all required functions with proper error handling
- Use synchronous patterns (Flask-compatible, not async)
- Include proper logging and exception handling
- NO markdown formatting, NO explanations
- Start immediately with imports and class definitions

Generate ONLY executable Python code now:"""
        
        elif specialist == "ChatGPT":
            system_prompt = """You are a Flask web development specialist. Generate ONLY executable code/config files.

CRITICAL: Your response must be valid Flask Python code or configuration files.

REQUIREMENTS:
- Create Flask applications with proper route definitions
- Include error handling, logging, CORS setup
- Generate configuration files (requirements.txt, .env.example)
- Use Flask patterns and best practices
- NO markdown formatting, NO explanations  
- Start immediately with imports or configuration content

Generate ONLY executable Flask code/config now:"""
        
        try:
            print(f"   🤖 Generating code using {specialist}...")
            
            if specialist == "Gemini":
                response = await query_gemini_pro(system_prompt, enhanced_content)
            elif specialist == "Grok":
                response = await query_grok(system_prompt, enhanced_content)
            elif specialist == "ChatGPT":
                response = await query_openai(system_prompt, enhanced_content)
            else:
                raise ValueError(f"Unknown specialist: {specialist}")
            
            # Clean and validate response
            clean_code = self._clean_llm_response(response, chunk_name)
            return clean_code
            
        except Exception as e:
            logger.error(f"Error with {specialist}: {e}")
            return self._create_error_placeholder(chunk_name, str(e))
    
    def _clean_llm_response(self, response: str, chunk_name: str) -> str:
        """Clean LLM response and validate it's actual code/content"""
        
        # Remove common markdown artifacts
        response = response.replace('```python', '').replace('```sql', '').replace('```', '')
        response = response.replace('```markdown', '').replace('```md', '')
        
        # Remove leading/trailing whitespace
        response = response.strip()
        
        # Check for specification indicators (bad responses)
        spec_indicators = [
            'Create files:', 'GENERATE ONLY', 'REQUIREMENTS:', 'CRITICAL:',
            'Based on the following', 'Implementation should', 'You should create'
        ]
        
        has_spec_text = any(indicator in response[:200] for indicator in spec_indicators)
        if has_spec_text:
            logger.warning(f"⚠️  {chunk_name}: Response contains specification text")
        
        return response
    
    def _create_error_placeholder(self, chunk_name: str, error: str) -> str:
        """Create placeholder when generation fails"""
        return f'''"""
ERROR: Failed to generate {chunk_name}
Error: {error}

This is a placeholder - manually implement or regenerate.
"""

print("GENERATION FAILED FOR {chunk_name}")
print("Error: {error}")
'''

    def _determine_output_files(self, chunk_name: str, content: str) -> dict:
        """Determine what files should be created from a chunk"""
        
        # Extract file paths from chunk content
        files = {}
        lines = content.split('\n')
        
        for line in lines[:20]:  # Check first 20 lines
            if 'Create file:' in line or 'Create files:' in line:
                # Extract file paths
                if ':' in line:
                    paths_part = line.split(':', 1)[1].strip()
                    # Handle multiple files
                    if '\n-' in paths_part or ',' in paths_part:
                        # Multiple files listed
                        for path in paths_part.replace('\n-', ',').split(','):
                            path = path.strip().replace('-', '').strip()
                            if path and '.' in path:
                                files[path] = f"Generated from {chunk_name}"
                    else:
                        # Single file
                        if paths_part and '.' in paths_part:
                            files[paths_part] = f"Generated from {chunk_name}"
        
        # Fallback based on chunk name
        if not files:
            if "database" in chunk_name:
                files = {"database/models.py": "Database models", "database/schema.sql": "Database schema"}
            elif "tools" in chunk_name:
                files = {"tools/agent_tools.py": "Agent tools implementation"}
            elif "flask" in chunk_name:
                files = {"app.py": "Flask application"}
            elif "config" in chunk_name:
                files = {"requirements.txt": "Dependencies", "config.py": "Configuration"}
            elif "background" in chunk_name:
                files = {"background/lamp_processor.py": "Background processor"}
            else:
                files = {f"generated_{chunk_name.replace('.txt', '.py')}": "Generated file"}
        
        return files

    async def validate_generated_content(self, content: str, file_path: str) -> bool:
        """Validate that generated content is appropriate for the file type"""
        
        if not content.strip():
            logger.error(f"❌ {file_path}: Empty content generated")
            return False
        
        # Python file validation
        if file_path.endswith('.py'):
            # Check for basic Python indicators
            python_indicators = ['import ', 'from ', 'class ', 'def ', '@', '=', 'if ', 'try:']
            has_python = any(indicator in content for indicator in python_indicators)
            
            if not has_python:
                logger.error(f"❌ {file_path}: Doesn't look like Python code")
                return False
            
            # Try to compile (basic syntax check)
            try:
                compile(content, file_path, 'exec')
                logger.info(f"✅ {file_path}: Valid Python syntax")
            except SyntaxError as e:
                logger.error(f"❌ {file_path}: Python syntax error - {e}")
                return False
        
        # SQL file validation
        elif file_path.endswith('.sql'):
            sql_indicators = ['CREATE TABLE', 'INSERT INTO', 'SELECT', 'ALTER TABLE']
            has_sql = any(indicator in content.upper() for indicator in sql_indicators)
            
            if not has_sql:
                logger.error(f"❌ {file_path}: Doesn't look like SQL")
                return False
        
        # Markdown file validation
        elif file_path.endswith('.md'):
            md_indicators = ['#', '##', '```', '*', '-', '[', ']']
            has_markdown = any(indicator in content for indicator in md_indicators)
            
            if not has_markdown:
                logger.warning(f"⚠️  {file_path}: Doesn't use markdown formatting")
        
        return True


async def main():
    """Main build process for Flask Database-First architecture"""
    
    print("🌊 Flask Database-First Multi-Agent Build System")
    print("=" * 60)
    
    orchestrator = FlaskOrchestrator()
    
    # Setup directories
    spec_dir = "spec_chunks/"
    output_dir = "generated_flask_app/"
    
    print(f"📁 Setting up build environment...")
    create_directory(output_dir)
    
    # Create project documentation that LLMs will use as context
    project_context = """
# Surfboard Lamp Flask Backend - Architecture Overview

## System Overview
Flask-based backend that fetches surf data from APIs and pushes it to Arduino devices via HTTP POST.

## Database Schema (5 tables):
- users: user_id(PK), username, password_hash, email, location, theme, preferred_output
- lamps: lamp_id(PK), user_id(FK), arduino_id, arduino_ip, last_updated  
- daily_usage: usage_id(PK), website_url, last_updated
- location_websites: location(PK), usage_id(FK)
- usage_lamps: usage_id+lamp_id(composite PK), api_key, http_endpoint

## Agent Tools Workflow:
1. get_all_lamp_ids() → List[int] 
2. get_lamp_details(lamp_id) → {arduino_id, arduino_ip, websites[]}
3. fetch_website_data(api_key, endpoint) → {wave_height_m, wave_period_s, wind_speed_mps, wind_deg, location, timestamp}
4. send_to_arduino(arduino_id, data, format) → HTTP POST to http://{arduino_ip}/api/update
5. update_lamp_timestamp(lamp_id) → bool

## Arduino Communication:
- PUSH-based (not polling)
- HTTP POST to Arduino's local IP address
- Endpoint: POST http://{arduino_ip}/api/update
- Payload: {wave_height_m, wave_period_s, wind_speed_mps, wind_deg, location, timestamp}

## Flask Routes:
- GET /api/lamp/config?id={lamp_id} → {registered, lamp_id, update_interval, status, error}
- POST /api/register → Register user+lamp with {username, email, password, location, lamp_id, arduino_id, arduino_ip}
- GET /health → {status: "ok"}

## Technology Stack:
- Flask (synchronous, not async)
- PostgreSQL + SQLAlchemy + psycopg2
- Requests for HTTP calls
- Background processing with scheduled jobs
"""
    
    # Check for spec chunks
    if not os.path.exists(spec_dir):
        print(f"❌ Error: {spec_dir} directory not found!")
        print("Please run: python create_flask_specs.py")
        return
    
    # Get chunks in dependency order
    chunk_order = [
        "01_database_foundation.txt", 
        "02_agent_tools.txt",
        "03_flask_app.txt",
        "04_config_setup.txt",
        "05_database_setup.txt",
        "06_background_processing.txt"
    ]
    
    print(f"\n🔍 Checking for required chunks...")
    missing_chunks = []
    for chunk in chunk_order:
        if not os.path.exists(os.path.join(spec_dir, chunk)):
            missing_chunks.append(chunk)
        else:
            print(f"   ✅ Found: {chunk}")
    
    if missing_chunks:
        print(f"\n❌ Missing chunks: {missing_chunks}")
        print("Please run: python create_flask_specs.py")
        return
    
    print(f"\n🚀 Processing {len(chunk_order)} chunks in dependency order...")
    
    success_count = 0
    failure_count = 0
    
    for chunk_name in chunk_order:
        print(f"\n🔄 Processing: {chunk_name}")
        
        # Read chunk content
        chunk_path = os.path.join(spec_dir, chunk_name)
        chunk_content = read_document_chunk(chunk_path)
        
        if "Error" in chunk_content:
            print(f"❌ {chunk_content}")
            failure_count += 1
            continue
        
        # Get specialist assignment
        specialist = orchestrator.chunk_assignments[chunk_name]
        print(f"   🎯 Specialist: {specialist}")
        
        # Generate content
        generated_content = await orchestrator.run_specialist(specialist, chunk_content, chunk_name, project_context)
        
        # Determine output files
        output_files = orchestrator._determine_output_files(chunk_name, chunk_content)
        print(f"   📝 Will create: {list(output_files.keys())}")
        
        # Handle multiple files in single response
        if len(output_files) == 1:
            # Single file output
            file_path = list(output_files.keys())[0]
            full_path = os.path.join(output_dir, file_path)
            
            if await orchestrator.validate_generated_content(generated_content, file_path):
                result = create_or_write_file(full_path, generated_content)
                print(f"   ✅ {result}")
                success_count += 1
            else:
                print(f"   ❌ Validation failed for {file_path}")
                failure_count += 1
        else:
            # Multiple files - split content
            # For now, save as combined file with comment headers
            combined_path = os.path.join(output_dir, f"combined_{chunk_name.replace('.txt', '.py')}")
            result = create_or_write_file(combined_path, generated_content)
            print(f"   ✅ {result} (combined - split manually)")
            success_count += 1
    
    # Final summary
    total = success_count + failure_count
    print(f"\n🎉 Flask build completed!")
    print(f"📂 Output directory: {output_dir}")
    print(f"📊 Results: {success_count}/{total} successful, {failure_count} failed")
    
    if success_count > 0:
        print(f"\n📝 Next steps:")
        print(f"   1. Review generated files in {output_dir}")
        print(f"   2. Set up your PostgreSQL database")
        print(f"   3. Update .env with your database credentials")
        print(f"   4. Run: pip install -r requirements.txt")
        print(f"   5. Run: python setup_database.py")
        print(f"   6. Run: python app.py")
    
    if failure_count > 0:
        print(f"\n⚠️  {failure_count} chunks failed - check logs above for details")


def sync_main():
    """Synchronous wrapper for async main"""
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
