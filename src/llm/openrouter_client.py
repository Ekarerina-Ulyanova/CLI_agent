"""
OpenRouter LLM client implementation using LangChain.
"""

import json
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, BaseMessage

from src.utils.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OpenRouterClient:
    """
    Client for interacting with OpenRouter API via LangChain.
    """
    
    def __init__(self, temperature: float = 0.1, max_tokens: int = 4000):
        """
        Initialize OpenRouter client.
        
        Args:
            temperature (float): Sampling temperature (0-2)
            max_tokens (int): Maximum tokens to generate
        """
        try:
            base_url = settings.openrouter_base_url.strip()
            model = settings.openrouter_model.strip()

            if not base_url.startswith("https://openrouter.ai/api/v1"):
                logger.warning(f"Base URL might be incorrect: {base_url}")
                if "openrouter.ai" in base_url and "/api/v1" not in base_url:
                    base_url = "https://openrouter.ai/api/v1"
            
            logger.info(f"Initializing OpenRouter with:")
            logger.info(f"  Base URL: {base_url}")
            logger.info(f"  Model: {model}")
            logger.info(f"  API Key: {'Set' if settings.openrouter_api_key else 'Not set'}")
            
            self.llm = ChatOpenAI(
                api_key=settings.openrouter_api_key,
                base_url=base_url,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30,
                max_retries=2
            )

            self.base_url = base_url
            self.model_name = model
            
            logger.info(f"✓ OpenRouter client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter client: {e}")
            raise
    
    def generate(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text using the LLM.
        
        Args:
            messages (List[BaseMessage]): List of message objects
            temperature (Optional[float]): Override default temperature
            max_tokens (Optional[int]): Override default max tokens
            
        Returns:
            str: Generated text response
        """
        try:
            if temperature is not None or max_tokens is not None:
                llm_kwargs = {
                    "api_key": settings.openrouter_api_key,
                    "base_url": self.base_url,
                    "model": self.model_name,
                    "temperature": temperature if temperature is not None else 0.1,
                    "max_tokens": max_tokens if max_tokens is not None else 4000,
                    "timeout": 30,
                    "max_retries": 2
                }
                llm_to_use = ChatOpenAI(**llm_kwargs)
            else:
                llm_to_use = self.llm

            response = llm_to_use.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")

            error_str = str(e)
            if "404" in error_str:
                logger.error(f"OpenRouter API endpoint not found. Check URL: {self.base_url}")
                logger.error("Make sure to use: https://openrouter.ai/api/v1")
            elif "401" in error_str or "403" in error_str:
                logger.error("Unauthorized. Check OPENROUTER_API_KEY in .env")
            elif "429" in error_str:
                logger.error("Rate limit exceeded. Please wait and try again.")
            elif "model" in error_str.lower():
                logger.error(f"Model may not be available. Check OPENROUTER_MODEL: {self.model_name}")
            else:
                logger.error(f"Unknown error: {error_str}")
            
            raise
    
    def test_connection(self) -> bool:
        """
        Test connection to OpenRouter API.
        
        Returns:
            bool: True if connection successful
        """
        try:
            logger.info("Testing OpenRouter connection...")

            messages = [
                SystemMessage(content="You are a test assistant. Respond with 'OK' if you can hear me."),
                HumanMessage(content="Test connection. Say 'OK' if working.")
            ]
            
            response = self.generate(messages, max_tokens=10)
            
            if response and len(response) > 0:
                logger.info(f"✓ OpenRouter connection test successful")
                logger.debug(f"Response: {response[:50]}")
                return True
            else:
                logger.warning("OpenRouter connection test returned empty response")
                return False
                
        except Exception as e:
            logger.error(f"✗ OpenRouter connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models from OpenRouter.
        
        Returns:
            List[Dict[str, Any]]: List of available models
        """
        try:
            import requests
            
            headers = {
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/coding-agent",
                "X-Title": "Coding Agent"
            }
            
            # Базовый URL для запроса моделей
            base_url = self.base_url.rstrip('/')
            models_url = f"{base_url}/models"
            
            logger.info(f"Fetching models from: {models_url}")
            
            response = requests.get(
                models_url,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                models = data.get("data", [])
                logger.info(f"Retrieved {len(models)} models")
                return models
            else:
                logger.error(f"Failed to fetch models: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching available models: {e}")
            return []
    
    def create_system_message(self, content: str) -> SystemMessage:
        """
        Create a system message.
        
        Args:
            content (str): Message content
            
        Returns:
            SystemMessage: System message object
        """
        return SystemMessage(content=content)
    
    def create_human_message(self, content: str) -> HumanMessage:
        """
        Create a human message.
        
        Args:
            content (str): Message content
            
        Returns:
            HumanMessage: Human message object
        """
        return HumanMessage(content=content)