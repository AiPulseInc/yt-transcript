from dotenv import load_dotenv
import os
import requests
import logging
import random
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

logger = logging.getLogger(__name__)

class ProxyStats:
    def __init__(self):
        self.success_count = 0
        self.fail_count = 0
        self.last_success = None
        self.last_used = None

    @property
    def success_rate(self):
        total = self.success_count + self.fail_count
        return (self.success_count / total * 100) if total > 0 else 0

class WebshareConfig:
    API_BASE_URL = "https://proxy.webshare.io/api/v2"
    API_TOKEN = os.getenv('WEBSHARE_API_TOKEN', '').strip()
    MAX_PROXIES = 5
    
    # Class variable to store proxy statistics
    proxy_stats = defaultdict(ProxyStats)
    
    @classmethod
    def update_proxy_stats(cls, proxy_address: str, success: bool):
        """Update statistics for a proxy"""
        stats = cls.proxy_stats[proxy_address]
        if success:
            stats.success_count += 1
            stats.last_success = datetime.now()
        else:
            stats.fail_count += 1
        stats.last_used = datetime.now()
        
        logger.info(f"Proxy {proxy_address} stats - Success rate: {stats.success_rate:.1f}% "
                   f"(Success: {stats.success_count}, Fail: {stats.fail_count})")
    
    @classmethod
    def get_proxy_list(cls) -> List[Dict[str, str]]:
        """Get a list of available proxies from Webshare API"""
        if not cls.API_TOKEN:
            logger.error("Webshare API token not found in environment variables")
            return []
            
        try:
            token = cls.API_TOKEN.replace('Token ', '')
            
            params = {
                'mode': 'direct',
                'page': 1,
                'page_size': cls.MAX_PROXIES
            }
            
            response = requests.get(
                f"{cls.API_BASE_URL}/proxy/list/",
                params=params,
                headers={
                    "Authorization": f"Token {token}"
                }
            )
            
            if response.status_code == 200:
                proxy_list = response.json()
                valid_proxies = []
                
                for proxy in proxy_list.get('results', []):
                    if not all(key in proxy for key in ['username', 'password', 'proxy_address', 'port']):
                        continue
                    if not proxy.get('valid', False):
                        continue
                        
                    proxy_url = f"http://{proxy['username']}:{proxy['password']}@{proxy['proxy_address']}:{proxy['port']}"
                    proxy_address = f"{proxy['proxy_address']}:{proxy['port']}"
                    
                    # Get stats for this proxy
                    stats = cls.proxy_stats[proxy_address]
                    success_rate = stats.success_rate
                    last_success = stats.last_success.strftime('%Y-%m-%d %H:%M:%S') if stats.last_success else 'Never'
                    
                    logger.info(f"Proxy {proxy_address} - Success rate: {success_rate:.1f}%, Last success: {last_success}")
                    
                    valid_proxies.append({
                        "http": proxy_url,
                        "https": proxy_url,
                        "address": proxy_address,
                        "success_rate": success_rate,
                        "last_success": stats.last_success,
                        "success_count": stats.success_count
                    })
                
                # Sort proxies by success rate and success count
                valid_proxies.sort(key=lambda x: (
                    -x['success_rate'],  # Higher success rate first
                    -x['success_count'],  # More successful attempts first
                    -(datetime.now() - x['last_success']).total_seconds() if x['last_success'] else float('-inf')  # More recent success first
                ))
                
                logger.info(f"Retrieved {len(valid_proxies)} valid proxies")
                return valid_proxies
                    
            elif response.status_code == 429:
                logger.error("Webshare API rate limit exceeded")
            elif response.status_code == 401:
                logger.error("Invalid Webshare API token")
            else:
                logger.error(f"Failed to get proxy from Webshare API: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching proxies from Webshare: {str(e)}")
            
        return []

    @classmethod
    def get_random_proxy(cls, proxy_list=None) -> Optional[Dict[str, str]]:
        """Get a proxy with strong preference for successful ones"""
        if proxy_list is None:
            proxy_list = cls.get_proxy_list()
            
        if not proxy_list:
            return None

        # Split proxies into successful (>0% success rate) and untested/failed ones
        successful_proxies = [p for p in proxy_list if p['success_rate'] > 0 and p['success_count'] >= 1]
        other_proxies = [p for p in proxy_list if p['success_rate'] == 0 or p['success_count'] < 1]

        # 90% chance to use a successful proxy if available
        if successful_proxies and random.random() < 0.9:
            # Take the best performing proxy
            proxy = successful_proxies[0]
            logger.info(f"Selected best proxy: {proxy['address']} "
                       f"(Success rate: {proxy['success_rate']:.1f}%, "
                       f"Successful attempts: {proxy['success_count']})")
            return proxy
        
        # 10% chance to try a new proxy or if no successful proxies available
        if other_proxies:
            proxy = random.choice(other_proxies)
            logger.info(f"Selected untested/new proxy: {proxy['address']} "
                       f"(Success rate: {proxy['success_rate']:.1f}%, "
                       f"Successful attempts: {proxy['success_count']})")
            return proxy
        
        # If no other options, use any available proxy
        proxy = random.choice(proxy_list)
        logger.info(f"Selected fallback proxy: {proxy['address']} "
                   f"(Success rate: {proxy['success_rate']:.1f}%, "
                   f"Successful attempts: {proxy['success_count']})")
        return proxy