# CloudScraper Wrapper

A powerful Python wrapper for CloudScraper that adds proxy management, rate limiting, caching, and extensive error handling capabilities.

## Features

- Proxy support with automatic rotation and health monitoring
- Intelligent rate limiting and request throttling
- Response caching with customizable expiration
- Async support for parallel requests
- Comprehensive error handling and retry logic
- Detailed request statistics and logging
- File download support with progress tracking
- Cookie management and persistence
- Custom header support
- SSL verification options

## Installation

```bash
pip install cloudscraper-wrapper
```

## Basic Usage

```python
from cloudscraper_wrapper import CloudScraperWrapper

# Basic initialization
scraper = CloudScraperWrapper(
    delay_range=(2, 5),
    max_retries=3,
    timeout=30
)

# Simple GET request
response = scraper.get('https://example.com')
if response:
    print("Successfully retrieved page")
```

## Advanced Usage

### Proxy Configuration

```python
# Single proxy
scraper = CloudScraperWrapper(
    proxy='http://user:pass@host:port'
)

# Proxy rotation
proxies = [
    'http://user1:pass1@host1:port1',
    'http://user2:pass2@host2:port2',
    'http://user3:pass3@host3:port3'
]

scraper = CloudScraperWrapper(
    proxy_rotation=True,
    proxy_list=proxies,
    max_retries=3
)

# Manage proxies
scraper.add_proxy_to_rotation('http://user4:pass4@host4:port4')
scraper.remove_proxy_from_rotation('http://user1:pass1@host1:port1')
scraper.set_proxy('http://newuser:newpass@newhost:port')

# Get proxy statistics
stats = scraper.get_proxy_stats()
print(f"Proxy performance: {stats}")
```

### Async Batch Requests

```python
# Multiple URLs in parallel
urls = [
    'https://example1.com',
    'https://example2.com',
    'https://example3.com'
]

async def main():
    responses = await scraper.batch_get(
        urls,
        max_concurrent=5
    )
    for url, response in zip(urls, responses):
        if response:
            print(f"Successfully retrieved {url}")

# Run with asyncio
import asyncio
asyncio.run(main())
```

### File Downloads

```python
# Download with progress bar
success = scraper.download_file(
    url='https://example.com/file.pdf',
    output_path='downloads/file.pdf',
    show_progress=True
)
```

### Cache Management

```python
# Custom cache settings
response = scraper.get(
    'https://example.com',
    use_cache=True,
    max_cache_age=7200  # Cache for 2 hours
)

# Clear cache
scraper.clear_cache()  # Clear all cache
scraper.clear_cache(max_age=86400)  # Clear cache older than 24 hours
```

### Context Manager

```python
with CloudScraperWrapper() as scraper:
    response = scraper.get('https://example.com')
    # Resources automatically cleaned up after use
```

## Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| delay_range | tuple | (2, 5) | Range for random delay between requests (seconds) |
| proxy | str/dict | None | Single proxy configuration |
| proxy_rotation | bool | False | Enable proxy rotation |
| proxy_list | list | None | List of proxies for rotation |
| max_retries | int | 3 | Maximum number of retry attempts |
| timeout | int | 30 | Request timeout in seconds |
| custom_headers | dict | None | Custom headers for requests |
| cookie_file | str | None | Path to cookie file for persistence |
| max_concurrent_requests | int | 10 | Maximum concurrent requests for batch operations |
| log_level | str | 'INFO' | Logging level |
| log_file | str | 'scraper.log' | Path to log file |
| cache_enabled | bool | True | Enable response caching |
| verify_ssl | bool | True | Verify SSL certificates |

## Statistics and Monitoring

```python
# Get request statistics
stats = scraper.get_stats()
print(f"""
Success Rate: {stats['successful_requests']/stats['requests_made']*100}%
Cache Hit Rate: {stats['cache_hits']/(stats['cache_hits'] + stats['cache_misses'])*100}%
Average Request Time: {stats['total_request_time']/stats['successful_requests']}s
""")
```

## Error Handling

```python
from cloudscraper_wrapper import RequestError, ProxyError, CacheError

try:
    response = scraper.get('https://example.com')
except RequestError as e:
    print(f"Request failed: {e}")
except ProxyError as e:
    print(f"Proxy error: {e}")
except CacheError as e:
    print(f"Cache error: {e}")
```

## License

MIT License

## Support

- GitHub Issues: [Report a bug](https://github.com/yourusername/cloudscraper-wrapper/issues)
- Documentation: [Full documentation](https://github.com/yourusername/cloudscraper-wrapper/wiki)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational purposes only. Follow websites' terms of service and robots.txt rules when scraping.