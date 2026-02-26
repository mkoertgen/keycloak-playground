# CloudNativePG Alert Rules for Keycloak

> **Scope:** Optional alert rules for production CNPG (CloudNativePG) deployments backing Keycloak  
> **Applies to:** Kubernetes environments using CNPG operator (not the docker-compose setup)

This guide provides Prometheus alert rules for monitoring CloudNativePG clusters running Keycloak databases in production. The playground docker-compose setup doesn't use CNPG, but these rules are useful if you deploy to Kubernetes with the [CloudNativePG operator](https://cloudnative-pg.io/).

---

## Why These Rules Matter

Stock CNPG Helm charts include basic infrastructure alerts (pod placement, disk space, connection limits) but miss critical operational signals:

| Missing Alert Category | Impact                                 |
| ---------------------- | -------------------------------------- |
| Backup health          | Silent backup failures                 |
| WAL archiving          | Corrupted PITR recovery window         |
| Long transactions      | Lock contention, blocked queries       |
| Idle-in-transaction    | Connection pool leaks                  |
| Checkpoint pressure    | Write storms, degraded I/O performance |
| Failover detection     | Untracked primary promotion events     |

---

## Alert Rules

### Cluster Health

```yaml
groups:
  - name: cnpg-cluster-health
    rules:
      - alert: CNPGClusterNotHealthy
        expr: |
          cnpg_cluster_ready_instances{namespace="your-namespace"}
            < cnpg_cluster_instances{namespace="your-namespace"}
        for: 5m
        labels:
          severity: warning
          service: database
        annotations:
          summary: "CNPG: cluster degraded"
          description: "Cluster {{ $labels.cluster }} has {{ $value }} ready instances (< expected total). Pod crash or primary failover detected."
          runbook: https://cloudnative-pg.io/documentation/current/troubleshooting/

      - alert: CNPGClusterDown
        expr: |
          cnpg_cluster_ready_instances{namespace="your-namespace"} == 0
        for: 1m
        labels:
          severity: critical
          service: database
        annotations:
          summary: "CNPG: cluster completely down"
          description: "Zero ready instances. Database unavailable."
          runbook: https://cloudnative-pg.io/documentation/current/troubleshooting/

      - alert: CNPGHighReplicationLag
        expr: |
          cnpg_pg_replication_lag{namespace="your-namespace"} > 30
        for: 5m
        labels:
          severity: warning
          service: database
        annotations:
          summary: "CNPG: replication lag >30s"
          description: "Replication lag {{ $value }}s on {{ $labels.pod }}. Check network or replica performance."

      - alert: CNPGReplicationLagCritical
        expr: |
          cnpg_pg_replication_lag{namespace="your-namespace"} > 300
        for: 2m
        labels:
          severity: critical
          service: database
        annotations:
          summary: "CNPG: replication lag >5 minutes"
          description: "Lag {{ $value }}s - failover would cause data loss. Investigate immediately."

      - alert: CNPGReplicationNotStreaming
        expr: |
          cnpg_pg_replication_streaming_replicas{
            namespace="your-namespace",
            pod=~".*-1$"
          } == 0
        for: 3m
        labels:
          severity: critical
          service: database
        annotations:
          summary: "CNPG: PRIMARY has zero streaming replicas"
          description: "No replicas attached to PRIMARY. Any crash risks data loss (no instant failover available)."
```

### Backup & WAL Archiving

```yaml
- name: cnpg-backup-wal
  rules:
    - alert: CNPGNoRecentWALArchive
      expr: |
        time() - cnpg_pg_stat_archiver_last_archived_time{
          namespace="your-namespace"
        } > 3600
      for: 15m
      labels:
        severity: warning
        service: database
      annotations:
        summary: "CNPG: no WAL archived in >1 hour"
        description: "PITR window not advancing. Check S3/object storage connectivity."
        runbook: https://cloudnative-pg.io/documentation/current/wal_archiving/

    - alert: CNPGArchiveFailure
      expr: |
        increase(cnpg_pg_stat_archiver_failed_count{
          namespace="your-namespace"
        }[30m]) > 0
      for: 5m
      labels:
        severity: critical
        service: database
      annotations:
        summary: "CNPG: WAL archive failures"
        description: "{{ $value }} failed WAL archives in last 30m. PITR continuity broken."
        runbook: https://cloudnative-pg.io/documentation/current/wal_archiving/

    - alert: CNPGBackupNoRecentSuccess
      expr: |
        (time() - max(cnpg_collector_last_collection_time{
          namespace="your-namespace",
          pod=~".*-([1-9][0-9]*)$"
        })) > 90000
      for: 10m
      labels:
        severity: critical
        service: database
      annotations:
        summary: "CNPG: no backup heartbeat in >25 hours"
        description: "No backup collection in 25h. Scheduled backups may be failing."
        runbook: https://cloudnative-pg.io/documentation/current/backup_recovery/
```

### Performance & Transaction Health

```yaml
- name: cnpg-performance
  interval: 30s
  rules:
    - alert: CNPGLongRunningTransaction
      expr: |
        max(cnpg_backends_max_tx_duration_seconds{
          namespace="your-namespace",
          pod=~".*-([1-9][0-9]*)$"
        }) > 300
      for: 2m
      labels:
        severity: warning
        service: database
      annotations:
        summary: "CNPG: transaction >5 minutes"
        description: "Transaction running {{ $value | humanizeDuration }}. Holds locks, blocks autovacuum."

    - alert: CNPGLongRunningTransactionCritical
      expr: |
        max(cnpg_backends_max_tx_duration_seconds{
          namespace="your-namespace",
          pod=~".*-([1-9][0-9]*)$"
        }) > 1800
      for: 2m
      labels:
        severity: critical
        service: database
      annotations:
        summary: "CNPG: transaction >30 minutes - likely stuck"
        description: "Transaction open for {{ $value | humanizeDuration }}. Connection pool exhaustion risk."

    - alert: CNPGIdleInTransactionConnections
      expr: |
        sum(cnpg_backends_waiting{
          namespace="your-namespace",
          pod=~".*-([1-9][0-9]*)$"
        }) > 3
      for: 5m
      labels:
        severity: warning
        service: database
      annotations:
        summary: "CNPG: multiple blocked/waiting connections"
        description: "{{ $value }} connections waiting. Lock contention or stuck transaction."

    - alert: CNPGHighCheckpointFrequency
      expr: |
        rate(cnpg_pg_stat_bgwriter_checkpoints_req_total{
          namespace="your-namespace",
          pod=~".*-1$"
        }[15m]) > 0.5
      for: 10m
      labels:
        severity: warning
        service: database
      annotations:
        summary: "CNPG: high checkpoint rate"
        description: "{{ $value | humanize }} requested checkpoints/s. Heavy write pressure detected."
```

### Failover Detection

```yaml
- name: cnpg-failover
  interval: 15s
  rules:
    - alert: CNPGPrimaryChanged
      expr: |
        changes(cnpg_pg_replication_is_primary{
          namespace="your-namespace",
          pod=~".*-([1-9][0-9]*)$"
        }[10m]) > 0
      for: 0m
      labels:
        severity: warning
        service: database
      annotations:
        summary: "CNPG: PRIMARY changed - failover detected"
        description: "Failover or switchover in last 10m. Verify Keycloak reconnected to new primary."

    - alert: CNPGFailoverDetected
      expr: |
        changes(cnpg_collector_up{namespace="your-namespace", role="primary"}[5m]) > 0
      for: 0m
      labels:
        severity: warning
        service: database
      annotations:
        summary: "CNPG: primary collector role changed"
        description: "Primary role changed. Check application connection pool refresh."
```

---

## Runbooks

### CNPGClusterNotHealthy / CNPGClusterDown

**Symptom:** One or more CNPG pods not ready, or entire cluster down

**Investigation:**

```bash
# Check pod status
kubectl get pods -n your-namespace -l cnpg.io/cluster=your-cluster

# Check recent events
kubectl get events -n your-namespace --sort-by='.lastTimestamp' | tail -20

# Check pod logs (replace pod-1 with actual pod name)
kubectl logs -n your-namespace your-cluster-1 --tail=100

# Check CNPG operator logs
kubectl logs -n cnpg-system deployment/cnpg-controller-manager
```

**Common causes:**

- PVC full (disk space exhaustion)
- PostgreSQL crash (check logs for `PANIC` or `FATAL`)
- Network partition between primary and replicas
- Node resource exhaustion (OOM, CPU throttling)

**Resolution:**

- If PRIMARY failed: CNPG auto-promotes a replica (wait 2-5min for reconciliation)
- If replica failed: Check node/PVC status, review pod logs
- If entire cluster down: Check namespace events and CNPG operator logs

---

### CNPGArchiveFailure / CNPGNoRecentWALArchive

**Symptom:** WAL segments not being archived to object storage

**Investigation:**

```bash
# Check archiver status in PostgreSQL
kubectl exec -n your-namespace your-cluster-1 -- \
  psql -U postgres -c "SELECT * FROM pg_stat_archiver;"

# Check CNPG backup configuration
kubectl get cluster -n your-namespace your-cluster -o yaml | grep -A 20 backup

# Check object storage credentials (secret)
kubectl get secret -n your-namespace your-backup-secret -o yaml
```

**Common causes:**

- Invalid S3/object storage credentials
- Network connectivity to storage backend lost
- Insufficient IAM/RBAC permissions on bucket
- Bucket does not exist or was deleted
- WAL segment size misconfiguration

**Resolution:**

1. Verify credentials: Test S3 access with `aws s3 ls s3://bucket-name/` (or equivalent)
2. Check network policies: Ensure pods can reach object storage endpoint
3. Review CNPG logs for detailed error messages
4. If credentials rotated: Update secret and trigger cluster reconciliation

**Critical:** Failed WAL archiving breaks point-in-time recovery. Resolve immediately.

---

### CNPGLongRunningTransaction

**Symptom:** Transaction open for >5 minutes

**Investigation:**

```bash
# Find long-running transactions
kubectl exec -n your-namespace your-cluster-1 -- \
  psql -U postgres -c "
    SELECT pid, usename, state, state_change, query_start, query
    FROM pg_stat_activity
    WHERE state != 'idle'
      AND xact_start < now() - interval '5 minutes'
    ORDER BY xact_start;
  "

# Check for locks held by long transaction
kubectl exec -n your-namespace your-cluster-1 -- \
  psql -U postgres -c "
    SELECT l.pid, l.mode, l.granted, a.query
    FROM pg_locks l
    JOIN pg_stat_activity a ON l.pid = a.pid
    WHERE a.xact_start < now() - interval '5 minutes';
  "
```

**Common causes (Keycloak context):**

- Abandoned admin console session with open transaction
- Stuck user migration job
- Long-running batch operations (user import, realm export)
- Application bug (missing commit/rollback)

**Resolution:**

1. If query is legitimate but slow: Let it finish (monitor progress)
2. If stuck or abandoned:
   ```sql
   -- Terminate the backend (replace PID):
   SELECT pg_terminate_backend(12345);
   ```
3. If recurring: Review application transaction management
4. Consider connection pool timeout tuning in Keycloak JDBC config

---

### CNPGReplicationNotStreaming

**Symptom:** PRIMARY has zero streaming replicas attached

**Investigation:**

```bash
# Check replication status on PRIMARY
kubectl exec -n your-namespace your-cluster-1 -- \
  psql -U postgres -c "SELECT * FROM pg_stat_replication;"

# Check replica logs
kubectl logs -n your-namespace your-cluster-2 --tail=100

# Check network connectivity between pods
kubectl exec -n your-namespace your-cluster-2 -- \
  nc -zv your-cluster-rw 5432
```

**Common causes:**

- Replica crashed and hasn't restarted yet
- Replication slot deleted or full
- Authentication failure (replication user credentials)
- Network policy blocking replication traffic
- WAL segments missing on primary (replica too far behind)

**Resolution:**

1. **If replica pod is down:** Check pod events and restart if necessary
2. **If replication slot issue:**

   ```sql
   -- Check slots:
   SELECT slot_name, active, restart_lsn FROM pg_replication_slots;

   -- If inactive and old, may need to drop and recreate:
   SELECT pg_drop_replication_slot('slot_name');
   ```

3. **If replica too far behind:** May require full replica rebuild (CNPG handles this automatically via `pg_basebackup`)

**Critical:** Operating without replicas means:

- No high availability (crash = full restore required)
- Potential data loss if PRIMARY crashes before backup window
- Production deployments should never run in this state

---

### CNPGPrimaryChanged / CNPGFailoverDetected

**Symptom:** Primary role switched to another pod (automatic failover or manual switchover)

**Investigation:**

```bash
# Verify current primary
kubectl get cluster -n your-namespace your-cluster -o jsonpath='{.status.currentPrimary}'

# Check recent events for failover reason
kubectl get events -n your-namespace --field-selector involvedObject.name=your-cluster

# Verify Keycloak reconnected successfully
kubectl logs -n your-namespace deployment/keycloak | grep -i "connection\|pool\|database"
```

**Expected behavior:** CNPG promotes a healthy replica to primary automatically if:

- PRIMARY pod crashes
- PRIMARY node fails or is drained
- PRIMARY becomes unresponsive (readiness/liveness probes fail)

**Action required:**

1. **Verify application connectivity:** Keycloak should reconnect automatically to new primary via `cnpg-cluster-rw` service (CNPG updates DNS)
2. **Check for connection errors:** Look for JDBC connection exceptions in Keycloak logs
3. **Monitor replication lag:** After failover, new replicas may need time to catch up
4. **Identify root cause:** Review logs on old primary pod if still available

**Connection pool refresh:** Most JDBC pools (HikariCP, used by Keycloak) handle failover gracefully:

- Stale connections to old primary fail and are evicted
- New connections route to new primary via updated service endpoint
- May see brief spike in connection errors during 10-30s transition window

---

## Deployment

### Prometheus Configuration

Add rules to your Prometheus config:

```yaml
# prometheus.yml
rule_files:
  - /etc/prometheus/rules/cnpg-alerts.yml

# Mount rules file in Prometheus pod/container
```

### Prometheus Operator (Kubernetes)

Deploy as `PrometheusRule` custom resource:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: cnpg-keycloak-alerts
  namespace: monitoring
spec:
  groups:
    - name: cnpg-cluster-health
      rules:
        # ... paste rules from above ...
```

### Alert Routing

Example Alertmanager config:

```yaml
route:
  routes:
    - match:
        service: database
      receiver: database-oncall
      group_by: [alertname, cluster]
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h

receivers:
  - name: database-oncall
    slack_configs:
      - channel: "#database-alerts"
        title: "{{ .GroupLabels.alertname }}"
        text: "{{ range .Alerts }}{{ .Annotations.description }}{{ end }}"
```

---

## Metrics Reference

CNPG exports metrics via `cnpg-collector` sidecar container. Key metrics:

| Metric                                        | Description                          |
| --------------------------------------------- | ------------------------------------ |
| `cnpg_cluster_ready_instances`                | Number of ready pods in cluster      |
| `cnpg_cluster_instances`                      | Total expected pods                  |
| `cnpg_pg_replication_lag`                     | Replication lag in seconds           |
| `cnpg_pg_replication_streaming_replicas`      | Number of active streaming replicas  |
| `cnpg_pg_stat_archiver_last_archived_time`    | Last successful WAL archive (epoch)  |
| `cnpg_pg_stat_archiver_failed_count`          | Failed WAL archive attempts          |
| `cnpg_backends_max_tx_duration_seconds`       | Longest running transaction duration |
| `cnpg_backends_waiting`                       | Connections in waiting state         |
| `cnpg_pg_stat_bgwriter_checkpoints_req_total` | Requested checkpoints (write load)   |
| `cnpg_pg_replication_is_primary`              | 1 if pod is PRIMARY, 0 otherwise     |

**Metrics endpoint:** `http://<pod-ip>:9187/metrics` (via ServiceMonitor)

---

## Testing Alerts

Trigger test scenarios in non-production:

```bash
# Simulate high replication lag (pause replica)
kubectl exec -n your-namespace your-cluster-2 -- \
  psql -U postgres -c "SELECT pg_wal_replay_pause();"
# Resume: SELECT pg_wal_replay_resume();

# Simulate long transaction
kubectl exec -n your-namespace your-cluster-1 -- \
  psql -U postgres -c "BEGIN; SELECT pg_sleep(600);"
# Cancel in another session

# Simulate failover (delete PRIMARY pod)
kubectl delete pod -n your-namespace your-cluster-1
# CNPG auto-promotes replica
```

---

## Further Reading

- [CloudNativePG Documentation](https://cloudnative-pg.io/documentation/current/)
- [PostgreSQL Monitoring Guide](https://www.postgresql.org/docs/current/monitoring-stats.html)
- [CNPG Backup & Recovery](https://cloudnative-pg.io/documentation/current/backup_recovery/)
- [Prometheus Alerting Best Practices](https://prometheus.io/docs/practices/alerting/)
