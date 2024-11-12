import cloudscraper
import time
import json
from typing import Dict, Optional, Union
import logging
from urllib.parse import urlparse
import os
from datetime import datetime
import random

class CloudScraperWrapper:
    def __init__(self, delay_range: tuple = (2, 5)):
        # Initialize the CloudScraper wrapper with configuration options
        # Args:
        #     delay_range (tuple): Range for random delay between requests (min, max) in seconds
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize cloudscraper
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        
        self.delay_range = delay_range
        self.last_request_time = 0
        
        # Create a directory for cached responses
        self.cache_dir = 'cache'
        os.makedirs(self.cache_dir, exist_ok=True)

    def _respect_rate_limit(self):
        # Implement rate limiting between requests
        current_time = time.time()
        time_passed = current_time - self.last_request_time
        delay = random.uniform(*self.delay_range)
        
        if time_passed < delay:
            time.sleep(delay - time_passed)
        
        self.last_request_time = time.time()

    def _get_cache_filename(self, url: str) -> str:
        # Generate a cache filename from URL
        parsed = urlparse(url)
        return os.path.join(self.cache_dir, f"{parsed.netloc}_{hash(url)}.json")

    def _save_to_cache(self, url: str, data: str):
        # Save response data to cache
        cache_file = self._get_cache_filename(url)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'url': url,
                'data': data
            }, f)

    def _get_from_cache(self, url: str, max_age: int = 3600) -> Optional[str]:
        # Retrieve data from cache if it exists and hasn't expired
        # Args:
        #     url (str): URL of the cached content
        #     max_age (int): Maximum age of cache in seconds
        # Returns:
        #     Optional[str]: Cached data if valid, None if expired or not found
        
        cache_file = self._get_cache_filename(url)
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cache_time = datetime.fromisoformat(cache_data['timestamp'])
                if (datetime.now() - cache_time).total_seconds() < max_age:
                    return cache_data['data']
        return None

    def get(self, url: str, params: Optional[Dict] = None, use_cache: bool = True, 
            max_cache_age: int = 3600) -> Optional[str]:
        # Perform GET request with rate limiting and error handling
        # Args:
        #     url (str): URL to scrape
        #     params (dict, optional): Query parameters
        #     use_cache (bool): Whether to use caching
        #     max_cache_age (int): Maximum cache age in seconds
        # Returns:
        #     Optional[str]: Response text if successful, None if failed
        
        if use_cache:
            cached_data = self._get_from_cache(url, max_cache_age)
            if cached_data:
                self.logger.info(f"Retrieved from cache: {url}")
                return cached_data

        self._respect_rate_limit()
        
        try:
            self.logger.info(f"Requesting: {url}")
            response = self.scraper.get(url, params=params)
            
            if response.status_code == 200:
                if use_cache:
                    self._save_to_cache(url, response.text)
                return response.text
            else:
                self.logger.error(f"Request failed with status code: {response.status_code}")
                return None
                
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            self.logger.error(f"Cloudflare challenge error: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return None

    def post(self, url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Optional[str]:
        # Perform POST request with rate limiting and error handling
        # Args:
        #     url (str): URL to send POST request to
        #     data (dict, optional): Form data
        #     json_data (dict, optional): JSON data
        # Returns:
        #     Optional[str]: Response text if successful, None if failed
        
        self._respect_rate_limit()
        
        try:
            self.logger.info(f"POST request to: {url}")
            response = self.scraper.post(url, data=data, json=json_data)
            
            if response.status_code == 200:
                return response.text
            else:
                self.logger.error(f"POST request failed with status code: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error in POST request: {str(e)}")
            return None

    def download_file(self, url: str, output_path: str) -> bool:
        # Download a file from URL
        # Args:
        #     url (str): URL of the file
        #     output_path (str): Where to save the file
        # Returns:
        #     bool: True if successful, False otherwise
        
        self._respect_rate_limit()
        
        try:
            self.logger.info(f"Downloading file from: {url}")
            response = self.scraper.get(url, stream=True)
            
            if response.status_code == 200:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                self.logger.error(f"File download failed with status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error downloading file: {str(e)}")
            return False
