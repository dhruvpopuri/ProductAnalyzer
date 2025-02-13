import logging
from typing import Dict, Any, List
import groq
from django.conf import settings
import json
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class GroqClient:
    """Generic client for interacting with Groq's LLM API with retry logic and error handling"""
    
    def __init__(self):
        self.client = groq.Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.2-3b-preview"
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    def generate_completion(
        self, 
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a completion from the LLM
        
        Args:
            prompt: The prompt to send to the LLM
            temperature: Controls randomness (0-1)
            max_tokens: Maximum tokens in response
            **kwargs: Additional arguments to pass to the API
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error making request to Groq: {str(e)}")
            raise

    def generate_structured_completion(
        self, 
        prompt: str, 
        expected_format: Dict,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> Dict:
        """
        Generate a structured JSON response from the LLM
        """
        formatted_prompt = f"""
        {prompt}
        
        You must respond with valid JSON in exactly this format. Do not include any additional text or explanation:
        {json.dumps(expected_format, indent=2)}
        
        Ensure your response is valid JSON and matches the exact format above.
        """
        
        try:
            result = self.generate_completion(
                prompt=formatted_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return json.loads(result)
        except json.JSONDecodeError as e:
            logger.debug(f"Raw response: {result}")
            logger.error(f"Error parsing JSON response: {str(e)}")
            return None
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return None