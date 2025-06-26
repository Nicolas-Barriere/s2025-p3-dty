"""
API client for interacting with Albert API.

This module handles all low-level API communication with the Albert service.
"""

import json
import logging
import requests
from typing import Dict, List, Optional, Any

from .config import AlbertConfig
from .exceptions import AlbertAPIError

logger = logging.getLogger(__name__)


class AlbertAPIClient:
    """Client for interacting with Albert API."""
    
    def __init__(self, config: AlbertConfig):
        """
        Initialize the Albert API client.
        
        Args:
            config: Configuration for Albert API
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
        })
    
    def make_request(
        self, 
        messages: List[Dict[str, str]], 
        functions: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to Albert API with optional function calling.
        
        Args:
            messages: List of message objects for the conversation
            functions: Optional list of function definitions for function calling
            
        Returns:
            Response from Albert API
            
        Raises:
            AlbertAPIError: If API request fails
        """
        try:
            payload = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            
            # Add function calling parameters if functions are provided
            if functions:
                payload["tools"] = [{"type": "function", "function": func} for func in functions]
                payload["tool_choice"] = "auto"
            
            logger.info(f"Making request to Albert API with {len(messages)} messages")
            if functions:
                logger.info(f"Including {len(functions)} available tools")
            
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info("Successfully received response from Albert API")
            return result
            
        except requests.RequestException as e:
            logger.error(f"Failed to make request to Albert API: {e}")
            raise AlbertAPIError(f"API request failed: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response from Albert API: {e}")
            raise AlbertAPIError(f"Invalid JSON response: {e}")
