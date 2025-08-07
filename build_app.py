# TODO: Add content for build_app.py
import os
import asyncio
from dotenv import load_dotenv
from file_system_tools import create_directory, create_or_write_file, read_document_chunk
from llm_gate import query_gemini_flash, query_grok, query_openai, query_gemini_pro

load_dotenv()

async def run_orchestrator(chunk_content: str) -> str:
    """Asks Gemini Flash to choose a specialist."""
    system_prompt = """You are an expert project manager agent. Your job is to analyze a chunk of a technical document and decide which specialist agent should handle the task.

The specialists are:
- 'Grok': Use for generating Python code (.py files).
- 'ChatGPT': Use for generating infrastructure or config files (Dockerfile, .yml, .gitignore, etc.).
- 'Gemini': Use for generating database schemas (SQL), data files (JSON), and documentation (Markdown).
- 'FileSystem': Use ONLY for creating directories.

Based on the user's prompt, which contains the content of a document chunk, you must respond with ONLY one of the following words: "Grok", "ChatGPT", "Gemini", or "FileSystem"."""
    
    try:
        choice = await query_gemini_flash(system_prompt, chunk_content)
        return choice.strip()
    except Exception as e:
        print(f"⚠️  Orchestrator fallback mode: {e}")
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

async def run_specialist(specialist: str, chunk_content: str) -> str:
    """Calls the chosen specialist to generate the file content."""
    
    if specialist == "Grok":
        system_prompt = """You are an expert Python developer. Based on the following instructions, generate complete, production-ready Python code. 

CRITICAL REQUIREMENTS:
- Follow agent_rules.md conventions (snake_case, type hints, async/await)
- Include proper imports, error handling, and comprehensive docstrings
- For Arduino endpoints, return EXACTLY this JSON format:
{
    "registered": bool,
    "brightness": int,
    "location_used": str,
    "wave_height_m": float | None,
    "wave_period_s": float | None,
    "wind_speed_mps": float | None,
    "wind_deg": int | None,
    "error": str | None
}
- Use structured logging with logger.info/error
- Your response should contain ONLY the code, no explanations."""
        
        return await query_grok(system_prompt, chunk_content)
    
    elif specialist == "ChatGPT":
        system_prompt = """You are an expert DevOps engineer. Based on the following instructions, generate complete configuration or infrastructure files.

REQUIREMENTS:
- Follow agent_rules.md conventions
- Include comprehensive comments explaining choices
- Use environment variables for configuration
- Include health checks and production best practices
- Your response should contain ONLY the file content, no explanations."""
        
        return await query_openai(system_prompt, chunk_content)

    elif specialist == "Gemini":
        system_prompt = """You are an expert data architect and system designer. Based on the following instructions, generate complete database schemas, data models, or system configuration files.

REQUIREMENTS:
- Follow agent_rules.md conventions
- Include proper relationships, constraints, and indexes
- Use async patterns for database operations
- Include comprehensive error handling and logging
- Your response should contain ONLY the code/schema, no explanations."""
        
        return await query_gemini_pro(system_prompt, chunk_content)
    
    return ""

def parse_target_filename(chunk_filename: str, chunk_content: str) -> str:
    """Extract target filename from chunk name and content."""
    # Remove numeric prefix and .txt extension
    base_name = chunk_filename.split('_', 1)[-1].replace('.txt', '')
    
    # Check content for specific filename hints
    lines = chunk_content.split('\n')[:10]  # Check first 10 lines
    for line in lines:
        if 'file:' in line.lower() or 'create' in line.lower():
            # Look for filename patterns
            words = line.split()
            for word in words:
                if '.' in word and len(word.split('.')) == 2:
                    return word
    
    return base_name

async def main():
    """Main function to build the application."""
    spec_dir = "spec_chunks/"
    output_dir = "generated_surf_lamp_app/"
    
    print("🌊 Starting Multi-Agent Surfboard Lamp Backend Builder")
    print("=" * 60)
    
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
    
    for chunk_file in chunk_files:
        print(f"🔄 Processing: {chunk_file}")
        
        # Read chunk content
        chunk_path = os.path.join(spec_dir, chunk_file)
        chunk_content = read_document_chunk(chunk_path)
        
        if "Error" in chunk_content:
            print(f"❌ {chunk_content}")
            continue
        
        # Get orchestrator decision
        chosen_specialist = await run_orchestrator(chunk_content)
        print(f"   🎯 Orchestrator → {chosen_specialist}")
        
        # Handle directory creation
        if chosen_specialist == "FileSystem":
            print(f"   📁 Creating directory structure...")
            # Parse directory paths from content
            lines = chunk_content.split('\n')
            for line in lines:
                if '/' in line and not line.strip().startswith('#') and '├──' in line or '└──' in line:
                    # Extract directory path from tree structure
                    cleaned_line = line.replace('├──', '').replace('└──', '').replace('│', '').strip()
                    if cleaned_line and '.' not in cleaned_line:  # Skip files, only create directories
                        dir_path = cleaned_line.rstrip('/')
                        if dir_path:
                            result = create_directory(os.path.join(output_dir, dir_path))
                            print(f"      {result}")
                elif line.strip() and not line.startswith('Create') and '/' in line and not '.' in line:
                    # Handle simple directory paths
                    dir_path = line.strip().rstrip('/')
                    if dir_path and not dir_path.startswith('#'):
                        result = create_directory(os.path.join(output_dir, dir_path))
                        print(f"      {result}")
        else:
            # Generate file content
            target_filename = parse_target_filename(chunk_file, chunk_content)
            output_path = os.path.join(output_dir, target_filename)
            
            print(f"   🔧 Generating: {target_filename}")
            generated_content = await run_specialist(chosen_specialist, chunk_content)
            
            result = create_or_write_file(output_path, generated_content)
            print(f"   ✅ {result}")
        
        print()
    
    print("🎉 Multi-agent build process completed!")
    print(f"📂 Output directory: {output_dir}")

def sync_main():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())

if __name__ == "__main__":
    sync_main()
