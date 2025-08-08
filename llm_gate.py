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
        """Generate working Python code template"""
        if "endpoint" in content.lower() or "fastapi" in content.lower():
            return '''from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/api/v1/lamps/{lamp_id}/config")
async def get_lamp_config(lamp_id: str) -> Dict[str, Any]:
    return {
        "registered": False,
        "brightness": 0,
        "location_used": "",
        "wave_height_m": None,
        "wave_period_s": None,
        "wind_speed_mps": None,
        "wind_deg": None,
        "error": None
    }
'''
        elif "agent" in content.lower() or "langchain" in content.lower():
            return '''from typing import Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class SurfLampAgent:
    async def process_lamp_request(self, lamp_id: str) -> Dict[str, Any]:
        return {
            "registered": False,
            "brightness": 0,
            "location_used": "",
            "wave_height_m": None,
            "wave_period_s": None,
            "wind_speed_mps": None,
            "wind_deg": None,
            "error": None
        }
'''
        else:
            return '''from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class GeneratedClass:
    async def process_data(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        return {"status": "success", "data": data}
'''
    
    def _simulate_infra_code(self, content: str) -> str:
        """Generate working infrastructure code"""
        if "docker" in content.lower():
            return '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
'''
        elif "config" in content.lower():
            return '''from typing import Optional
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://user:pass@localhost/surflamp"
    redis_url: str = "redis://localhost:6379"
    api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"

settings = Settings()
'''
        else:
            return '''from typing import Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class ExternalService:
    async def fetch_data(self) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/data")
            return response.json()
'''
    
    def _simulate_data_code(self, content: str) -> str:
        """Generate working database code"""
        if "repository" in content.lower():
            return '''import asyncpg
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class LampRepository:
    def __init__(self, db_pool):
        self.db_pool = db_pool
    
    async def get_lamp_config(self, lamp_id: str) -> Optional[Dict[str, Any]]:
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM lamps WHERE lamp_id = $1", lamp_id
            )
            return dict(row) if row else None
    
    async def update_lamp_config(self, lamp_id: str, config: Dict[str, Any]) -> bool:
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE lamps SET brightness = $2 WHERE lamp_id = $1",
                lamp_id, config.get("brightness", 0)
            )
            return "UPDATE 1" in result
'''
        elif "model" in content.lower() or "schema" in content.lower():
            return '''from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Lamp(Base):
    __tablename__ = "lamps"
    
    lamp_id = Column(String, primary_key=True)
    brightness = Column(Integer, default=0)
    location_used = Column(String, default="")
    registered = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
'''
        else:
            return '''import redis.asyncio as redis
from typing import Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def set(self, key: str, value: Dict[str, Any], expire: int = 3600) -> bool:
        return await self.redis.setex(key, expire, json.dumps(value))
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
