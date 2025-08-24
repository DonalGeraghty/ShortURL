# 📊 Logging Guide for Google Cloud Run

## 🎯 **Overview**

This guide covers the comprehensive logging system implemented in your URL Shortener API, designed specifically for Google Cloud Run deployment. The logging system provides structured logs, performance metrics, and error tracking for production monitoring.

## ✨ **Features**

- **🔍 Structured Logging**: JSON-formatted logs for easy parsing
- **📈 Performance Metrics**: Request duration tracking and performance thresholds
- **🚨 Error Tracking**: Comprehensive error logging with context
- **🌐 Request Monitoring**: Full request/response lifecycle logging
- **⚙️ Environment Configuration**: Different log levels for dev/prod/cloud
- **📁 File Logging**: Optional file-based logging for production

## 🏗️ **Architecture**

### **Logging Components**

1. **`logging_config.py`** - Centralized logging configuration
2. **`url_shortener.py`** - Core business logic logging
3. **`app.py`** - Flask application and request logging
4. **Middleware** - Request/response logging hooks

### **Logger Hierarchy**

```
root
├── url_shortener          # Core URL shortening operations
├── flask_app             # Flask application operations
├── access                # Request/response logging
├── error                 # Error tracking
└── werkzeug             # Flask framework logs
```

## 🔧 **Configuration**

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment mode | `production` |
| `LOG_LEVEL` | Global log level | `INFO` |
| `LOG_FORMAT` | Log format style | `structured` |

### **Environment-Specific Settings**

#### **Development (`FLASK_ENV=development`)**
- **Level**: DEBUG
- **Format**: Detailed human-readable
- **Output**: Console only
- **Performance**: All operations logged

#### **Production (`FLASK_ENV=production`)**
- **Level**: INFO
- **Format**: Structured JSON
- **Output**: Console + Files
- **Performance**: Performance thresholds

#### **Google Cloud Run (`FLASK_ENV=cloud_run`)**
- **Level**: INFO
- **Format**: Structured JSON (Cloud Logging optimized)
- **Output**: Console only (Cloud Logging captures)
- **Performance**: Performance thresholds

## 📝 **Log Format**

### **Structured JSON Format**

```json
{
  "timestamp": "2024-01-01 12:00:00",
  "level": "INFO",
  "logger": "url_shortener",
  "message": "URL shortening completed successfully",
  "module": "url_shortener",
  "function": "shorten_url",
  "line": 156,
  "operation": "shorten_url",
  "short_code": "abc123",
  "duration_ms": 45.67,
  "status": "success"
}
```

### **Performance Metrics**

```json
{
  "timestamp": "2024-01-01 12:00:00",
  "level": "INFO",
  "logger": "url_shortener",
  "message": "Operation completed quickly",
  "operation": "shorten_url",
  "duration_ms": 45.67,
  "performance": true,
  "short_code": "abc123",
  "database": "firestore"
}
```

## 🚀 **Usage Examples**

### **Basic Logging**

```python
from logging_config import get_logger

logger = get_logger('url_shortener')

# Info logging
logger.info("Operation started", extra={
    "operation": "process_url",
    "url_length": len(url)
})

# Error logging
logger.error("Operation failed", extra={
    "operation": "process_url",
    "error": str(error),
    "retry_count": 3
})
```

### **Performance Logging**

```python
from logging_config import log_performance

# Log performance metrics
log_performance(
    operation="url_shortening",
    duration_ms=45.67,
    short_code="abc123",
    database="firestore"
)
```

### **Error Logging**

```python
from logging_config import log_error

try:
    # Your operation
    result = process_data()
except Exception as e:
    log_error(
        operation="process_data",
        error=e,
        input_data=input_data,
        retry_count=retry_count
    )
```

## 📊 **Google Cloud Run Integration**

### **Cloud Logging Benefits**

1. **Automatic Collection**: Logs automatically captured by Cloud Run
2. **Structured Querying**: Use Cloud Logging queries to filter logs
3. **Alerting**: Set up alerts based on log patterns
4. **Monitoring**: Integrate with Cloud Monitoring dashboards

### **Cloud Logging Queries**

#### **Find Slow Requests**
```
resource.type="cloud_run_revision"
resource.labels.service_name="url-shortener-api"
jsonPayload.duration_ms>1000
```

#### **Find Errors**
```
resource.type="cloud_run_revision"
resource.labels.service_name="url-shortener-api"
severity>=ERROR
```

