"""
Enhanced Multi-Agent Build System with Contract Validation
==========================================================
This version ensures LLMs generate actual code, not instructions
"""

import os
import asyncio
from dotenv import load_dotenv
from file_system_tools import create_directory, create_or_write_file, read_document_chunk
from llm_gate import query_gemini_flash, query_grok, query_openai, query_gemini_pro
from contract_validator import ContractValidator
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize contract validator
validator = ContractValidator()


async def run_orchestrator(chunk_content: str) -> str:
    """Asks Gemini Flash to choose a specialist."""
    system_prompt = """You are an expert project manager agent. Your job is to analyze a chunk of a technical document and decide which specialist agent should handle the task.

The specialists are:
- 'Grok': Use for generating Python code (.py files).
- 'ChatGPT': Use for generating infrastructure or config files (Dockerfile, .yml, .gitignore, etc.).
- 'Gemini': Use for generating database schemas (SQL), data files (JSON), and documentation (Markdown).
- 'FileSystem': Use ONLY for creating directories.

Based on the user's prompt, which contains the content of a document chunk, you must respond with ONLY one of the following words: "Grok", "ChatGPT", "Gemini", or "FileSystem".

DO NOT add any explanation. Output ONLY the specialist name."""
    
    try:
        choice = await query_gemini_flash(system_prompt, chunk_content)
        # Clean the response to ensure it's just the specialist name
        choice = choice.strip().split('\n')[0].strip()
        # Remove any quotes or extra characters
        choice = choice.replace('"', '').replace("'", '').strip()
        
        # Validate it's one of our specialists
        valid_specialists = ["Grok", "ChatGPT", "Gemini", "FileSystem"]
        if choice not in valid_specialists:
            logger.warning(f"Invalid specialist choice: {choice}, defaulting to Grok")
            choice = "Grok"
        
        return choice
    except Exception as e:
        logger.warning(f"⚠️  Orchestrator fallback mode: {e}")
        # Fallback to local logic if API fails
        content_lower = chunk_content.lower()
        
        if 'directory' in content_lower or 'folder' in content_lower:
            return "FileSystem"
        elif ('dockerfile' in content_lower or 'docker-compose' in content_lower or 
              '.yml' in chunk_content or '.yaml' in chunk_content):
            return "ChatGPT"
        elif ('.sql' in chunk_content or 'database' in content_lower or 
              'schema' in content_lower):
            return "Gemini"
        elif '.py' in chunk_content or 'python' in content_lower:
            return "Grok"
        else:
            return "Grok"  # Default to Python specialist


