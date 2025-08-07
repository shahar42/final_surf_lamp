"""
LLM Gateway - Handles API calls to different LLM providers
"""
import os
import httpx
import json
from typing import Dict, Any
import asyncio
from dotenv import load_dotenv
load_dotenv() 

class LLMGateway:
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.openai_api_key = os.getenv('OPENAI_API_KEY') 
        self.grok_api_key = os.getenv('GROK_API_KEY')
        
    async def query_gemini_flash(self, system_prompt: str, user_prompt: str) -> str:
        """Query Gemini 2.5 Flash for orchestration decisions"""
        if not self.gemini_api_key:
            print("⚠️  GEMINI_API_KEY not found, using simulation mode")
            return self._simulate_orchestrator(user_prompt)
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{system_prompt}\n\nUser request: {user_prompt}"
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 100
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=30.0)
                response.raise_for_status()
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            print(f"❌ Gemini Flash API error: {e}")
            return self._simulate_orchestrator(user_prompt)
    
    async def query_grok(self, system_prompt: str, user_prompt: str) -> str:
        """Query Grok-4 for Python code generation"""
        if not self.grok_api_key:
            print("⚠️  GROK_API_KEY not found, using simulation mode")
            return self._simulate_python_code(user_prompt)
            
        url = "https://api.x.ai/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.grok_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "model": "grok-2-1212",
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"❌ Grok API error: {e}")
            return self._simulate_python_code(user_prompt)
    
    async def query_openai(self, system_prompt: str, user_prompt: str) -> str:
        """Query ChatGPT o1-mini for infrastructure code"""
        if not self.openai_api_key:
            print("⚠️  OPENAI_API_KEY not found, using simulation mode")
            return self._simulate_infra_code(user_prompt)
            
        url = "https://api.openai.com/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 3000
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"❌ OpenAI API error: {e}")
            return self._simulate_infra_code(user_prompt)
    
    async def query_gemini_pro(self, system_prompt: str, user_prompt: str) -> str:
        """Query Gemini 2.5 Pro for data/database code"""
        if not self.gemini_api_key:
            print("⚠️  GEMINI_API_KEY not found, using simulation mode")
            return self._simulate_data_code(user_prompt)
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.gemini_api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{system_prompt}\n\nUser request: {user_prompt}"
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4000
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=60.0)
                response.raise_for_status()
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            print(f"❌ Gemini Pro API error: {e}")
            return self._simulate_data_code(user_prompt)
    
    def _simulate_orchestrator(self, content: str) -> str:
        """Simulate orchestrator decision when API unavailable"""
        content_lower = content.lower()
        
        if 'directory' in content_lower or 'folder' in content_lower:
            return "FileSystem"
        elif ('dockerfile' in content_lower or 'docker-compose' in content_lower or 
              '.yml' in content or '.yaml' in content):
            return "ChatGPT"
        elif ('.sql' in content or 'database' in content_lower or 'schema' in content_lower):
            return "Gemini"
        elif '.py' in content or 'python' in content_lower:
            return "Grok"
        else:
            return "Grok"
    
    def _simulate_python_code(self, content: str) -> str:
        """Generate placeholder Python code"""
        filename = self._extract_filename(content)
        return f'''"""
Generated by: Grok (Simulation Mode)
Purpose: {content[:100]}...
Dependencies: Listed in requirements.txt
"""

# TODO: Replace with actual Grok-generated code
# This is a placeholder for file: {filename}

print("This is a simulated Python file - replace with actual Grok output")
'''
    
    def _simulate_infra_code(self, content: str) -> str:
        """Generate placeholder infrastructure code"""
        filename = self._extract_filename(content)
        return f'''# Generated by: ChatGPT (Simulation Mode)
# Purpose: {content[:100]}...
# File: {filename}

# TODO: Replace with actual ChatGPT-generated infrastructure code
'''
    
    def _simulate_data_code(self, content: str) -> str:
        """Generate placeholder data/database code"""
        filename = self._extract_filename(content)
        return f'''-- Generated by: Gemini Pro (Simulation Mode)
-- Purpose: {content[:100]}...
-- File: {filename}

-- TODO: Replace with actual Gemini-generated database code
'''
    
    def _extract_filename(self, content: str) -> str:
        """Extract filename from content"""
        lines = content.split('\n')[:5]
        for line in lines:
            if 'file:' in line.lower() or 'create' in line.lower():
                words = line.split()
                for word in words:
                    if '.' in word and len(word.split('.')) == 2:
                        return word
        return "unknown_file"

# Convenience functions for backwards compatibility
llm_gateway = LLMGateway()

async def query_gemini_flash(system_prompt: str, user_prompt: str) -> str:
    return await llm_gateway.query_gemini_flash(system_prompt, user_prompt)

async def query_grok(system_prompt: str, user_prompt: str) -> str:
    return await llm_gateway.query_grok(system_prompt, user_prompt)

async def query_openai(system_prompt: str, user_prompt: str) -> str:
    return await llm_gateway.query_openai(system_prompt, user_prompt)

async def query_gemini_pro(system_prompt: str, user_prompt: str) -> str:
    return await llm_gateway.query_gemini_pro(system_prompt, user_prompt)# TODO: Add content for llm_gate.py
