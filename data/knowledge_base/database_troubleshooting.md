# Database Troubleshooting Guide (PostgreSQL / MySQL / Redis)

## PostgreSQL

### Connection Issues

**Symptoms:**
- "too many connections" errors
- Connection timeouts
- pgBouncer pool exhaustion

**Diagnosis:**
```sql
-- Current connection count by state
SELECT state, count(*) FROM pg_stat_activity GROUP BY state;

-- Connections per application
SELECT application_name, count(*) FROM pg_stat_activity GROUP BY application_name ORDER BY count DESC;

-- Check max_connections setting
SHOW max_connections;

-- Active locks
SELECT pid, relname, mode, granted FROM pg_locks l JOIN pg_class c ON l.relation = c.oid WHERE NOT granted;
```

**Resolution:**
```bash
# Kill idle connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND query_start < now() - interval '10 minutes';

# Restart pgBouncer
systemctl restart pgbouncer

# Check pgBouncer pool stats
psql -p 6432 pgbouncer -c "SHOW POOLS;"
```

---

### Slow Query Diagnosis

**Enable slow query logging:**
```sql
-- In postgresql.conf
log_min_duration_statement = 1000  -- log queries > 1 second
log_line_prefix = '%t [%p]: [%l-1] '

-- Reload config
SELECT pg_reload_conf();
```

**Find slow queries:**
```sql
-- pg_stat_statements (requires extension)
SELECT query, calls, total_exec_time/calls AS avg_ms, rows/calls AS avg_rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;

-- Currently running slow queries
SELECT pid, now() - query_start AS runtime, query
FROM pg_stat_activity
WHERE state = 'active'
AND now() - query_start > interval '5 seconds'
ORDER BY runtime DESC;
```

**EXPLAIN ANALYZE a slow query:**
```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) 
SELECT * FROM orders WHERE customer_id = 12345;
```

**Common Fixes:**
- `CREATE INDEX CONCURRENTLY idx_name ON table(column);` — add missing index
- `VACUUM ANALYZE table_name;` — update statistics and remove dead tuples
- `SET work_mem = '256MB';` — increase sort/hash memory for complex queries

---

### Replication Lag

**Diagnosis:**
```sql
-- On primary: check replication state
SELECT client_addr, state, sent_lsn, write_lsn, flush_lsn, replay_lsn,
       (sent_lsn - replay_lsn) AS lag_bytes
FROM pg_stat_replication;

-- On replica: check lag
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

**Resolution:**
1. If lag is temporary: wait for replica to catch up
2. If lag is growing: check replica server load, I/O
3. Consider adding replica slots only if WAL retention is needed
4. If replica too far behind: rebuild from base backup

---

## Redis

### Memory Management

**Diagnosis:**
```bash
redis-cli info memory
redis-cli info stats | grep evicted
redis-cli --bigkeys           # Find large keys
redis-cli memory doctor       # Get recommendations
```

**Configuration Best Practices:**
```bash
# Set max memory with LRU eviction
redis-cli config set maxmemory 4gb
redis-cli config set maxmemory-policy allkeys-lru

# Enable lazy freeing for better performance
redis-cli config set lazyfree-lazy-eviction yes
```

### Slow Commands

**Diagnose:**
```bash
redis-cli slowlog get 10      # Last 10 slow commands
redis-cli slowlog len         # Number of slow commands logged
redis-cli --latency-history   # Latency over time
```

**Common Issues:**
- `KEYS *` — never use in production; use `SCAN` instead
- Large HMSET/LRANGE — paginate or use pipelines
- N+1 commands — use pipelining or Lua scripts

### Cluster Issues

```bash
redis-cli cluster info
redis-cli cluster nodes
redis-cli --cluster check <host>:<port>

# Fix cluster: reshard if needed
redis-cli --cluster reshard <host>:<port>
```

---

## MySQL / MariaDB

### Connection Pool Exhaustion

```sql
-- Show current connections
SHOW STATUS LIKE 'Threads_connected';
SHOW VARIABLES LIKE 'max_connections';

-- Show processlist
SHOW FULL PROCESSLIST;

-- Kill long-running queries
KILL QUERY <process_id>;
```

### InnoDB Lock Waits

```sql
-- Current lock waits
SELECT r.trx_id waiting_trx_id, r.trx_mysql_thread_id waiting_thread,
       b.trx_id blocking_trx_id, b.trx_mysql_thread_id blocking_thread
FROM information_schema.innodb_lock_waits w
INNER JOIN information_schema.innodb_trx b ON b.trx_id = w.blocking_trx_id
INNER JOIN information_schema.innodb_trx r ON r.trx_id = w.requesting_trx_id;
```

### Binary Log Rotation

```bash
# Show binary logs
mysqlbinlog --no-defaults /var/lib/mysql/mysql-bin.index

# Purge old logs (keep last 7 days)
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);
```

---

## Database Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|---------|
| PostgreSQL connections | 80% of max | 90% of max |
| Query duration P99 | > 1s | > 5s |
| Replication lag | > 30s | > 5min |
| Redis memory usage | > 75% | > 90% |
| Redis eviction rate | > 100/s | > 1000/s |
| Cache hit rate | < 90% | < 70% |
| MySQL slow queries | > 10/min | > 100/min |
| Dead tuple ratio | > 10% | > 30% |
