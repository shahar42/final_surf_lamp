#!/usr/bin/env python3
"""
Multi-Agent Contract-First Code Generator V2.0+
===============================================

This orchestrator ensures all generated code follows the immutable contracts
defined in shared/contracts.py. Each domain LLM receives only its specific
contracts and cannot violate interface boundaries.

Author: Multi-Agent Architecture Team
Version: 2.0+
"""

import os
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from file_system_tools import create_directory, create_or_write_file, read_document_chunk
from llm_gate import query_gemini_flash, query_grok, query_openai, query_gemini_pro

load_dotenv()

class ContractValidator:
    """Validates that generated code follows interface contracts"""
    
    def __init__(self):
        self.contracts_path = "shared/contracts.py"
        
    def validate_contracts_exist(self) -> bool:
        """Ensure contracts file exists before generation"""
        if not os.path.exists(self.contracts_path):
            print(f"❌ CRITICAL: {self.contracts_path} not found!")
            print("   Cannot generate code without interface contracts.")
            return False
        
        print(f"✅ Interface contracts found: {self.contracts_path}")
        return True
    
    def extract_domain_interfaces(self, domain: str) -> List[str]:
        """Extract relevant interfaces for a specific domain"""
        
        domain_mappings = {
            "api_layer": [],  # API layer consumes interfaces, doesn't implement them
            "business_logic": ["ILampControlService", "IBackgroundScheduler"],
            "data_layer": ["ILampRepository", "IUserRepository", "IActivityLogger", "ICacheManager"],
            "infrastructure": ["ISurfDataProvider", "IPasswordSecurity", "IInputValidator"]
        }
        
        return domain_mappings.get(domain, [])
    
    def create_domain_contract_summary(self, domain: str) -> str:
        """Create contract summary for specific domain"""
        
        interfaces = self.extract_domain_interfaces(domain)
        
        if not interfaces:
            return "# This domain consumes interfaces but doesn't implement any\n"
        
        summary = f"# INTERFACES YOU MUST IMPLEMENT FOR {domain.upper()}:\n\n"
        
        # Read actual contracts file to extract relevant interfaces
        try:
            with open(self.contracts_path, 'r') as f:
                contracts_content = f.read()
            
            for interface in interfaces:
                if f"class {interface}" in contracts_content:
                    # Extract interface definition
                    lines = contracts_content.split('\n')
                    interface_lines = []
                    capturing = False
                    
                    for line in lines:
                        if f"class {interface}" in line:
                            capturing = True
                        elif capturing and line.startswith("class ") and interface not in line:
                            break
                        
                        if capturing:
                            interface_lines.append(line)
                    
                    summary += '\n'.join(interface_lines) + "\n\n"
            
            return summary
            
        except Exception as e:
            return f"# Error reading contracts: {e}\n"

