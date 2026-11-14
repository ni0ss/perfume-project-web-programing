# Kubernetes autoscaling lab

These manifests demonstrate Kubernetes service load balancing and automatic horizontal scaling. They do not create a cluster or provision managed services.

## Prerequisites

- A Kubernetes cluster with Metrics Server installed and working.
- The `perfume-project:local` image built and available to every node.
- In-cluster Services named `postgres-primary`, `postgres-replica`, `cache`, and `ollama`.
- PostgreSQL primary and replica plus shared Redis; the included Kubernetes Job applies migrations and seeds the demo catalog.
- A real, unique Django secret and the database password used by the primary.

The host-only Compose lab is a separate demonstration; its services do not automatically become Kubernetes Services.

## Apply

Build the image with `docker build -t perfume-project:local .`, then make it available to your cluster using the cluster-specific image-loading command. For example, a kind cluster can use `kind load docker-image perfume-project:local`.

Create the runtime Secret without adding the values to Git:

```bash
kubectl create secret generic perfume-secrets \
  --from-literal=DJANGO_SECRET_KEY="$(openssl rand -hex 48)" \
  --from-literal=DJANGO_DATABASE_PASSWORD='the-primary-database-password'
```

Review and adjust the example hostnames in `perfume-runtime.example.yaml` for your cluster, then apply the ConfigMap and run migrations once:

```bash
kubectl apply -f deploy/kubernetes/perfume-runtime.example.yaml
kubectl apply -f deploy/kubernetes/perfume-migrate-job.yaml
kubectl wait --for=condition=complete job/perfume-migrate --timeout=5m
kubectl apply -f deploy/kubernetes/perfume-web.yaml
kubectl get deployment,service,hpa,pods
```

The Service distributes requests over ready web pods. The HPA targets 70% average CPU use, starts with two pods, and can scale to six. Inspect scaling and metrics with:

```bash
kubectl get hpa perfume-web --watch
kubectl top pods -l app.kubernetes.io/name=perfume-web
```

To repeat a clean migration job after a code/schema change, delete the completed Job before applying it again:

```bash
kubectl delete job perfume-migrate
kubectl apply -f deploy/kubernetes/perfume-migrate-job.yaml
kubectl wait --for=condition=complete job/perfume-migrate --timeout=5m
```

Do not expose this template as-is. It is an educational workload manifest; production still needs trusted TLS at an Ingress, hardened secret management, network policies, shared media storage, resource tuning, and backups.