async def run_specialist(specialist: str, chunk_content: str, file_path: str) -> str:
    """Calls the chosen specialist to generate the file content."""
    
    # Get required interfaces for this file
    required_interfaces = validator.get_required_interfaces(file_path)
    interface_info = ""
    if required_interfaces:
        interface_info = f"\n\nThis file MUST implement these interfaces from shared.contracts: {', '.join(required_interfaces)}"
    
    if specialist == "Grok":
        system_prompt = f"""You are an expert Python developer. You MUST generate ONLY executable Python code.

CRITICAL REQUIREMENTS:
1. Output ONLY Python code - no explanations, no markdown, no comments outside the code
2. Start your response with imports or the shebang line
3. The code must be syntactically correct and ready to run
4. Import all interfaces from shared.contracts at the top of the file
5. Implement all required methods from the interfaces{interface_info}
6. Include proper error handling and logging
7. DO NOT include any text before or after the code
8. DO NOT use markdown code blocks like ```python
9. DO NOT add explanations or instructions
10. OUTPUT ONLY THE PYTHON CODE

For Arduino endpoints, the response MUST be EXACTLY this format:
{{
    "registered": bool,
    "brightness": int,
    "location_used": str,
    "wave_height_m": float | None,
    "wave_period_s": float | None,
    "wind_speed_mps": float | None,
    "wind_deg": int | None,
    "error": str | None
}}

REMEMBER: OUTPUT ONLY CODE. NO EXPLANATIONS. NO MARKDOWN."""
        
        response = await query_grok(system_prompt, chunk_content)
        
    elif specialist == "ChatGPT":
        system_prompt = f"""You are an expert DevOps engineer. You MUST generate ONLY the configuration/infrastructure file content.

CRITICAL REQUIREMENTS:
1. Output ONLY the file content - no explanations, no markdown
2. Include comments within the file as needed
3. Use environment variables for configuration
4. Include health checks and production best practices{interface_info}
5. DO NOT include any text before or after the file content
6. DO NOT use markdown code blocks
7. DO NOT add explanations
8. OUTPUT ONLY THE FILE CONTENT

REMEMBER: OUTPUT ONLY THE FILE CONTENT. NO EXPLANATIONS."""
        
        response = await query_openai(system_prompt, chunk_content)

    elif specialist == "Gemini":
        system_prompt = f"""You are an expert data architect. You MUST generate ONLY the code/schema content.

CRITICAL REQUIREMENTS:
1. Output ONLY the code/SQL/JSON - no explanations, no markdown
2. For Python files, follow the same rules as Grok specialist
3. Include proper relationships, constraints, and indexes for SQL
4. Use async patterns for database operations{interface_info}
5. DO NOT include any text before or after the code
6. DO NOT use markdown code blocks
7. DO NOT add explanations
8. OUTPUT ONLY THE CODE/SCHEMA

REMEMBER: OUTPUT ONLY CODE. NO EXPLANATIONS."""
        
        response = await query_gemini_pro(system_prompt, chunk_content)
    
    else:
        return ""
    
    # Extract pure code from response
    clean_code = validator.extract_pure_code(response)
    
    # Validate if it's Python code with required interfaces
    if specialist in ["Grok", "Gemini"] and '.py' in file_path and required_interfaces:
        for interface in required_interfaces:
            is_valid, errors = validator.validate_implementation(clean_code, interface)
            if not is_valid:
                logger.warning(f"⚠️  Generated code doesn't properly implement {interface}")
                for error in errors:
                    logger.warning(f"   - {error}")
                
                # Try to fix by generating a stub and asking for completion
                stub = validator.generate_interface_stub(interface)
                if stub:
                    logger.info(f"   🔧 Requesting specialist to complete interface implementation...")
                    
                    fix_prompt = f"""The following code needs to properly implement {interface} from shared.contracts.

Here's a stub with the required methods:

{stub}

Now complete this implementation based on these requirements:
{chunk_content}

OUTPUT ONLY THE COMPLETE PYTHON CODE. NO EXPLANATIONS."""
                    
                    if specialist == "Grok":
                        clean_code = await query_grok(system_prompt, fix_prompt)
                    else:
                        clean_code = await query_gemini_pro(system_prompt, fix_prompt)
                    
                    clean_code = validator.extract_pure_code(clean_code)
    
    # Special validation for Arduino response format
    if 'lamp' in file_path.lower() and 'config' in chunk_content.lower():
        is_valid, errors = validator.validate_arduino_response(clean_code)
        if not is_valid:
            logger.warning("⚠️  Arduino response validation failed:")
            for error in errors:
                logger.warning(f"   - {error}")
    
    return clean_code


def parse_target_filename(chunk_filename: str, chunk_content: str) -> str:
    """Extract target filename from chunk name and content."""
    # Remove numeric prefix and .txt extension
    base_name = chunk_filename.split('_', 1)[-1].replace('.txt', '')
    
    # Check content for specific filename hints
    lines = chunk_content.split('\n')[:10]  # Check first 10 lines
    for line in lines:
        if 'create file:' in line.lower():
            # Extract the file path
            parts = line.split(':', 1)
            if len(parts) > 1:
                file_path = parts[1].strip()
                if '/' in file_path:
                    # Return just the path after 'app/'
                    if 'app/' in file_path:
                        return file_path.split('app/', 1)[1]
                    return file_path
        elif 'file:' in line.lower():
            words = line.split()
            for word in words:
                if '.' in word and len(word.split('.')) == 2:
                    return word
    
    # Handle special cases
    if 'dockerfile' in chunk_filename.lower():
        return 'Dockerfile'
    elif 'docker-compose' in chunk_filename.lower():
        return 'docker-compose.yml'
    elif 'requirements' in chunk_filename.lower():
        return 'requirements.txt'
    
    return base_name


async def validate_generated_code(file_path: str, content: str) -> bool:
    """
    Final validation before writing to file
    """
    # Check if it looks like actual code vs instructions
    instruction_indicators = [
        "Create file:", "Create a file", "This file should",
        "Implement the following", "Here's how to", "You should",
        "The file needs to", "Make sure to", "Follow these",
        "Generate the", "Build a", "Design a"
    ]
    
    first_lines = content[:500].lower()
    for indicator in instruction_indicators:
        if indicator.lower() in first_lines:
            logger.error(f"❌ Generated content appears to be instructions, not code!")
            logger.error(f"   First 200 chars: {content[:200]}...")
            return False
    
    # For Python files, try to compile
    if file_path.endswith('.py'):
        try:
            compile(content, file_path, 'exec')
            logger.info(f"   ✅ Python syntax validation passed")
            return True
        except SyntaxError as e:
            logger.error(f"❌ Python syntax error in generated code: {e}")
            logger.error(f"   Line {e.lineno}: {e.text}")
            return False
    
    return True