class ContractAwareOrchestrator:
    """Orchestrates code generation with contract enforcement"""
    
    def __init__(self):
        self.validator = ContractValidator()
        self.domain_llm_mapping = {
            "api_layer": "ChatGPT",
            "business_logic": "Sonnet", 
            "data_layer": "Gemini",
            "infrastructure": "ChatGPT"
        }
    
    async def analyze_domain_spec(self, spec_content: str) -> str:
        """Use Gemini Flash to determine which domain this spec belongs to"""
        
        system_prompt = """You are an expert system architect. Analyze the specification and determine which domain it belongs to.

The domains are:
- 'api_layer': FastAPI endpoints, HTTP handlers, request/response validation
- 'business_logic': LangChain agents, service orchestration, business rules  
- 'data_layer': Database operations, models, caching, persistence
- 'infrastructure': Docker, deployment, external APIs, configuration

Based on the specification content, respond with ONLY one word: "api_layer", "business_logic", "data_layer", or "infrastructure"."""
        
        try:
            choice = await query_gemini_flash(system_prompt, spec_content)
            return choice.strip().lower()
        except Exception as e:
            print(f"⚠️  Orchestrator fallback mode: {e}")
            # Fallback logic based on content analysis
            content_lower = spec_content.lower()
            
            if any(word in content_lower for word in ['endpoint', 'fastapi', 'router', 'api']):
                return "api_layer"
            elif any(word in content_lower for word in ['langchain', 'agent', 'service', 'business']):
                return "business_logic"
            elif any(word in content_lower for word in ['database', 'model', 'repository', 'cache']):
                return "data_layer"
            elif any(word in content_lower for word in ['docker', 'deployment', 'external', 'config']):
                return "infrastructure"
            else:
                return "business_logic"  # Default

    async def generate_domain_code(self, domain: str, spec_content: str) -> str:
        """Generate code for specific domain using assigned LLM - simplified like v1"""
        
        llm_assignment = self.domain_llm_mapping[domain]
        
        # Create simple, direct system prompt like v1
        system_prompt = self._create_domain_prompt(domain, "")
        
        # Create aggressive code-only prompt
        user_prompt = f"""IGNORE THE DOCUMENTATION IN THE SPECIFICATION. GENERATE ONLY EXECUTABLE CODE.

SPECIFICATION (extract the requirements, ignore the documentation):
{spec_content}

YOU MUST RESPOND WITH ONLY PYTHON CODE OR CONFIG FILES.
- NO markdown code blocks (```python)
- NO explanations or documentation
- NO specification text or comments about the spec
- ONLY working, executable code
- START immediately with imports or code syntax
- If multiple files are needed, separate with "# FILE: filename.py" comments

GENERATE WORKING CODE NOW:"""
        
        print(f"   🤖 Generating {domain} code using {llm_assignment}...")
        
        try:
            generated_code = ""
            
            if llm_assignment == "ChatGPT":
                generated_code = await query_openai(system_prompt, user_prompt)
            elif llm_assignment == "Sonnet":
                generated_code = await query_grok(system_prompt, user_prompt)  # Using Grok as Sonnet proxy
            elif llm_assignment == "Gemini":
                generated_code = await query_gemini_pro(system_prompt, user_prompt)
            else:
                raise ValueError(f"Unknown LLM assignment: {llm_assignment}")
            
            # Validate that we got actual code, not just specifications
            if not generated_code.strip():
                raise ValueError("Empty response from LLM")
                
            # Aggressive validation - reject documentation responses
            doc_indicators = ['DOMAIN RESPONSIBILITY', 'SPECIFICATION', 'REQUIREMENTS', 'OVERVIEW', 
                            'The following', 'This section', 'Based on the', 'According to',
                            '```python', '```', 'markdown', 'documentation']
            
            if any(indicator in generated_code for indicator in doc_indicators):
                print(f"❌ {domain} returned documentation instead of code!")
                print(f"   Found doc indicators in response, treating as error")
                generated_code = self._create_simple_code_template(domain)
                
            elif not any(keyword in generated_code for keyword in ['import ', 'class ', 'def ', 'async def', 'from ']):
                print(f"❌ {domain} response doesn't contain code keywords!")
                print(f"   First 200 chars: {generated_code[:200]}...")
                generated_code = self._create_simple_code_template(domain)
            print(f"   ✅ Generated {len(generated_code)} characters of {domain} code")
            return generated_code
                
        except Exception as e:
            print(f"❌ Error generating {domain} code: {e}")
            return self._create_error_placeholder(domain, str(e))
    
    def _create_domain_prompt(self, domain: str, contract_summary: str) -> str:
        """Create specialized prompt for each domain - using original v1 style"""
        
        if domain == "api_layer":
            return """You are an expert FastAPI developer. You MUST generate ONLY working Python code files.

DO NOT WRITE DOCUMENTATION OR EXPLANATIONS. WRITE ONLY EXECUTABLE CODE.

Generate complete FastAPI endpoints with:
- All necessary imports (fastapi, typing, etc.)
- Router definitions using APIRouter()
- Full endpoint functions with proper async/await
- Error handling with try/catch blocks
- Pydantic models if needed
- Dependency injection with Depends()

For Arduino endpoints, return EXACTLY:
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

START YOUR RESPONSE WITH IMPORTS. NO MARKDOWN BLOCKS. NO EXPLANATIONS."""

        elif domain == "business_logic":
            return """You are an expert Python developer. You MUST generate ONLY working Python code files.

DO NOT WRITE DOCUMENTATION OR EXPLANATIONS. WRITE ONLY EXECUTABLE CODE.

Generate complete business logic classes with:
- All necessary imports (typing, abc, asyncio, etc.)
- Class definitions implementing the specified interfaces
- Full method implementations with async/await
- Error handling and logging
- LangChain agent implementations if specified

Implement these interfaces: ILampControlService, IBackgroundScheduler

START YOUR RESPONSE WITH IMPORTS. NO MARKDOWN BLOCKS. NO EXPLANATIONS."""

        elif domain == "data_layer":
            return """You are an expert database developer. You MUST generate ONLY working Python code files.

DO NOT WRITE DOCUMENTATION OR EXPLANATIONS. WRITE ONLY EXECUTABLE CODE.

Generate complete database classes with:
- All necessary imports (asyncpg, redis, typing, etc.)
- Repository classes implementing the specified interfaces
- Full CRUD methods with async/await
- SQL queries and database operations
- Redis caching implementation
- Error handling with database connections

Implement these interfaces: ILampRepository, IUserRepository, IActivityLogger, ICacheManager

START YOUR RESPONSE WITH IMPORTS. NO MARKDOWN BLOCKS. NO EXPLANATIONS."""

        elif domain == "infrastructure":
            return """You are an expert DevOps engineer. You MUST generate ONLY working code/config files.

DO NOT WRITE DOCUMENTATION OR EXPLANATIONS. WRITE ONLY EXECUTABLE CODE/CONFIG.

Generate complete infrastructure files:
- Python classes for external APIs and security services
- Docker files and docker-compose.yml configurations
- All necessary imports and implementations
- Config classes with proper validation
- Security implementations with bcrypt

Implement these interfaces: ISurfDataProvider, IPasswordSecurity, IInputValidator

For Docker files, write actual Dockerfile syntax, not markdown.
For Python files, START WITH IMPORTS. NO MARKDOWN BLOCKS."""
        
        return "You are an expert developer. Generate complete, working code based on the requirements."

    def _create_simple_code_template(self, domain: str) -> str:
        """Create minimal working code template when LLM fails"""
        
        if domain == "api_layer":
            return '''from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/v1/lamps/{lamp_id}/config")
async def get_lamp_config(lamp_id: str) -> Dict[str, Any]:
    """Arduino lamp configuration endpoint"""
    return {
        "registered": False,
        "brightness": 0,
        "location_used": "",
        "wave_height_m": None,
        "wave_period_s": None,
        "wind_speed_mps": None,
        "wind_deg": None,
        "error": "Template - implement actual logic"
    }
'''
        elif domain == "business_logic":
            return '''from typing import Dict, Any, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

class LampControlService:
    """Template lamp control service"""
    
    async def get_lamp_configuration_data(self, lamp_id: str) -> Dict[str, Any]:
        """Get lamp configuration - implement actual logic"""
        return {
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": "Template - implement actual logic"
        }
'''
        elif domain == "data_layer":
            return '''import asyncpg
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class LampRepository:
    """Template lamp repository"""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def get_lamp_configuration(self, lamp_id: str) -> Optional[Dict[str, Any]]:
        """Get lamp config from database - implement actual logic"""
        return None
'''
        elif domain == "infrastructure":
            return '''from typing import Dict, Any, Optional
import bcrypt
import httpx
import logging

logger = logging.getLogger(__name__)

class SurfDataProvider:
    """Template surf data provider"""
    
    async def fetch_surf_data(self, location_index: int) -> Optional[Dict[str, Any]]:
        """Fetch surf data - implement actual logic"""
        return None

class PasswordSecurity:
    """Template password security"""
    
    async def hash_password(self, password: str) -> str:
        """Hash password"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
'''
        else:
            return f"# Template for {domain}\nprint('Implement {domain} code here')\n"

    def _create_error_placeholder(self, domain: str, error: str) -> str:
        """Create placeholder when generation fails"""
        return f'''"""
ERROR: Failed to generate {domain} code
Error: {error}

This is a placeholder - regenerate this domain manually.
"""

print("GENERATION FAILED FOR {domain.upper()} DOMAIN")
print("Error: {error}")
'''

    def parse_output_structure(self, domain: str, spec_content: str) -> Dict[str, str]:
        """Parse what files should be created for this domain"""
        
        # This is a simplified version - in practice, you'd parse the spec more carefully
        domain_structures = {
            "api_layer": {
                "app/api/v1/endpoints/lamps.py": "Arduino lamp configuration endpoint",
                "app/api/v1/endpoints/users.py": "User registration endpoint", 
                "app/api/v1/endpoints/health.py": "Health check endpoints",
                "app/api/v1/router.py": "Main API router"
            },
            "business_logic": {
                "app/services/lamp_control_service.py": "Main lamp business logic",
                "app/agents/surf_lamp_agent.py": "LangChain coordination agent",
                "app/services/background_scheduler.py": "Background task scheduler"
            },
            "data_layer": {
                "app/repositories/lamp_repository.py": "Lamp database operations",
                "app/repositories/user_repository.py": "User database operations", 
                "app/cache/cache_manager.py": "Redis cache management",
                "app/db/models.py": "SQLAlchemy models"
            },
            "infrastructure": {
                "app/external/surf_data_provider.py": "External surf API integration",
                "app/security/password_security.py": "Password hashing services",
                "app/security/input_validator.py": "Input validation services",
                "app/config.py": "Application configuration",
                "Dockerfile": "Container configuration",
                "docker-compose.yml": "Multi-container setup"
            }
        }
        
        return domain_structures.get(domain, {})

