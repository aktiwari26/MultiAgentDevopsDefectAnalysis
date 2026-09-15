# Other / Unclassified Systems — Incident Response Guide

## Overview

This guide covers incidents from systems that do not fit standard
IT infrastructure categories (Kubernetes, Nginx, CloudWatch, Application,
Database). Common examples include:

- **IoT / Edge Computing**: MQTT brokers, OPC-UA servers, Modbus devices,
  SCADA/PLC systems, industrial sensors
- **Network / Firewall**: Cisco, Palo Alto, pfSense, iptables anomaly logs
- **Embedded Systems**: Firmware crash dumps, watchdog resets, bare-metal logs
- **Proprietary Platforms**: Legacy ERP systems, vendor appliances, mainframe
- **Custom Scripts / Cron Jobs**: Scheduled task failures, ETL pipeline errors

---

## Severity Guidelines for Unknown/Other Systems

| Condition | Suggested Severity |
|---|---|
| Physical safety risk / plant shutdown | P1 |
| Revenue impact > $10k/hr OR full service stoppage | P1 |
| Significant data loss or production halt | P2 |
| Degraded throughput / partial outage | P2–P3 |
| Monitoring gaps, isolated failures | P3–P4 |
| Warnings with no immediate impact | P4 |

When classifying "other" systems: **err on the side of higher severity**
and let the human operator downgrade after review.

---

## General Investigation Steps

### Step 1: Identify the System Type
- Read ALL log lines before concluding: vendor names, protocol names
  (MQTT, Modbus, OPC-UA, SNMP, etc.) are strong indicators.
- Check for proprietary error codes — search vendor docs for exact codes.
- If truly unidentifiable, treat as P3 minimum.

### Step 2: Assess Business Impact
- Is production halted? Are physical safety systems involved?
- Quantify: units/hour lost, revenue/hour, users affected.
- Check if the system feeds others (cascade risk).

### Step 3: Collect Context
- System name, location, last change (firmware/config/deployment).
- Recent maintenance or updates (common root cause: bad update).
- Connectivity to other IT systems (databases, cloud APIs, message queues).

### Step 4: Containment
- **If safety risk**: escalate to on-site team FIRST, then IT.
- **If data loss**: stop writes, snapshot state, engage vendor support.
- **If cascading**: isolate the failing component.

### Step 5: Engage the Right Team
- IoT/OT incidents: engage OT (Operational Technology) team.
- Vendor appliances: open support ticket immediately.
- Proprietary systems: consult internal SME or vendor runbook.

---

## Common Patterns in "Other" Logs

### IoT / SCADA Patterns
```
MQTT_BROKER: Client X DISCONNECTED  →  Network partition or device power loss
PLC_FAULT: ESTOP signal             →  Hardware fault, sensor out of range
OPC-UA: BadCommunicationError       →  PLC unreachable, firmware crash
MODBUS CRC mismatch                 →  Wire fault, EMI interference, bad firmware
Historian data gap                  →  Data pipeline broken — check time-series DB
Temperature/pressure out of range   →  Physical issue — may need on-site inspection
```

### Network / Firewall Patterns
```
DROP/REJECT spike                   →  DDoS, misconfiguration, or attack
Interface flap                      →  Cable fault, SFP issue, spanning-tree loop
BGP session down                    →  ISP issue or config change
ARP storm / MAC flooding            →  Switch loop or spanning-tree failure
```

### ETL / Script Patterns
```
Exit code != 0                      →  Script failure — check stderr/stdout
Data validation failure             →  Upstream schema change
File not found / permission denied  →  Deployment issue, missing credentials
Timeout exceeded                    →  Downstream system slow or unavailable
```

---

## Remediation Playbook

### For IoT/SCADA Incidents
1. **Do not restart PLCs or sensors without engineering sign-off.**
2. Check network layer first: ping/traceroute from edge gateway to devices.
3. Verify power supply to affected sensor nodes.
4. Check firmware update logs — rollback if recent update coincides with failure.
5. Restart MQTT broker only if all devices show connectivity issues.
6. Review historian write-back to ensure no data loss window exceeds SLA.

### For Unknown Vendor Systems
1. Document all error codes verbatim — do not paraphrase.
2. Open P1 vendor support ticket if production-impacting.
3. Collect heap/core dumps if available.
4. Do NOT upgrade firmware/software during incident.
5. Check vendor status page for known issues.

---

## JIRA Ticket Template for "Other" Category

```
Summary: [P4/Other] Unclassified system incident — <system name>

Description:
- Log source: <device/service name>
- Log type: other (classified by DevOps AI)
- Detected at: <timestamp>
- Possible impact: <describe>
- Recommended action: Manual investigation required
- Auto-analysis: See attached DevOps report

Labels: other-system, needs-human-review, auto-triaged
Priority: Low (upgrade if impact confirmed)
```

---

## Escalation Contacts

- OT/SCADA incidents: ops-team@company.com
- Network/Firewall: netops@company.com
- Unknown vendor systems: vendor-support@company.com (reference contract ID)
- General escalation: oncall@company.com or PagerDuty rotation
