export const agentConfig = [
  { id: 'classifier', label: 'Classifier', icon: 'Tag' },
  { id: 'severity', label: 'Severity', icon: 'AlertTriangle' },
  { id: 'rootCause', label: 'Root Cause', icon: 'Search' },
  { id: 'remediation', label: 'Remediation', icon: 'Wrench' },
  { id: 'runbook', label: 'Runbook', icon: 'BookOpen' },
  { id: 'jira', label: 'JIRA', icon: 'Ticket' },
  { id: 'alerts', label: 'Alerts', icon: 'Bell' },
];

export const sampleLogs = [
  {
    id: 1,
    title: 'High CPU on k8s node',
    description: 'Node cpu-pressure condition detected across 3 pods in production',
    severity: 'critical',
    source: 'kubernetes',
  },
  {
    id: 2,
    title: 'Database connection pool exhausted',
    description: 'PostgreSQL max connections reached (100/100) on db-primary',
    severity: 'critical',
    source: 'database',
  },
  {
    id: 3,
    title: 'API latency spike detected',
    description: 'p99 latency exceeded 5s for /api/v1/orders endpoint',
    severity: 'warning',
    source: 'application',
  },
  {
    id: 4,
    title: 'Memory leak in payment service',
    description: 'Heap usage at 92% with steady growth over 4h',
    severity: 'error',
    source: 'application',
  },
  {
    id: 5,
    title: 'SSL certificate expiring',
    description: 'Wildcard cert for *.acme.com expires in 72 hours',
    severity: 'warning',
    source: 'infrastructure',
  },
  {
    id: 6,
    title: 'Disk space alert on log volume',
    description: '/var/log mounted volume at 85% capacity',
    severity: 'info',
    source: 'infrastructure',
  },
];

export const severityColors = {
  critical: { bg: 'rgba(239,68,68,0.15)', text: '#fca5a5', dot: '#ef4444' },
  error: { bg: 'rgba(249,115,22,0.15)', text: '#fdba74', dot: '#f97316' },
  warning: { bg: 'rgba(234,179,8,0.15)', text: '#fde68a', dot: '#eab308' },
  info: { bg: 'rgba(59,130,246,0.15)', text: '#93c5fd', dot: '#3b82f6' },
};

export const kpiData = [
  {
    title: 'Total Runs',
    value: '2,847',
    change: '+12.3%',
    positive: true,
    sparkline: [30, 45, 38, 52, 48, 61, 55, 68, 72, 65, 78, 82],
  },
  {
    title: 'Success Rate',
    value: '98.7%',
    change: '+0.5%',
    positive: true,
    sparkline: [95, 96, 97, 96, 98, 97, 98, 99, 98, 99, 98, 99],
  },
  {
    title: 'Tokens Used',
    value: '14.2M',
    change: '+8.1%',
    positive: false,
    sparkline: [800, 1100, 950, 1300, 1200, 1500, 1400, 1700, 1600, 1900, 1800, 2100],
  },
  {
    title: 'Avg Response Time',
    value: '2.4s',
    change: '-18.2%',
    positive: true,
    sparkline: [4.2, 3.8, 3.5, 3.2, 3.0, 2.8, 2.7, 2.6, 2.5, 2.4, 2.4, 2.3],
  },
  {
    title: 'Issues Auto-Resolved',
    value: '1,532',
    change: '+23.7%',
    positive: true,
    sparkline: [80, 95, 110, 105, 130, 125, 140, 155, 150, 165, 170, 182],
  },
  {
    title: 'Active Incidents',
    value: '3',
    change: '–',
    positive: true,
    sparkline: [8, 7, 5, 6, 4, 5, 3, 4, 3, 2, 3, 3],
  },
];

export const issuesOverTime = [
  { month: 'Jan', critical: 12, warning: 28, info: 45 },
  { month: 'Feb', critical: 8, warning: 32, info: 52 },
  { month: 'Mar', critical: 15, warning: 25, info: 48 },
  { month: 'Apr', critical: 10, warning: 30, info: 55 },
  { month: 'May', critical: 18, warning: 22, info: 42 },
  { month: 'Jun', critical: 7, warning: 35, info: 58 },
  { month: 'Jul', critical: 14, warning: 28, info: 50 },
  { month: 'Aug', critical: 9, warning: 33, info: 53 },
  { month: 'Sep', critical: 20, warning: 20, info: 38 },
  { month: 'Oct', critical: 11, warning: 29, info: 47 },
  { month: 'Nov', critical: 6, warning: 31, info: 60 },
  { month: 'Dec', critical: 16, warning: 26, info: 44 },
];