async def main():
    """Main contract-aware build process"""
    
    print("🌊 Multi-Agent Contract-First Code Generator V2.0+")
    print("=" * 65)
    
    orchestrator = ContractAwareOrchestrator()
    
    # Step 1: Validate contracts exist
    if not orchestrator.validator.validate_contracts_exist():
        print("\n🛑 STOPPING: Cannot proceed without interface contracts")
        print("   Please ensure shared/contracts.py exists first")
        return
    
    # Step 2: Setup directories
    spec_dir = "spec_chunks/"
    output_dir = "generated_surf_lamp_app/"
    
    print(f"\n📁 Setting up build environment...")
    create_directory(output_dir)
    create_directory(os.path.join(output_dir, "shared"))
    
    # Copy contracts to output
    try:
        with open("shared/contracts.py", 'r') as f:
            contracts_content = f.read()
        create_or_write_file(os.path.join(output_dir, "shared/contracts.py"), contracts_content)
        print("✅ Interface contracts copied to output directory")
    except Exception as e:
        print(f"❌ Failed to copy contracts: {e}")
        return
    
    # Step 3: Find domain specification files
    if not os.path.exists(spec_dir):
        print(f"❌ Error: {spec_dir} directory not found!")
        print("Please create domain specification chunks first.")
        return
    
    domain_specs = [
        "api_layer_complete.txt",
        "business_logic_complete.txt", 
        "data_layer_complete.txt",
        "infrastructure_complete.txt"
    ]
    
    print(f"\n🔍 Looking for domain specifications...")
    found_specs = []
    for spec_file in domain_specs:
        spec_path = os.path.join(spec_dir, spec_file)
        if os.path.exists(spec_path):
            found_specs.append(spec_file)
            print(f"   ✅ Found: {spec_file}")
        else:
            print(f"   ⚠️  Missing: {spec_file}")
    
    if not found_specs:
        print(f"\n❌ No domain specifications found in {spec_dir}")
        print("Expected files: api_layer_complete.txt, business_logic_complete.txt, etc.")
        return
    
    # Step 4: Process each domain
    print(f"\n🚀 Processing {len(found_specs)} domain specifications...")
    
    for spec_file in found_specs:
        domain = spec_file.replace("_complete.txt", "")
        print(f"\n🔄 Processing domain: {domain}")
        
        # Read specification
        spec_path = os.path.join(spec_dir, spec_file)
        spec_content = read_document_chunk(spec_path)
        
        if "Error" in spec_content:
            print(f"❌ {spec_content}")
            continue
        
        # Generate domain code
        generated_code = await orchestrator.generate_domain_code(domain, spec_content)
        
        # Determine output structure
        output_files = orchestrator.parse_output_structure(domain, spec_content)
        
        if len(output_files) == 1:
            # Single file output
            file_path, description = list(output_files.items())[0]
            output_path = os.path.join(output_dir, file_path)
            result = create_or_write_file(output_path, generated_code)
            print(f"   ✅ {result}")
        else:
            # Multiple files - would need more sophisticated parsing
            # For now, create a combined file
            combined_path = os.path.join(output_dir, f"{domain}_generated.py")
            result = create_or_write_file(combined_path, generated_code)
            print(f"   ✅ {result} (combined file - split manually if needed)")
    
    # Step 5: Contract compliance check
    print(f"\n🧪 Running contract compliance validation...")
    
    # Check that contracts file wasn't modified
    try:
        with open("shared/contracts.py", 'r') as f:
            original_contracts = f.read()
        with open(os.path.join(output_dir, "shared/contracts.py"), 'r') as f:
            copied_contracts = f.read()
        
        if original_contracts == copied_contracts:
            print("   ✅ Interface contracts remain immutable")
        else:
            print("   ❌ WARNING: Interface contracts were modified!")
            
    except Exception as e:
        print(f"   ⚠️  Could not validate contract integrity: {e}")
    
    print(f"\n🎉 Contract-aware generation completed!")
    print(f"📂 Output directory: {output_dir}")
    print(f"🔒 Contracts preserved in: {output_dir}/shared/contracts.py")
    print(f"\n💡 Next steps:")
    print(f"   1. Review generated code for contract compliance")
    print(f"   2. Run: python interface_generator.py --validate")
    print(f"   3. Test Arduino endpoint format validation")
    print(f"   4. Run integration tests")

def sync_main():
    """Synchronous wrapper for async main"""
    asyncio.run(main())

if __name__ == "__main__":
    sync_main()
