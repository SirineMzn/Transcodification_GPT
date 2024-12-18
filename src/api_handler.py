"""
API handling module for OpenAI interactions.
Manages all API calls and response processing.
"""
from typing import List, Dict, Any, Optional
import openai
import json
import time
import logging
from config import APIConfig
import streamlit as st

logger = logging.getLogger(__name__)

class APIHandler:
    def __init__(self):
        """Initialize API handler with OpenAI key from Streamlit secrets."""
        self.api_key = st.secrets["API_key"]["openai_api_key"]
        openai.api_key = self.api_key
        self.response_format = self._get_response_format()

    def _get_response_format(self) -> Dict:
        """
        Define API response format schema.
        
        Returns:
            Dict: Response format specification
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "account_matching_response",
                "schema": {
                    "type": "object",
                    "properties": {
                        "final_answer": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "account_number": {"type": "string"},
                                    "label": {"type": "string"},
                                    "coa_account": {"type": "string"},
                                    "coa_label": {"type": "string"},
                                    "justification": {"type": "string"}
                                },
                                "required": ["account_number", "label", "coa_account", 
                                           "coa_label", "justification"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["final_answer"],
                    "additionalProperties": False
                },
                "strict": True
            }
        }

    async def process_batch(
        self, 
        prompt: str, 
        coa_accounts: List[str], 
        retries: int = APIConfig.MAX_RETRIES
    ) -> Optional[List[Dict]]:
        """
        Process a batch of accounts through the API.
        
        Args:
            prompt: Formatted prompt text
            coa_accounts: List of COA accounts to include
            retries: Number of retry attempts
            
        Returns:
            Optional[List[Dict]]: Processed account mappings
        """
        for attempt in range(retries):
            try:
                response = await self._make_api_call(prompt, coa_accounts)
                return self._parse_response(response)
            except Exception as e:
                logger.error(f"API call failed (attempt {attempt + 1}/{retries}): {str(e)}")
                if attempt < retries - 1:
                    time.sleep(APIConfig.RETRY_DELAY)
                else:
                    raise
                    
        return None

    async def _make_api_call(self, prompt: str, coa_accounts: List[str]) -> Dict:
        """
        Make API call to OpenAI.
        
        Args:
            prompt: Formatted prompt text
            coa_accounts: List of COA accounts
            
        Returns:
            Dict: API response
        """
        messages = [
            {"role": "system", "content": "You are an assistant that provides structured JSON responses based on the schema."},
            {"role": "user", "content": f"{prompt}\n\nExisting accounts in PCG:\n{chr(10).join(coa_accounts)}"}
        ]
        
        return await openai.ChatCompletion.acreate(
            model=APIConfig.MODEL,
            messages=messages,
            response_format=self.response_format,
            temperature=APIConfig.TEMPERATURE,
            max_tokens=APIConfig.MAX_TOKENS
        )

    def _parse_response(self, response: Dict) -> List[Dict]:
        """
        Parse API response into structured format.
        
        Args:
            response: Raw API response
            
        Returns:
            List[Dict]: Processed account mappings
        """
        try:
            content = response['choices'][0]['message']['content']
            parsed = json.loads(content)
            final_answer = parsed["final_answer"]
            
            if isinstance(final_answer, list):
                return final_answer
            elif isinstance(final_answer, dict):
                return [final_answer]
            else:
                raise ValueError("Unexpected format for 'final_answer'")
                
        except Exception as e:
            logger.error(f"Error parsing API response: {str(e)}")
            raise
