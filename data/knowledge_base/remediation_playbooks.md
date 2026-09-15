# DevOps Remediation Playbooks

## PLAYBOOK-001: Redis / Cache Failure

### Trigger Conditions
- Redis connection timeout errors
- Cache hit rate < 20%
- Redis CPU > 90%
- Redis memory eviction rate high

### Diagnosis
```bash
redis-cli ping
redis-cli info memory
redis-cli info stats | grep evicted_keys
redis-cli info clients | grep connected_clients
redis-cli --latency -h <redis-host>
```

### Remediation Steps
1. Check Redis cluster health: `redis-cli cluster info`
2. If OOM: increase `maxmemory` or eviction policy (`allkeys-lru`)
3. If connection pool exhausted: reduce `maxclients` or add connection pooling
4. Flush stale cache keys: `redis-cli keys "stale:*" | xargs redis-cli del`
5. Restart Redis (last resort): `systemctl restart redis`
6. Verify replication: `redis-cli info replication`

### Failover
- Configure application to fall back to database on cache miss
- Enable read-through caching mode
- Promote replica to primary: `redis-cli -h <replica> REPLICAOF NO ONE`

---

## PLAYBOOK-002: PostgreSQL Connection Pool Exhaustion

### Trigger Conditions
- Error: "too many connections" / "remaining connection slots reserved"
- Active connections approaching `max_connections`
- Connection wait time exceeds threshold

### Diagnosis
```sql
-- Check active connections
SELECT count(*), state, wait_event_type, wait_event 
FROM pg_stat_activity 
GROUP BY state, wait_event_type, wait_event;

-- Find long-running queries
SELECT pid, now() - query_start AS duration, query, state
FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '30 seconds'
ORDER BY duration DESC;

-- Check max connections
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;
```

### Remediation Steps
1. **Immediate**: Kill long-running queries
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity 
   WHERE state = 'active' AND now() - query_start > interval '60 seconds';
   ```
2. Deploy PgBouncer connection pooler in front of PostgreSQL
3. Increase `max_connections` in `postgresql.conf` (requires restart)
4. Reduce application connection pool size (`pool_size` in SQLAlchemy/HikariCP)
5. Add read replicas to distribute read traffic

### Prevention
- Use PgBouncer in transaction pooling mode
- Set connection pool limits per service
- Alert at 80% of max_connections
- Index frequently queried columns

---

## PLAYBOOK-003: Kubernetes Deployment Rollback

### Trigger Conditions
- New deployment causing errors / elevated failure rate
- CrashLoopBackOff after deploy
- Latency regression after deploy

### Rollback Commands
```bash
# Immediate rollback
kubectl rollout undo deployment/<deployment-name> -n <namespace>

# Rollback to specific revision
kubectl rollout history deployment/<deployment-name> -n <namespace>
kubectl rollout undo deployment/<deployment-name> --to-revision=<N> -n <namespace>

# Verify rollback status
kubectl rollout status deployment/<deployment-name> -n <namespace>
kubectl get pods -n <namespace> -l app=<app-label>
```

### Post-Rollback Verification
```bash
# Check all pods healthy
kubectl get pods -n <namespace>

# Verify endpoint health
kubectl exec -it <pod> -- curl -s http://localhost:<port>/health

# Check error rate in Grafana / logs
tail -f /var/log/app/error.log
```

---

## PLAYBOOK-004: API Gateway Circuit Breaker

### Trigger Conditions
- Upstream service failure rate > 50%
- Gateway returning 502/503/504 in bulk
- Circuit breaker opened alert

### Diagnosis
```bash
# Check nginx upstream health
nginx -t
curl -s http://localhost/nginx_status
cat /var/log/nginx/error.log | tail -100

# Check upstream targets
kubectl get endpoints <service-name> -n <namespace>
kubectl describe service <service-name> -n <namespace>
```

### Remediation
1. Identify failing upstream: check logs for specific 502/503 patterns
2. Remove unhealthy upstreams from load balancer rotation
3. Scale healthy pods: `kubectl scale deployment/<name> --replicas=5`
4. If circuit breaker block: wait for upstream recovery, then close manually
5. Enable degraded mode: return cached or default responses

---

## PLAYBOOK-005: Memory Leak / OOM

### Trigger Conditions
- Memory usage steadily climbing over time
- OOMKilled events in pods
- JVM heap dump required
- Node memory pressure

### Diagnosis
```bash
# Pod memory usage
kubectl top pods -n <namespace>
kubectl top nodes

# Node memory details
ssh <node-ip> 'cat /proc/meminfo'
ssh <node-ip> 'ps aux --sort=-%mem | head -20'

