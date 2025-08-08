#!/usr/bin/env python3
"""
Multi-Agent Contract-First Code Generator V2.0+ (FIXED)
======================================================

This version combines Version 1's proven chunk-based approach with 
Version 2's contract-first architecture. Uses simple, direct prompts
that explicitly demand code generation, not specifications.

Based on community research: LLMs need unambiguous coding instructions,
not comprehensive architectural documentation.

Author: Multi-Agent Architecture Team  
Version: 2.0+ (Fixed)
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from file_system_tools import create_directory, create_or_write_file, read_document_chunk
from llm_gate import query_gemini_flash, query_grok, query_openai, query_gemini_pro

load_dotenv()

class ContractAwareOrchestrator:
    """Simple orchestrator that uses V1's proven approach with contract awareness"""
    
    def __init__(self):
        # V1's proven LLM assignments based on file types
        self.specialist_mapping = {
            "Grok": "Python specialist - generates .py files",
            "ChatGPT": "Infrastructure specialist - generates config files", 
            "Gemini": "Data specialist - generates SQL, JSON, documentation",
            "FileSystem": "Directory creation only"
        }
    
    async def run_orchestrator(self, chunk_content: str) -> str:
        """V1's proven orchestrator logic - simple and direct"""
        
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
            # V1's proven fallback logic
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
                return "Grok"  # Default
    
    async def run_specialist(self, specialist: str, chunk_content: str) -> str:
        """V1's proven specialist prompts - simple and explicit about code generation"""
        
        if specialist == "Grok":
            system_prompt = """You are a code generation machine. You ONLY generate executable Python code. Never generate explanations, documentation, or specifications.

CRITICAL: Your response must be valid Python code that can be saved directly to a .py file and executed.

REQUIREMENTS:
- Import from shared.contracts for interfaces
- Include all necessary imports at the top
- Use async/await for I/O operations  
- Include error handling with try/except blocks
- NO markdown formatting, NO explanations, NO comments about what the code does
- Start immediately with imports or class definitions

EXAMPLE RESPONSE FORMAT:
```
from fastapi import APIRouter
from shared.contracts import ILampControlService

router = APIRouter()

@router.get("/test")
async def test():
    return {"status": "ok"}
```

Generate ONLY executable Python code now:"""
            
            return await query_grok(system_prompt, chunk_content)
        
        elif specialist == "ChatGPT":
            system_prompt = """You are a configuration file generator. You ONLY generate valid configuration files. Never generate explanations or documentation.

CRITICAL: Your response must be a valid config file that can be saved directly and used immediately.

REQUIREMENTS:
- Generate Docker, YAML, or other config files
- Include all necessary configuration options
- Use environment variables where appropriate
- NO markdown formatting, NO explanations
- Start immediately with the file content

EXAMPLE RESPONSE FORMAT:
```
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
```

Generate ONLY the configuration file content now:"""
            
            return await query_openai(system_prompt, chunk_content)

        elif specialist == "Gemini":
            system_prompt = """You are a SQL and data file generator. You ONLY generate executable SQL, JSON, or data files. Never generate explanations or documentation.

CRITICAL: Your response must be valid SQL/JSON/data that can be saved directly to a file and executed/used immediately.

REQUIREMENTS:
- Generate CREATE TABLE statements, INSERT queries, or JSON data
- Include proper constraints and relationships
- Use correct SQL syntax for PostgreSQL
- NO markdown formatting, NO explanations
- Start immediately with SQL commands or JSON structure

EXAMPLE RESPONSE FORMAT:
```
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);
```

Generate ONLY the SQL/data file content now:"""
            
            return await query_gemini_pro(system_prompt, chunk_content)
        
        return ""

    def parse_target_filename(self, chunk_filename: str, chunk_content: str) -> str:
        """V1's proven filename parsing logic"""
        
        # Remove numeric prefix and .txt extension
        base_name = chunk_filename.split('_', 1)[-1].replace('.txt', '')
        
        # Check content for specific filename hints  
        lines = chunk_content.split('\n')[:10]
        for line in lines:
            if 'file:' in line.lower() or 'create' in line.lower():
                words = line.split()
                for word in words:
                    if '.' in word and len(word.split('.')) == 2:
                        return word
        
        return base_name

    def validate_generated_code(self, content: str, filename: str) -> bool:
        """Validate that generated content is actually code, not specifications"""
        
        if not content.strip():
            return False
        
        # Check for code indicators
        code_indicators = [
            'import ', 'from ', 'class ', 'def ', 'async def', 'CREATE TABLE', 
            'SELECT', 'INSERT', 'version:', 'services:', 'FROM python:', 
            '#!/', 'export ', 'ENV ', 'RUN ', 'COPY ', '@', 'router = '
        ]
        has_code_indicators = any(indicator in content for indicator in code_indicators)
        
        # Check for specification indicators (bad)
        spec_indicators = [
            'DOMAIN RESPONSIBILITY:', 'INTERFACE CONTRACTS:', 'IMPLEMENTATION REQUIREMENTS:',
            'CRITICAL ENDPOINT SPECIFICATIONS:', 'REQUIRED DIRECTORY STRUCTURE:',
            'Implementation Requirements:', 'Error Handling:', 'PURPOSE:', 'SPECIFICATION',
            'Create file:', 'Generate complete', 'Based on the following', 'API Layer Complete',
            'Business Logic Layer', 'Data Layer Complete', 'Infrastructure Layer'
        ]
        has_spec_indicators = any(indicator in content for indicator in spec_indicators)
        
        # Check for markdown formatting (usually indicates documentation)
        markdown_indicators = ['```python', '```sql', '```yaml', '```dockerfile', '## ', '### ', '**']
        has_markdown = any(indicator in content for indicator in markdown_indicators)
        
        if has_spec_indicators:
            print(f"   ❌ {filename}: Contains specification text, not code")
            print(f"      Found: {[ind for ind in spec_indicators if ind in content]}")
            return False
        
        if has_markdown:
            print(f"   ❌ {filename}: Contains markdown formatting, likely documentation")
            return False
        
        if not has_code_indicators:
            print(f"   ⚠️  {filename}: No clear code indicators found")
            print(f"      First 150 chars: {content[:150]}...")
            # Still allow it through in case it's valid but minimal code
            return True
        
        print(f"   ✅ {filename}: Validated as actual code")
        return True