#### **Performance Analysis**
```
resource.type="cloud_run_revision"
resource.labels.service_name="url-shortener-api"
jsonPayload.performance=true
jsonPayload.duration_ms>500
```

### **Log Levels in Cloud Run**

| Level | Cloud Logging Severity | Use Case |
|-------|----------------------|----------|
| DEBUG | DEBUG | Development debugging |
| INFO | INFO | Normal operations, performance |
| WARNING | WARNING | Performance issues, fallbacks |
| ERROR | ERROR | Errors, failures |
| CRITICAL | CRITICAL | System failures |

## 🔍 **Monitoring and Alerting**

### **Key Metrics to Monitor**

1. **Request Duration**
   - Fast: < 100ms
   - Normal: 100-500ms
   - Slow: 500-1000ms
   - Very Slow: > 1000ms

2. **Error Rates**
   - 4xx errors (client issues)
   - 5xx errors (server issues)
   - Database connection failures

3. **Performance Patterns**
   - URL shortening operations
   - URL retrieval operations
   - Database fallbacks

### **Alerting Examples**

#### **High Error Rate**
```
resource.type="cloud_run_revision"
resource.labels.service_name="url-shortener-api"
severity>=ERROR
```

**Threshold**: > 5% error rate in 5 minutes

#### **Slow Performance**
```
resource.type="cloud_run_revision"
resource.labels.service_name="url-shortener-api"
jsonPayload.duration_ms>1000
```

**Threshold**: > 10 slow requests in 5 minutes

#### **Service Unavailable**
```
resource.type="cloud_run_revision"
resource.labels.service_name="url-shortener-api"
severity>=ERROR
jsonPayload.message="Health check failed"
```

**Threshold**: Any occurrence

## 🛠️ **Customization**

### **Adding Custom Loggers**

```python
# In your module
from logging_config import get_logger

logger = get_logger('custom_module')

# Use the logger
logger.info("Custom operation", extra={
    "custom_field": "custom_value",
    "operation": "custom_operation"
})
```

### **Custom Log Formats**

```python
# Modify logging_config.py
'custom_format': {
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(custom_field)s',
    'datefmt': '%Y-%m-%d %H:%M:%S'
}
```

### **Performance Thresholds**

```python
# Modify logging_config.py performance thresholds
if duration_ms < 50:      # Very fast
    logger.info("Operation completed very quickly", extra=log_data)
elif duration_ms < 100:   # Fast
    logger.info("Operation completed quickly", extra=log_data)
elif duration_ms < 500:   # Normal
    logger.info("Operation completed normally", extra=log_data)
elif duration_ms < 1000:  # Slow
    logger.warning("Operation completed slowly", extra=log_data)
else:                     # Very slow
    logger.error("Operation completed very slowly", extra=log_data)
```

## 📁 **File Logging (Production)**

### **Log Files Structure**

```
logs/
├── access.log          # Request/response logs
├── errors.log          # Error logs
└── performance.log     # Performance metrics (optional)
```

### **Log Rotation**

For production file logging, consider implementing log rotation:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'logs/app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

## 🚨 **Troubleshooting**

### **Common Issues**

1. **Logs Not Appearing**
   - Check log level configuration
   - Verify logger handlers
   - Check environment variables

2. **Performance Impact**
   - Use appropriate log levels
   - Avoid logging in hot paths
   - Use async logging for high-volume

3. **Cloud Logging Issues**
   - Verify Cloud Run service account permissions
   - Check log format compatibility
   - Monitor Cloud Logging quotas

### **Debug Commands**

```bash
# Check current log configuration
python -c "from logging_config import setup_logging; setup_logging('development')"

# Test logging
python -c "from logging_config import get_logger; logger = get_logger('test'); logger.info('Test log')"

# View log files
tail -f logs/access.log
tail -f logs/errors.log
```

## 💰 **Cost Optimization**

### **Cloud Logging Costs**

- **Ingestion**: $0.50 per GB
- **Storage**: $0.01 per GB per month
- **Queries**: $0.01 per GB scanned

### **Optimization Tips**

1. **Use appropriate log levels**
2. **Avoid logging large objects**
3. **Implement log sampling for high-volume operations**
4. **Set up log retention policies**

## 🎯 **Best Practices**

1. **Structured Logging**: Always use structured JSON format
2. **Context**: Include relevant context in every log
3. **Performance**: Log performance metrics for critical operations
4. **Error Handling**: Log errors with full context
5. **Monitoring**: Set up alerts for critical issues
6. **Retention**: Implement log retention policies

---

🎉 **Your logging system is now production-ready for Google Cloud Run!**