async def main():
    """Main function to build the application."""
    spec_dir = "spec_chunks/"
    output_dir = "generated_surf_lamp_app/"
    
    print("🌊 Enhanced Multi-Agent Surfboard Lamp Backend Builder")
    print("   WITH CONTRACT VALIDATION & CODE ENFORCEMENT")
    print("=" * 60)
    
    # Check if contracts file exists
    contracts_file = os.path.join(output_dir, "shared", "contracts.py")
    if os.path.exists(contracts_file):
        print(f"✅ Found shared/contracts.py")
        print(f"🔍 Contract validator loaded with {len(validator.interfaces)} interfaces")
    else:
        print("⚠️  Warning: shared/contracts.py not found")
        print("   Contract validation will be skipped")
    
    # Create output directory
    create_directory(output_dir)
    
    # Get all chunk files
    if not os.path.exists(spec_dir):
        print(f"❌ Error: {spec_dir} directory not found!")
        print("Please create spec chunks first.")
        return
    
    chunk_files = sorted([f for f in os.listdir(spec_dir) if f.endswith('.txt')])
    
    if not chunk_files:
        print(f"❌ No .txt files found in {spec_dir}")
        return
    
    print(f"📁 Found {len(chunk_files)} specification chunks")
    print()
    
    success_count = 0
    failure_count = 0
    
    for chunk_file in chunk_files:
        print(f"🔄 Processing: {chunk_file}")
        
        # Read chunk content
        chunk_path = os.path.join(spec_dir, chunk_file)
        chunk_content = read_document_chunk(chunk_path)
        
        if "Error" in chunk_content:
            print(f"❌ {chunk_content}")
            failure_count += 1
            continue
        
        # Get orchestrator decision
        chosen_specialist = await run_orchestrator(chunk_content)
        print(f"   🎯 Orchestrator → {chosen_specialist}")
        
        # Handle directory creation
        if chosen_specialist == "FileSystem":
            print(f"   📁 Creating directory structure...")
            # Parse directory paths from content
            lines = chunk_content.split('\n')
            dir_count = 0
            for line in lines:
                if '/' in line and not line.strip().startswith('#'):
                    # Extract directory path from tree structure
                    if '├──' in line or '└──' in line:
                        cleaned_line = line.replace('├──', '').replace('└──', '').replace('│', '').strip()
                        if cleaned_line and '.' not in cleaned_line:  # Skip files, only create directories
                            dir_path = cleaned_line.rstrip('/')
                            if dir_path and not dir_path.startswith('─'):
                                result = create_directory(os.path.join(output_dir, dir_path))
                                if "Successfully" in result:
                                    dir_count += 1
            
            print(f"      Created {dir_count} directories")
            success_count += 1
        else:
            # Generate file content
            target_filename = parse_target_filename(chunk_file, chunk_content)
            output_path = os.path.join(output_dir, target_filename)
            
            print(f"   🔧 Generating: {target_filename}")
            
            # Get required interfaces for validation
            required_interfaces = validator.get_required_interfaces(target_filename)
            if required_interfaces:
                print(f"   📋 Must implement: {', '.join(required_interfaces)}")
            
            try:
                generated_content = await run_specialist(chosen_specialist, chunk_content, target_filename)
                
                # Validate before writing
                if await validate_generated_code(target_filename, generated_content):
                    result = create_or_write_file(output_path, generated_content)
                    print(f"   ✅ {result}")
                    success_count += 1
                else:
                    print(f"   ❌ Validation failed, skipping file write")
                    failure_count += 1
            except Exception as e:
                logger.error(f"   ❌ Error generating {target_filename}: {e}")
                failure_count += 1
        
        print()
    
    print("=" * 60)
    print("🎉 Multi-agent build process completed!")
    print(f"📊 Results: {success_count} succeeded, {failure_count} failed")
    print(f"📂 Output directory: {output_dir}")
    
    if failure_count > 0:
        print(f"⚠️  Warning: {failure_count} files failed validation")
        print("   Check the logs above for details")


def sync_main():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())


if __name__ == "__main__":
    sync_main()
