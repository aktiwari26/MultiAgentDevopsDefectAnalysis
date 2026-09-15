# Standard Incident Response SOP

## Overview
This document defines the standard operating procedure for incident response at all severity levels. All SRE and DevOps engineers must follow this process for any production incident.

---

## Severity Classification

| Level | Label | Definition | Response Time | Example |
|-------|-------|------------|--------------|---------|
| P1 | CRITICAL | Complete production outage, data loss risk, revenue impact | 15 minutes | Payment service down, database corruption |
| P2 | HIGH | Major degradation, partial outage, >20% error rate | 30 minutes | API latency >5s, auth service degraded |
| P3 | MEDIUM | Non-critical service impact, elevated errors, no customer impact | 2 hours | Staging environment issues, metrics anomalies |
| P4 | LOW | Minor issues, cosmetic, informational | Next business day | Log warnings, capacity planning flags |

---

## Phase 1: Detection

### Automated Detection Signals
- Alerting system (PagerDuty, OpsGenie) fires
- Monitoring dashboard (Grafana, Datadog) anomaly detected
- Customer complaint escalation
- SLO burn rate alert

### Initial Assessment (First 5 Minutes)
1. Acknowledge the alert in alerting system
2. Assess severity using the classification table above
3. Open the incident channel: `#incident-YYYY-MM-DD-<short-description>`
4. Post initial status update with what is known

### Detection Commands
```bash
# Check overall system health
kubectl get pods --all-namespaces | grep -v Running
kubectl get nodes
kubectl top nodes

# Check error rates
tail -f /var/log/nginx/error.log
journalctl -u <service-name> -f --since "5 minutes ago"

# Check recent deployments
kubectl rollout history deployment/<name>
git log --oneline -10
```

---

## Phase 2: Triage

### Establish Clear Ownership
- **Incident Commander**: Owns the incident, coordinates response
- **Technical Lead**: Drives technical investigation and resolution
- **Communications Lead**: Updates stakeholders and customers
- **Scribe**: Documents all actions and findings in real-time

### Triage Questions
1. What services are affected? What is the blast radius?
2. When did it start? Is it correlated with a deployment?
3. Is it getting worse, stable, or improving?
4. What is the customer impact?
5. Can we roll back to fix immediately?

### Triage Commands
```bash
# Correlate with deployments
kubectl rollout history deployment/payment-service

# Check service mesh / traffic
kubectl describe service <svc-name>
curl -s http://service:port/health | jq

# Check dependencies
kubectl get endpoints
kubectl exec -it <pod> -- nc -zv redis-host 6379
kubectl exec -it <pod> -- nc -zv postgres-host 5432
```

---

## Phase 3: Mitigation (Containment)

### Priority: Restore Service Before Root Cause

#### Option A — Rollback (Fastest, Preferred)
```bash
# Rollback to previous version
kubectl rollout undo deployment/<deployment-name>
kubectl rollout status deployment/<deployment-name>

# Verify rollback
kubectl get pods -n <namespace>
curl -s https://api.yourdomain.com/health
```

#### Option B — Scale Out
```bash
# Increase replicas to handle load
kubectl scale deployment/<name> --replicas=<count>
kubectl autoscale deployment/<name> --min=3 --max=10 --cpu-percent=70
```

#### Option C — Traffic Redirection
```bash
# Route traffic away from failing region/instance
# Update load balancer weights
# Enable maintenance mode / feature flag
```

#### Option D — Circuit Breaker Activation
- Enable circuit breaker at API gateway level
- Return cached/degraded responses
- Disable non-essential features

---

## Phase 4: Resolution

### Root Cause Analysis
1. Review logs from the time of incident onset
2. Correlate with recent changes (deployments, config changes, infra updates)
3. Reproduce in staging if possible
4. Identify the exact failure point and fix

### Permanent Fix Deployment
```bash
# Deploy the fix
kubectl apply -f deployment.yaml
kubectl rollout status deployment/<name>

# Verify all pods healthy
kubectl get pods -n <namespace>
kubectl describe deployment/<name>

# Run smoke tests
./scripts/smoke-test.sh production
```

### Verification Checklist
- [ ] Error rate back to baseline (<1%)
- [ ] Latency P99 within SLO
- [ ] All pods in Running state, restart count = 0
- [ ] Database connections healthy
- [ ] Cache hit rate restored
- [ ] End-to-end test passing
- [ ] Monitoring dashboards green

---

## Phase 5: Post-Incident Review

### Timeline: Within 48 hours of incident resolution

### PIR Document Template
1. **Incident Summary** — What happened, when, customer impact
2. **Timeline** — Minute-by-minute account of events
3. **Root Cause** — The underlying technical cause
4. **Contributing Factors** — What made it worse or harder to detect
5. **What Went Well** — Effective response actions
6. **What Went Poorly** — Gaps in detection, communication, or response
7. **Action Items** — Specific tasks with owners and due dates

### Action Item Categories
- **Monitoring**: Add/improve alerts to detect earlier
- **Automation**: Automate the manual remediation steps
- **Architecture**: Address systemic weaknesses
- **Process**: Improve runbooks, on-call training, escalation paths
- **Testing**: Add tests that would have caught this issue

---

## Communication Templates

### Initial Alert (First 5 min)
```
🚨 INCIDENT DETECTED — P{1/2}
Service: [affected services]
Impact: [customer impact description]
Started: [timestamp]
IC: @[incident commander]
Status: Investigating
Updates: Every 15 minutes
```

### Status Update
```
📊 INCIDENT UPDATE — P{1/2} | T+{minutes}
Status: [Investigating / Mitigating / Monitoring]
Impact: [current customer impact]
Actions: [what team is doing]
ETA: [estimated resolution time or "TBD"]
```

### Resolution Notice
```
✅ INCIDENT RESOLVED — P{1/2} | Duration: {X}h {Y}m
Service: [affected services] — RESTORED
Root Cause: [brief explanation]
Fix: [what was done]
PIR: Scheduled for [date/time]
```
