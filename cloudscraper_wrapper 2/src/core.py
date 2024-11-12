import cloudscraper
import time
import json
import asyncio
import aiohttp
from typing import Dict, Optional, Union, List, Any, Tuple
import logging
from urllib.parse import urlparse
import os
from datetime import datetime
import random
from http.cookiejar import LWPCookieJar
from concurrent.futures import ThreadPoolExecutor
import hashlib
from .exceptions import (
    RequestError, 
    ProxyError, 
    CacheError,
    RateLimitError
)

class CloudScraperWrapper:
    def __init__(self, 
                 delay_range: tuple = (2, 5),
                 proxy: Optional[Union[str, Dict[str, str]]] = None,
                 proxy_rotation: bool = False,
                 proxy_list: Optional[list] = None,
                 max_retries: int = 3,
                 timeout: int = 30,
                 custom_headers: Optional[Dict[str, str]] = None,
                 cookie_file: Optional[str] = None,
                 max_concurrent_requests: int = 10,
                 log_level: str = 'INFO',
                 log_file: Optional[str] = 'scraper.log',
                 cache_enabled: bool = True,
                 verify_ssl: bool = True):

        # Configure enhanced logging
        self._setup_logging(log_level, log_file)
        
        # Initialize basic parameters
        self.delay_range = delay_range
        self.max_retries = max_retries
        self.timeout = timeout
        self.custom_headers = custom_headers or {}
        self.max_concurrent_requests = max_concurrent_requests
        self.cache_enabled = cache_enabled
        self.verify_ssl = verify_ssl
        self.last_request_time = 0
        
        # Initialize statistics
        self.stats = {
            'requests_made': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cached_responses': 0,
            'retry_attempts': 0,
            'total_request_time': 0,
            'proxy_rotations': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Proxy configuration
        self.proxy_rotation = proxy_rotation
        self.proxy_list = proxy_list if proxy_list else []
        self.current_proxy_index = 0
        self.proxy = proxy
        self.failed_proxies = set()
        self.proxy_stats = {}  # Track success/failure per proxy
        
        # Initialize cache and cookie handling
        self.cache_dir = os.path.join(os.getcwd(), 'cache')
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cookie handling
        self.cookie_file = cookie_file
        if cookie_file:
            self.cookies = LWPCookieJar(cookie_file)
            if os.path.exists(cookie_file):
                try:
                    self.cookies.load(ignore_discard=True)
                except Exception as e:
                    self.logger.warning(f"Failed to load cookies: {str(e)}")
        
        # Thread pool for concurrent requests
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_requests)
        
        # Initialize cloudscraper with optimal settings
        self._init_scraper()
        
        # Request session for connection pooling
        self.session = None
        self._initialize_session()

    def _initialize_session(self):
        """Initialize a persistent session for connection pooling"""
        self.session = self.scraper.session()
        self.session.verify = self.verify_ssl
        if self.custom_headers:
            self.session.headers.update(self.custom_headers)

    def _setup_logging(self, log_level: str, log_file: Optional[str]):
        """Enhanced logging setup with rotating file handler and detailed formatting"""
        from logging.handlers import RotatingFileHandler
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create detailed formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s'
        )
        
        # Console handler with color support
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        if log_file:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def _init_scraper(self):
        """Initialize or reinitialize the cloudscraper instance with optimal settings"""
        scraper_kwargs = {
            'browser': {
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False,
                'desktop': True
            },
            'timeout': self.timeout,
            'allow_brotli': True,
            'trust_env': True
        }
        
        if self.proxy:
            if isinstance(self.proxy, str):
                scraper_kwargs['proxies'] = {
                    'http': self.proxy,
                    'https': self.proxy
                }
            elif isinstance(self.proxy, dict):
                scraper_kwargs['proxies'] = self.proxy

        self.scraper = cloudscraper.create_scraper(**scraper_kwargs)
        
        # Add custom headers
        if self.custom_headers:
            self.scraper.headers.update(self.custom_headers)
        
        # Load cookies if available
        if hasattr(self, 'cookies'):
            self.scraper.cookies = self.cookies

    def _update_proxy_stats(self, proxy: str, success: bool):
        """Update success/failure statistics for a proxy"""
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {'success': 0, 'failure': 0}
        
        if success:
            self.proxy_stats[proxy]['success'] += 1
        else:
            self.proxy_stats[proxy]['failure'] += 1
            
        # Calculate success rate
        total = sum(self.proxy_stats[proxy].values())
        success_rate = self.proxy_stats[proxy]['success'] / total
        
        # Mark proxy as failed if success rate is too low
        if total >= 5 and success_rate < 0.3:
            self.failed_proxies.add(proxy)
            self.logger.warning(f"Proxy {proxy} marked as failed (success rate: {success_rate:.2%})")

    def _rotate_proxy(self, force: bool = False):
        """Rotate to next working proxy in proxy_list"""
        if not self.proxy_rotation or not self.proxy_list:
            return

        original_index = self.current_proxy_index
        while True:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(self.proxy_list)
            next_proxy = self.proxy_list[self.current_proxy_index]
            
            # Check if proxy is not in failed list
            if next_proxy not in self.failed_proxies:
                self.proxy = next_proxy
                self._init_scraper()
                self.stats['proxy_rotations'] += 1
                self.logger.info(f"Rotated to proxy: {self.proxy}")
                break
                
            # If we've tried all proxies, reset failed list
            if self.current_proxy_index == original_index:
                self.failed_proxies.clear()
                self.logger.warning("All proxies failed, resetting failed proxy list")

    def _respect_rate_limit(self):
        """Implement intelligent rate limiting between requests"""
        current_time = time.time()
        time_passed = current_time - self.last_request_time
        
        # Calculate dynamic delay based on recent success rate
        success_rate = self.stats['successful_requests'] / max(1, self.stats['requests_made'])
        base_delay = random.uniform(*self.delay_range)
        
        # Increase delay if success rate is low
        if success_rate < 0.5:
            adjusted_delay = base_delay * (1 + (0.5 - success_rate) * 2)
        else:
            adjusted_delay = base_delay
            
        if time_passed < adjusted_delay:
            sleep_time = adjusted_delay - time_passed
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _get_cache_key(self, url: str, params: Optional[Dict] = None) -> str:
        """Generate unique cache key for URL and parameters"""
        cache_data = url
        if params:
            cache_data += json.dumps(params, sort_keys=True)
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> str:
        """Generate filesystem path for cache key"""
        return os.path.join(self.cache_dir, f"{cache_key}.json")

    async def _async_get(self, url: str, **kwargs) -> Optional[str]:
        """Asynchronous GET request implementation with retry logic"""
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, **kwargs) as response:
                        if response.status == 200:
                            return await response.text()
                        else:
                            raise RequestError(f"HTTP {response.status}")
            except Exception as e:
                retry_count += 1
                if retry_count > self.max_retries:
                    self.logger.error(f"Async request failed after {retry_count} retries: {str(e)}")
                    return None
                await asyncio.sleep(random.uniform(*self.delay_range))
        return None

    def _save_to_cache(self, cache_key: str, data: str):
        """Save response data to cache with metadata"""
        cache_path = self._get_cache_path(cache_key)
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'metadata': {
                'proxy': self.proxy if self.proxy else None,
                'headers': dict(self.scraper.headers),
                'status': 'success'
            }
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f)
        except Exception as e:
            self.logger.error(f"Cache save failed: {str(e)}")
            raise CacheError(f"Failed to save cache: {str(e)}")

    def _get_from_cache(self, cache_key: str, max_age: int = 3600) -> Optional[str]:
        """Retrieve data from cache if not expired"""
        cache_path = self._get_cache_path(cache_key)
        
        try:
            if not os.path.exists(cache_path):
                self.stats['cache_misses'] += 1
                return None

            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if (datetime.now() - cache_time).total_seconds() < max_age:
                self.stats['cache_hits'] += 1
                return cache_data['data']
            
            self.stats['cache_misses'] += 1
            return None
                
        except Exception as e:
            self.logger.error(f"Cache retrieval failed: {str(e)}")
            self.stats['cache_misses'] += 1
            return None

    def get(self, url: str, params: Optional[Dict] = None, use_cache: bool = True,
            max_cache_age: int = 3600, custom_headers: Optional[Dict] = None) -> Optional[str]:
        """
        Enhanced GET request with caching, retries, and comprehensive error handling
        
        Args:
            url: Target URL
            params: Optional query parameters
            use_cache: Whether to use caching
            max_cache_age: Maximum cache age in seconds
            custom_headers: Optional headers for this request only
            
        Returns:
            Response text if successful, None otherwise
        """
        start_time = time.time()
        self.stats['requests_made'] += 1
        
        # Check cache if enabled
        if use_cache and self.cache_enabled:
            cache_key = self._get_cache_key(url, params)
            cached_data = self._get_from_cache(cache_key, max_cache_age)
            if cached_data:
                self.stats['cached_responses'] += 1
                return cached_data

        # Prepare headers for this request
        current_headers = self.scraper.headers.copy()
        if custom_headers:
            current_headers.update(custom_headers)

        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                self._respect_rate_limit()
                
                response = self.session.get(
                    url,
                    params=params,
                    headers=current_headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                
                if response.status_code == 200:
                    if use_cache and self.cache_enabled:
                        cache_key = self._get_cache_key(url, params)
                        self._save_to_cache(cache_key, response.text)
                    
                    self.stats['successful_requests'] += 1
                    self.stats['total_request_time'] += time.time() - start_time
                    
                    if self.proxy:
                        self._update_proxy_stats(self.proxy, True)
                    
                    # Save cookies if configured
                    if self.cookie_file:
                        self.cookies.save(ignore_discard=True)
                    
                    return response.text
                
                # Handle specific status codes
                if response.status_code == 403:
                    self.logger.warning("Possible Cloudflare challenge detected")
                    self._init_scraper()  # Reinitialize scraper
                elif response.status_code == 429:
                    self.logger.warning("Rate limit detected, increasing delay")
                    self.delay_range = (self.delay_range[0] * 1.5, self.delay_range[1] * 1.5)
                
                raise RequestError(f"HTTP {response.status_code}")
                
            except Exception as e:
                retry_count += 1
                if self.proxy:
                    self._update_proxy_stats(self.proxy, False)
                
                if retry_count <= self.max_retries:
                    self.stats['retry_attempts'] += 1
                    self.logger.warning(f"Attempt {retry_count}/{self.max_retries} failed: {str(e)}")
                    
                    if self.proxy_rotation:
                        self._rotate_proxy()
                    
                    # Exponential backoff
                    wait_time = (2 ** retry_count) + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    self.stats['failed_requests'] += 1
                    self.logger.error(f"All retry attempts failed for {url}: {str(e)}")
                    return None

        return None
    def post(self, url: str, data: Optional[Dict] = None, json_data: Optional[Dict] = None,
             custom_headers: Optional[Dict] = None) -> Optional[str]:
        """
        Enhanced POST request with retry logic and error handling
        
        Args:
            url: Target URL
            data: Form data to send
            json_data: JSON data to send
            custom_headers: Optional headers for this request only
            
        Returns:
            Response text if successful, None otherwise
        """
        start_time = time.time()
        self.stats['requests_made'] += 1
        
        # Prepare headers
        current_headers = self.scraper.headers.copy()
        if custom_headers:
            current_headers.update(custom_headers)

        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                self._respect_rate_limit()
                
                response = self.session.post(
                    url,
                    data=data,
                    json=json_data,
                    headers=current_headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                
                if response.status_code == 200:
                    self.stats['successful_requests'] += 1
                    self.stats['total_request_time'] += time.time() - start_time
                    
                    if self.proxy:
                        self._update_proxy_stats(self.proxy, True)
                    
                    return response.text
                
                raise RequestError(f"HTTP {response.status_code}")
                
            except Exception as e:
                retry_count += 1
                if self.proxy:
                    self._update_proxy_stats(self.proxy, False)
                
                if retry_count <= self.max_retries:
                    self.stats['retry_attempts'] += 1
                    if self.proxy_rotation:
                        self._rotate_proxy()
                    time.sleep((2 ** retry_count) + random.uniform(0, 1))
                else:
                    self.stats['failed_requests'] += 1
                    self.logger.error(f"POST request failed after all retries: {str(e)}")
                    return None

        return None

    async def batch_get(self, urls: List[str], max_concurrent: Optional[int] = None,
                       custom_headers: Optional[Dict] = None) -> List[Optional[str]]:
        """
        Execute multiple GET requests in parallel with rate limiting
        
        Args:
            urls: List of URLs to fetch
            max_concurrent: Maximum number of concurrent requests
            custom_headers: Optional headers for these requests
            
        Returns:
            List of response texts (None for failed requests)
        """
        max_concurrent = max_concurrent or self.max_concurrent_requests
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def bounded_get(url):
            async with semaphore:
                kwargs = {'headers': custom_headers} if custom_headers else {}
                return await self._async_get(url, **kwargs)
        
        tasks = [bounded_get(url) for url in urls]
        return await asyncio.gather(*tasks)

    def download_file(self, url: str, output_path: str, chunk_size: int = 8192,
                     show_progress: bool = True) -> bool:
        """
        Download a file with progress tracking and retry logic
        
        Args:
            url: File URL
            output_path: Where to save the file
            chunk_size: Size of chunks to download
            show_progress: Whether to show progress bar
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._respect_rate_limit()
            
            response = self.session.get(
                url,
                stream=True,
                timeout=self.timeout,
                verify=self.verify_ssl
            )
            
            if response.status_code != 200:
                self.logger.error(f"Download failed with status code: {response.status_code}")
                return False

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # Get file size if available
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f:
                if show_progress and total_size > 0:
                    from tqdm import tqdm
                    progress_bar = tqdm(
                        total=total_size,
                        unit='iB',
                        unit_scale=True
                    )
                    
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            progress_bar.update(len(chunk))
                    progress_bar.close()
                else:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error downloading file: {str(e)}")
            if os.path.exists(output_path):
                os.remove(output_path)  # Clean up partial download
            return False

    def clear_cache(self, max_age: Optional[int] = None):
        """
        Clear all cache or cache older than max_age
        
        Args:
            max_age: Optional maximum age in seconds
        """
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if not os.path.isfile(filepath):
                    continue
                    
                if max_age is None:
                    os.remove(filepath)
                else:
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if (datetime.now() - file_time).total_seconds() > max_age:
                        os.remove(filepath)
                        
            self.logger.info("Cache cleared successfully")
            
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            raise CacheError(f"Failed to clear cache: {str(e)}")

    def get_proxy_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Get detailed statistics for each proxy
        
        Returns:
            Dict containing stats for each proxy
        """
        stats = {}
        for proxy, data in self.proxy_stats.items():
            total = data['success'] + data['failure']
            if total > 0:
                success_rate = data['success'] / total
                stats[proxy] = {
                    'success_rate': success_rate,
                    'total_requests': total,
                    'successful_requests': data['success'],
                    'failed_requests': data['failure']
                }
        return stats

    def cleanup(self):
        """Cleanup resources and save state"""
        try:
            if self.cookie_file:
                self.cookies.save(ignore_discard=True)
            self.executor.shutdown(wait=True)
            self.session.close()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup resources on exit"""
        self.cleanup()

    def __del__(self):
        """Ensure resources are cleaned up"""
        self.cleanup()