async def main():
    """Main function using V1's proven approach with contract awareness"""
    
    print("🌊 Multi-Agent Contract-First Code Generator V2.0+ (FIXED)")
    print("=" * 65)
    
    orchestrator = ContractAwareOrchestrator()
    
    # V1's proven directory setup
    spec_dir = "spec_chunks/"
    output_dir = "generated_surf_lamp_app/"
    
    print(f"📁 Setting up build environment...")
    create_directory(output_dir)
    create_directory(os.path.join(output_dir, "shared"))
    
    # Copy contracts to output (V2 improvement)
    try:
        if os.path.exists("shared/contracts.py"):
            with open("shared/contracts.py", 'r') as f:
                contracts_content = f.read()
            create_or_write_file(os.path.join(output_dir, "shared/contracts.py"), contracts_content)
            print("✅ Interface contracts copied to output directory")
        else:
            print("⚠️  shared/contracts.py not found - continuing without contracts")
    except Exception as e:
        print(f"⚠️  Could not copy contracts: {e}")
    
    # V1's proven chunk processing
    if not os.path.exists(spec_dir):
        print(f"❌ Error: {spec_dir} directory not found!")
        print("Please create specification chunks first.")
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
        
        # V1's proven chunk reading
        chunk_path = os.path.join(spec_dir, chunk_file)
        chunk_content = read_document_chunk(chunk_path)
        
        if "Error" in chunk_content:
            print(f"❌ {chunk_content}")
            failure_count += 1
            continue
        
        # V1's proven orchestrator decision
        chosen_specialist = await orchestrator.run_orchestrator(chunk_content)
        print(f"   🎯 Orchestrator → {chosen_specialist}")
        
        # Handle directory creation (V1 logic)
        if chosen_specialist == "FileSystem":
            print(f"   📁 Creating directory structure...")
            lines = chunk_content.split('\n')
            for line in lines:
                if ('├──' in line or '└──' in line) and '.' not in line:
                    cleaned_line = line.replace('├──', '').replace('└──', '').replace('│', '').strip()
                    if cleaned_line and cleaned_line.endswith('/'):
                        dir_path = cleaned_line.rstrip('/')
                        if dir_path:
                            result = create_directory(os.path.join(output_dir, dir_path))
                            print(f"      {result}")
            success_count += 1
        else:
            # V1's proven file generation
            target_filename = orchestrator.parse_target_filename(chunk_file, chunk_content)
            output_path = os.path.join(output_dir, target_filename)
            
            print(f"   🔧 Generating: {target_filename}")
            generated_content = await orchestrator.run_specialist(chosen_specialist, chunk_content)
            
            # V2 improvement: Validate generated content
            if orchestrator.validate_generated_code(generated_content, target_filename):
                result = create_or_write_file(output_path, generated_content)
                print(f"   ✅ {result}")
                success_count += 1
            else:
                print(f"   ❌ Skipped {target_filename}: Generated specifications instead of code")
                print(f"      Try rephrasing the chunk to be more explicit about code generation")
                failure_count += 1
        
        print()
    
    # Final summary
    total = success_count + failure_count
    print("🎉 Multi-agent build process completed!")
    print(f"📂 Output directory: {output_dir}")
    print(f"📊 Results: {success_count}/{total} successful, {failure_count} failed")
    
    if failure_count > 0:
        print(f"\n💡 To fix failures:")
        print(f"   - Make chunk instructions more explicit about code generation")
        print(f"   - Start chunks with 'Create file: filename' for clarity")
        print(f"   - Use imperative language: 'Implement', 'Generate', 'Create'")

def sync_main():
    """Synchronous wrapper for the async main function."""
    asyncio.run(main())

if __name__ == "__main__":
    sync_main()
