# CloudScraper Wrapper 🚀

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Cloudscraper](https://img.shields.io/badge/cloudscraper-latest-orange.svg)](https://github.com/VeNoMouS/cloudscraper)

A robust Python wrapper for CloudScraper that handles Cloudflare protection, rate limiting, and caching. Perfect for web scraping projects that need to bypass anti-bot measures.

## 🔑 Key Features

- ✅ **Cloudflare Bypass**: Automatically handles Cloudflare's anti-bot challenges
- 🚦 **Smart Rate Limiting**: Built-in delays to prevent IP blocks
- 💾 **Response Caching**: Reduces unnecessary requests and improves performance
- 📝 **Comprehensive Logging**: Detailed logs for debugging and monitoring
- 🔄 **Request Retries**: Automatic retry mechanism for failed requests
- 🎯 **Type Hints**: Full Python type annotations for better code maintainability

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/cloudscraper-wrapper.git

# Install required packages
pip install -r requirements.txt
```

## 📋 Requirements

```text
cloudscraper>=1.2.60
python>=3.7
```

## 🚀 Quick Start

```python
from cloudscraper_wrapper import CloudScraperWrapper

# Initialize the scraper
scraper = CloudScraperWrapper(delay_range=(2, 5))

# Make a GET request
html = scraper.get('https://example.com')
if html:
    print("Successfully retrieved page")

# Make a POST request
response = scraper.post(
    'https://example.com/api',
    json_data={'key': 'value'}
)

# Download a file
success = scraper.download_file(
    'https://example.com/file.pdf',
    'downloads/file.pdf'
)
```

## 📚 Advanced Usage

### Cache Configuration

```python
# Customize cache duration
html = scraper.get(
    'https://example.com',
    use_cache=True,
    max_cache_age=7200  # Cache for 2 hours
)
```

### Custom Rate Limiting

```python
# Initialize with custom delay range
scraper = CloudScraperWrapper(delay_range=(3, 8))  # 3-8 seconds delay
```

### Error Handling

```python
try:
    response = scraper.get('https://example.com')
    if response is None:
        print("Request failed, check logs for details")
except Exception as e:
    print(f"An error occurred: {str(e)}")
```

## 📊 Features Breakdown

| Feature | Description |
|---------|------------|
| GET Requests | Supports URL parameters and response caching |
| POST Requests | Handles both form data and JSON payloads |
| File Downloads | Streams large files with progress tracking |
| Caching | Intelligent response caching with expiration |
| Rate Limiting | Random delays between requests |
| Error Handling | Comprehensive error catching and logging |
| Type Safety | Full typing support for modern Python |

## 🔍 Logging

The wrapper includes detailed logging functionality:

```python
# Logs are written to 'scraper.log' and console
# Format: timestamp - level - message
2024-03-12 10:15:30 - INFO - Requesting: https://example.com
2024-03-12 10:15:31 - INFO - Successfully retrieved from cache
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Cloudscraper](https://github.com/VeNoMouS/cloudscraper) for the base functionality
- All contributors and users of this wrapper

<p align="center">Made with ❤️ for the scraping community</p>
