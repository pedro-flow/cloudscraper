// Import required modules
const cloudscraper = require('cloudscraper');
const fs = require('fs').promises;
const path = require('path');
const winston = require('winston');

class CloudScraperWrapper {
    constructor(options = {}) {
        // Default configuration
        this.config = {
            delayRange: options.delayRange || [2000, 5000], // Convert to milliseconds
            cacheDir: options.cacheDir || 'cache',
            userAgent: options.userAgent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
        };

        // Initialize logger
        this.logger = winston.createLogger({
            level: 'info',
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.json()
            ),
            transports: [
                new winston.transports.File({ filename: 'scraper.log' }),
                new winston.transports.Console({
                    format: winston.format.simple()
                })
            ]
        });

        // Initialize cloudscraper
        this.scraper = cloudscraper.defaults({
            userAgent: this.config.userAgent
        });

        this.lastRequestTime = 0;

        // Ensure cache directory exists
        this._initializeCache();
    }

    // Initialize cache directory
    async _initializeCache() {
        try {
            await fs.mkdir(this.config.cacheDir, { recursive: true });
        } catch (error) {
            this.logger.error('Failed to create cache directory:', error);
        }
    }

    // Generate cache filename from URL
    _getCacheFilename(url) {
        const urlHash = Buffer.from(url).toString('base64').replace(/[/+=]/g, '_');
        return path.join(this.config.cacheDir, `${urlHash}.json`);
    }

    // Implement rate limiting
    async _respectRateLimit() {
        const now = Date.now();
        const timePassed = now - this.lastRequestTime;
        const delay = Math.random() * 
            (this.config.delayRange[1] - this.config.delayRange[0]) + 
            this.config.delayRange[0];

        if (timePassed < delay) {
            await new Promise(resolve => setTimeout(resolve, delay - timePassed));
        }

        this.lastRequestTime = Date.now();
    }

    // Save response to cache
    async _saveToCache(url, data) {
        const cacheFile = this._getCacheFilename(url);
        const cacheData = {
            timestamp: new Date().toISOString(),
            url,
            data
        };

        try {
            await fs.writeFile(cacheFile, JSON.stringify(cacheData), 'utf8');
        } catch (error) {
            this.logger.error('Failed to save to cache:', error);
        }
    }

    // Get data from cache
    async _getFromCache(url, maxAge = 3600000) { // maxAge in milliseconds
        const cacheFile = this._getCacheFilename(url);

        try {
            const cacheContent = await fs.readFile(cacheFile, 'utf8');
            const cacheData = JSON.parse(cacheContent);
            const cacheTime = new Date(cacheData.timestamp).getTime();
            
            if (Date.now() - cacheTime < maxAge) {
                return cacheData.data;
            }
        } catch (error) {
            // Cache miss or invalid cache is not an error
            return null;
        }

        return null;
    }

    // Perform GET request
    async get(url, params = {}, useCache = true, maxCacheAge = 3600000) {
        // Check cache first if enabled
        if (useCache) {
            const cachedData = await this._getFromCache(url, maxCacheAge);
            if (cachedData) {
                this.logger.info(`Retrieved from cache: ${url}`);
                return cachedData;
            }
        }

        await this._respectRateLimit();

        try {
            this.logger.info(`Requesting: ${url}`);
            
            // Build URL with query parameters
            const urlWithParams = new URL(url);
            Object.entries(params).forEach(([key, value]) => {
                urlWithParams.searchParams.append(key, value);
            });

            const response = await this.scraper.get(urlWithParams.toString());
            
            if (useCache) {
                await this._saveToCache(url, response);
            }

            return response;
        } catch (error) {
            this.logger.error('Request failed:', error);
            return null;
        }
    }

    // Perform POST request
    async post(url, data = null, jsonData = null) {
        await this._respectRateLimit();

        try {
            this.logger.info(`POST request to: ${url}`);

            const options = {
                method: 'POST',
                headers: {
                    'Content-Type': jsonData ? 'application/json' : 'application/x-www-form-urlencoded'
                }
            };

            if (jsonData) {
                options.body = JSON.stringify(jsonData);
            } else if (data) {
                options.form = data;
            }

            const response = await this.scraper.post(url, options);
            return response;
        } catch (error) {
            this.logger.error('POST request failed:', error);
            return null;
        }
    }

    // Download file
    async downloadFile(url, outputPath) {
        await this._respectRateLimit();

        try {
            this.logger.info(`Downloading file from: ${url}`);

            // Ensure directory exists
            await fs.mkdir(path.dirname(outputPath), { recursive: true });

            const response = await this.scraper.get(url, { encoding: null });
            await fs.writeFile(outputPath, response);

            this.logger.info(`File downloaded successfully to: ${outputPath}`);
            return true;
        } catch (error) {
            this.logger.error('File download failed:', error);
            return false;
        }
    }

    // Cleanup method
    async cleanup() {
        try {
            // Clean up old cache files
            const files = await fs.readdir(this.config.cacheDir);
            const now = Date.now();
            
            for (const file of files) {
                const filePath = path.join(this.config.cacheDir, file);
                const stats = await fs.stat(filePath);
                
                // Remove files older than 24 hours
                if (now - stats.mtime.getTime() > 24 * 3600000) {
                    await fs.unlink(filePath);
                }
            }
        } catch (error) {
            this.logger.error('Cleanup failed:', error);
        }
    }
}

module.exports = CloudScraperWrapper;