export const logTypeDistribution = [
  { type: 'Kubernetes', count: 185 },
  { type: 'Application', count: 312 },
  { type: 'Database', count: 98 },
  { type: 'Network', count: 67 },
  { type: 'Security', count: 43 },
  { type: 'Infrastructure', count: 156 },
];

export const pipelineTimeByService = [
  { service: 'Classifier', time: 0.8 },
  { service: 'Severity', time: 0.5 },
  { service: 'Root Cause', time: 2.1 },
  { service: 'Remediation', time: 1.7 },
  { service: 'Runbook', time: 0.9 },
  { service: 'JIRA', time: 0.4 },
  { service: 'Alerts', time: 0.3 },
];

export const classifiedIssues = [
  { id: 'INC-001', title: 'CPU spike on prod-01', severity: 'Critical', status: 'Resolved', agent: 'Classifier', time: '12s', date: '2026-05-09' },
  { id: 'INC-002', title: 'DB connection pool full', severity: 'Critical', status: 'Resolved', agent: 'Severity', time: '8s', date: '2026-05-09' },
  { id: 'INC-003', title: 'API /orders p99 latency', severity: 'Warning', status: 'Investigating', agent: 'Root Cause', time: '24s', date: '2026-05-08' },
  { id: 'INC-004', title: 'Memory leak payment-svc', severity: 'Error', status: 'Resolved', agent: 'Remediation', time: '18s', date: '2026-05-08' },
  { id: 'INC-005', title: 'SSL cert expiring', severity: 'Warning', status: 'Open', agent: 'Runbook', time: '6s', date: '2026-05-07' },
  { id: 'INC-006', title: 'Disk /var/log 85%', severity: 'Info', status: 'Resolved', agent: 'Alerts', time: '4s', date: '2026-05-07' },
  { id: 'INC-007', title: 'k8s node NotReady', severity: 'Critical', status: 'Resolved', agent: 'Classifier', time: '15s', date: '2026-05-06' },
  { id: 'INC-008', title: 'Redis OOM detected', severity: 'Error', status: 'Investigating', agent: 'JIRA', time: '11s', date: '2026-05-06' },
  { id: 'INC-009', title: 'CDN origin errors', severity: 'Warning', status: 'Resolved', agent: 'Root Cause', time: '22s', date: '2026-05-05' },
  { id: 'INC-010', title: 'Rate limiter triggered', severity: 'Info', status: 'Open', agent: 'Severity', time: '5s', date: '2026-05-05' },
];

export const ragPlaybooks = {
  'CPU Spike': `on_cpu_spike:
  detection:
    metric: node_cpu_seconds_total
    threshold: "> 80%"
    window: 5m
  diagnosis:
    - check_top_consumers: "kubectl top pods -n production --sort-by=cpu"
    - analyze_recent_deploys: "kubectl rollout history deploy -n production"
  remediation:
    - scale_horizontal: "kubectl scale deploy/\${service} --replicas=\${current+2}"
    - restart_selector: "kubectl rollout restart deploy/\${service}"`,
  'Memory Leak': `on_memory_leak:
  detection:
    metric: container_memory_working_set_bytes
    threshold: "> 90%"
    trend: "increasing over 1h"
  diagnosis:
    - heap_dump: "jmap -dump:live,format=b,file=/tmp/heap.hprof \${pid}"
    - gc_analysis: "jstat -gcutil \${pid} 1000 10"
  remediation:
    - rolling_restart: "kubectl rollout restart deploy/\${service}"
    - scale_up: "kubectl scale deploy/\${service} --replicas=\${current+3}"`,
  'DB Connection Exhaustion': `on_db_exhaustion:
  detection:
    metric: pg_stat_activity.count
    threshold: ">= max_connections * 0.9"
  diagnosis:
    - check_idle: "SELECT count(*) FROM pg_stat_activity WHERE state = 'idle'"
    - check_blocked: "SELECT count(*) FROM pg_locks WHERE granted = false"
  remediation:
    - terminate_idle: "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND age > '30m'"
    - pool_resize: "ALTER SYSTEM SET max_connections = \${current * 1.5}"`,
};
