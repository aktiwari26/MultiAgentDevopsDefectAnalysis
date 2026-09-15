# Nginx & Web Server Troubleshooting Guide

## Common HTTP Error Patterns

### 502 Bad Gateway

**Cause:** Nginx cannot reach the upstream (backend service is down or not listening)

**Diagnosis:**
```bash
tail -200 /var/log/nginx/error.log | grep "502\|upstream"
nginx -t
curl -I http://upstream-host:port/health
```

**Resolution:**
1. Verify backend service is running and listening
2. Check upstream host/port in nginx config
3. Verify firewall allows nginx → backend traffic
4. Check if upstream pod is Ready: `kubectl get endpoints <svc>`
5. Increase `proxy_read_timeout` if backend is slow

```nginx
upstream backend {
    server backend:8080;
    keepalive 32;
}

location /api/ {
    proxy_read_timeout 60s;
    proxy_connect_timeout 10s;
    proxy_pass http://backend;
}
```

---

### 503 Service Unavailable

**Cause:** All upstream servers are down, or upstream returned 503

**Diagnosis:**
```bash
# Check nginx upstream status
nginx -s reload && tail -f /var/log/nginx/error.log

# Check all backend pods
kubectl get pods -l app=backend
kubectl get endpoints backend-service
```

**Resolution:**
1. Scale backend pods: `kubectl scale deployment/backend --replicas=5`
2. Check if circuit breaker is tripping
3. Verify health checks pass: `curl http://backend/health`
4. Check for resource quota issues: `kubectl describe resourcequota`

---

### 504 Gateway Timeout

**Cause:** Backend took too long to respond

**Diagnosis:**
```bash
kubectl logs deployment/backend --tail=200 | grep -i "slow\|timeout\|latency"
kubectl top pods -l app=backend
```

**Resolution:**
1. Increase `proxy_read_timeout` in nginx config
2. Optimize slow backend query / operation
3. Add caching layer for expensive operations
4. Scale backend horizontally

---

### High 5xx Error Rate

**Diagnosis Commands:**
```bash
# Count error codes in last 1000 lines
tail -1000 /var/log/nginx/access.log | awk '{print $9}' | sort | uniq -c | sort -rn

# Find slowest endpoints
awk '{print $7, $10}' /var/log/nginx/access.log | sort -k2 -rn | head -20

# Real-time error rate
tail -f /var/log/nginx/access.log | awk '$9 >= 500 {print}'
```

**Resolution:**
1. Identify which endpoints are returning errors
2. Check backend service for those specific routes
3. Enable rate limiting temporarily if DDoS suspected
4. Add error page caching to reduce backend load

---

## Configuration Best Practices

### Rate Limiting
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    limit_req_status 429;
}
```

### Connection Pooling (Keepalive)
```nginx
upstream backend {
    server backend1:8080;
    server backend2:8080;
    keepalive 32;
}

location /api/ {
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_pass http://backend;
}
```

### Health Check Configuration
```nginx
upstream backend {
    server backend:8080;
    check interval=3000 rise=2 fall=3 timeout=1000 type=http;
    check_http_send "HEAD /health HTTP/1.0\r\n\r\n";
    check_http_expect_alive http_2xx;
}
```

### Gzip Compression
```nginx
gzip on;
gzip_types text/plain application/json application/javascript text/css;
gzip_min_length 1024;
gzip_comp_level 4;
```

---

## Log Format Reference

### Standard Access Log Format
```
$remote_addr - $remote_user [$time_local] "$request" 
$status $body_bytes_sent "$http_referer" "$http_user_agent" 
$request_time $upstream_response_time
```

### Alert Thresholds
- 5xx rate > 1%: WARNING
- 5xx rate > 5%: CRITICAL  
- P99 latency > 2000ms: WARNING
- P99 latency > 5000ms: CRITICAL
- Upstream response time > 1000ms: WARNING
