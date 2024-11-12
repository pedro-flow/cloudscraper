class CloudScraperWrapperException(Exception):
    """Base exception for CloudScraperWrapper"""
    pass

class RequestError(CloudScraperWrapperException):
    """Raised when a request fails"""
    pass

class ProxyError(CloudScraperWrapperException):
    """Raised when there's an issue with proxies"""
    pass

class CacheError(CloudScraperWrapperException):
    """Raised when there's an error with caching operations"""
    pass

class RateLimitError(CloudScraperWrapperException):
    """Raised when rate limit is exceeded"""
    pass