# Java heap analysis
kubectl exec -it <pod> -- jcmd 1 VM.native_memory summary
kubectl exec -it <pod> -- jmap -dump:format=b,file=/tmp/heap.hprof 1
```

### Remediation
1. Restart affected pod immediately (temporary fix)
2. Capture heap dump before restart for analysis
3. Increase memory limit as temporary measure
4. Analysis: look for growing object references, connection pools not released
5. Fix: patch the leak (unclosed streams, static collections, caches without eviction)
6. Test fix in staging under load before deploying

---

## PLAYBOOK-006: Kafka Consumer Lag

### Trigger Conditions
- Consumer lag growing continuously
- Messages processing slower than production rate
- Lag alert threshold exceeded

### Diagnosis
```bash
# Check consumer group lag
kafka-consumer-groups.sh --bootstrap-server <broker>:9092 \
  --describe --group <consumer-group>

# Check topic partition leadership
kafka-topics.sh --bootstrap-server <broker>:9092 --describe --topic <topic>

# Monitor throughput
kafka-consumer-perf-test.sh --broker-list <broker>:9092 \
  --topic <topic> --messages 1000
```

### Remediation
1. Increase consumer partitions: `kafka-topics.sh --alter --partitions <N>`
2. Scale consumer instances: `kubectl scale deployment/<consumer> --replicas=<N>`
3. Check consumer for slow processing (DB locks, external API calls)
4. Increase `fetch.max.bytes` and `max.poll.records` in consumer config
5. If lag is unrecoverable: reset consumer offset to current position (data loss risk)

---

## PLAYBOOK-007: Stripe / Payment API Timeout

### Trigger Conditions
- Stripe API calls timing out after 30s
- Payment success rate < 99%
- Webhook delivery failures

### Diagnosis
```bash
# Check Stripe status
curl -s https://status.stripe.com/api/v2/status.json | jq .status.indicator

# Check payment service logs
kubectl logs deployment/payment-service -n <namespace> --tail=200 | grep -i stripe

# Test connectivity
kubectl exec -it <pod> -- curl -I https://api.stripe.com
```

### Remediation
1. If Stripe incident: implement exponential retry with idempotency keys
2. Enable async processing: queue payments, process with retries
3. Add circuit breaker around Stripe calls
4. Return "pending" status to user, confirm via webhook
5. Monitor Stripe webhooks for delayed confirmations

---

## PLAYBOOK-008: Disk Space Exhaustion

### Trigger Conditions
- Disk usage > 85%
- AlertManager disk_almost_full firing
- Container unable to write logs

### Diagnosis
```bash
df -h
du -sh /var/log/* | sort -rh | head -10
du -sh /var/lib/docker/* | sort -rh | head -10
find /tmp -size +100M -type f 2>/dev/null
```

### Remediation
```bash
# Docker cleanup
docker system prune -af
docker volume prune -f

# Log cleanup (careful)
journalctl --vacuum-size=500M
find /var/log -name "*.gz" -mtime +7 -delete

# Kubernetes: clean evicted pods
kubectl get pods --all-namespaces | grep Evicted | \
  awk '{print "kubectl delete pod " $2 " -n " $1}' | bash
```

### Prevention
- Set log retention policies (max 7 days or 2GB)
- Enable Docker log rotation in `/etc/docker/daemon.json`
- Add disk usage alerting at 75%

---

## PLAYBOOK-009: JWT / Authentication Failures

### Trigger Conditions
- Spike in 401 Unauthorized errors
- JWT validation failures in logs
- User session invalidation

### Diagnosis Commands
```bash
# Decode JWT to check expiry
echo "<jwt-token>" | cut -d. -f2 | base64 -d | jq .exp

# Check auth service logs
kubectl logs deployment/auth-service --tail=100 | grep -i "jwt\|token\|auth"

# Verify secret/key availability
kubectl get secret jwt-signing-key -n <namespace>
```

### Remediation
1. If tokens expired: rotate signing key and force re-authentication
2. If clock skew: sync NTP on all nodes (`timedatectl status`)
3. If JWKS endpoint down: restart auth service
4. Increase token TTL as temporary measure
5. Implement token refresh flow if not already present

---

## PLAYBOOK-010: Security Incident — Brute Force / Unauthorized Access

### Trigger Conditions
- Multiple failed login attempts from single IP
- Unusual access patterns in auth logs
- Rate limit alerts from WAF

### Immediate Actions
```bash
# Block attacking IP at network level
iptables -I INPUT -s <attacker-ip> -j DROP

# Or via nginx
echo "deny <attacker-ip>;" >> /etc/nginx/conf.d/blocklist.conf
nginx -s reload

# Check auth logs
grep "failed login" /var/log/auth.log | awk '{print $NF}' | sort | uniq -c | sort -rn
```

### Investigation
1. Identify accounts targeted
2. Force password reset for targeted accounts
3. Enable MFA if not already
4. Review and rotate API keys if compromised
5. File security incident report

### Prevention
- Implement rate limiting on auth endpoints
- Add CAPTCHA after 5 failed attempts
- Enable geo-blocking for unexpected regions
- Set up fail2ban: `apt-get install fail2ban`
