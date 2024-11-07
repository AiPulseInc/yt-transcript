from dotenv import load_dotenv
import os
import logging

load_dotenv()

logger = logging.getLogger(__name__)

class WebshareConfig:
    # Get proxy details from environment variables
    PROXY_USERNAME = os.getenv('PROXY_USERNAME')
    PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
    PROXY_ADDRESS = os.getenv('PROXY_ADDRESS')
    PROXY_PORT = os.getenv('PROXY_PORT')
    
    @classmethod
    def get_proxy(cls):
        """Get proxy configuration"""
        if not all([cls.PROXY_USERNAME, cls.PROXY_PASSWORD, cls.PROXY_ADDRESS, cls.PROXY_PORT]):
            logger.error("One or more proxy configuration values missing in environment variables")
            return None
            
        proxy_url = f"http://{cls.PROXY_USERNAME}:{cls.PROXY_PASSWORD}@{cls.PROXY_ADDRESS}:{cls.PROXY_PORT}"
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }