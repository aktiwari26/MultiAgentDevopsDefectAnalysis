# Kubernetes Troubleshooting Runbook

## CrashLoopBackOff

### Symptoms
- Pod status shows `CrashLoopBackOff`
- `kubectl get pods` shows restart count increasing
- `kubectl describe pod <name>` shows exit codes repeatedly

### Root Causes
1. Application crash on startup (OOM, misconfiguration, missing env vars)
2. Liveness probe failing too aggressively
3. Missing ConfigMap or Secret referenced by the pod
4. Image pull issues followed by crash

### Diagnosis Commands
```bash
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --previous
kubectl logs <pod-name> -n <namespace> --tail=100
kubectl get events -n <namespace> --sort-by='.lastTimestamp'
```

### Resolution Steps
1. Check previous container logs: `kubectl logs <pod> --previous`
2. If OOM: increase memory limits in deployment spec
3. If missing secret: `kubectl get secret <name> -n <namespace>`
4. Adjust liveness probe `initialDelaySeconds` to give app time to start
5. If image issue: verify image tag exists in registry

### Prevention
- Set appropriate resource requests and limits
- Use readiness probes separate from liveness probes
- Test container startup locally before deploying
- Monitor restart counts with alerting threshold

---

## OOMKilled

### Symptoms
- Pod exit code 137
- `kubectl describe pod` shows `OOMKilled` in Last State
- Node memory pressure events

### Root Causes
1. Memory limit set too low for workload
2. Memory leak in application
3. Traffic spike causing memory surge
4. JVM heap not aligned with container limits (Java apps)

### Diagnosis Commands
```bash
kubectl top pod <pod-name> -n <namespace>
kubectl top node
kubectl describe node <node-name> | grep -A5 "Allocated resources"
kubectl describe pod <pod-name> | grep -A10 "Last State"
```

### Resolution Steps
1. Increase memory limit: edit deployment `resources.limits.memory`
2. For Java: set `-Xmx` to 75% of container memory limit
3. Enable memory profiling in staging environment
4. Check for unbounded caches or connection pools

### Prevention
- Set memory requests = 50-70% of limits
- Enable VPA (Vertical Pod Autoscaler) for automatic right-sizing
- Add memory usage alerting at 80% of limit
- Regular heap dump analysis for Java services

---

## ImagePullBackOff / ErrImagePull

### Symptoms
- Pod stuck in `ImagePullBackOff` state
- Events show `Failed to pull image`

### Diagnosis Commands
```bash
kubectl describe pod <pod-name> | grep -A10 "Events"
kubectl get secret regcred -n <namespace>
crictl images | grep <image-name>
```

### Resolution Steps
1. Verify image tag exists: `docker manifest inspect <image>:<tag>`
2. Check imagePullSecret exists: `kubectl get secret <secret> -n <namespace>`
3. Re-create pull secret if credentials expired
4. For private registries, patch service account

---

## Pod Stuck in Pending

### Symptoms
- Pod status `Pending` for more than 2 minutes
- No node assignment

### Root Causes
1. Insufficient cluster resources (CPU/memory)
2. Node selector / affinity mismatch
3. PVC not bound
4. Resource quota exceeded

### Diagnosis Commands
```bash
kubectl describe pod <pod-name>
kubectl describe nodes | grep -A5 "Allocated resources"
kubectl get pvc -n <namespace>
kubectl describe resourcequota -n <namespace>
```

### Resolution
1. Scale cluster: add new nodes or increase node size
2. Review resource requests — reduce if over-provisioned
3. Fix PVC or StorageClass configuration
4. Request quota increase from cluster admin

---

## Node NotReady

### Symptoms
- `kubectl get nodes` shows `NotReady`
- Pods on node being evicted

### Diagnosis Commands
```bash
kubectl describe node <node-name>
kubectl get events --field-selector involvedObject.name=<node-name>
ssh <node-ip> 'journalctl -u kubelet --since "10 minutes ago"'
```

### Resolution Steps
1. SSH to node, check kubelet: `systemctl status kubelet`
2. Restart kubelet: `systemctl restart kubelet`
3. Check disk pressure: `df -h`
4. Check memory pressure: `free -m`
5. If unrecoverable: drain and replace node

---

## HorizontalPodAutoscaler Not Scaling

### Symptoms
- HPA shows `<unknown>/80%` for metrics
- Pods not scaling under load

### Diagnosis Commands
```bash
kubectl describe hpa <hpa-name> -n <namespace>
kubectl top pods -n <namespace>
kubectl get apiservice v1beta1.metrics.k8s.io
```

### Resolution
1. Ensure metrics-server is running: `kubectl get pods -n kube-system | grep metrics-server`
2. Verify resource requests are set (HPA requires them for CPU percentages)
3. Check RBAC permissions for HPA to read metrics
4. Verify min/max replicas and current replica count
