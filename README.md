# AKI Detection Service

A production-grade clinical decision support system for real-time detection of Acute Kidney Injury (AKI) in hospital patients. The service ingests a live stream of HL7 messages from hospital systems, applies a trained machine learning model to creatinine blood test results, and pages the clinical response team when AKI is detected.

Deployed on Kubernetes (Azure AKS) and run live against a real-time hospital simulator for a two-week scoring period.

---

## What's in this repository

```
cw3/
├── main.py                        # Entry point: initialises model, state, metrics, MLLP loop
├── Dockerfile                     # Container image definition (python:3.12-slim)
├── coursework4.yaml               # Kubernetes manifest (Deployment + PVC)
├── requirements.txt               # Python dependencies
│
├── MLLP/
│   └── mllp_client.py             # TCP socket client with MLLP framing + exponential backoff reconnection
│
├── decoder/
│   ├── decoder.py                 # HL7v2 message parser (ADT^A01, ADT^A03, ORU^R01)
│   └── examples/                  # Sample HL7 message files for reference
│
├── processor/
│   ├── processor.py               # Core event processor: routes messages, runs ML inference
│   ├── creatinine_history.py      # Per-patient creatinine time-series management
│   ├── creatinine_features.py     # Feature engineering (12 features from demographics + history)
│   ├── patient_info.py            # Patient demographics and admission state
│   └── pager_decision.py          # Decision dataclass (mrn, timestamp, reason)
│
├── pager/
│   └── pager.py                   # HTTP POST to pager endpoint with 3-attempt retry + backoff
│
├── metrics/
│   └── metrics.py                 # Prometheus counters and histograms, HTTP server on port 8000
│
├── state/
│   └── state_manager.py           # Pickle serialisation/deserialisation to /state PVC
│
└── saved_model/
    ├── model.pkl                  # Serialised RandomForestClassifier (~3.7 MB)
    ├── threshold.pkl              # Optimal F3-score decision threshold
    └── training.py                # Offline training script (run separately — see below)
```

---

## What lives elsewhere

| Component | Location | Notes |
|---|---|---|
| **ML training data** | `/data/training.csv`, `/data/test.csv` | Injected at runtime via init container; not tracked in this repo |
| **Patient history** | `/data/history.csv` | 408k rows of baseline creatinine readings; injected by init container from `imperialswemlsspring2026.azurecr.io/coursework4-history` |
| **Hospital simulator** | `spire-simulator.coursework4:8440` (MLLP) / `:8441` (pager) | External course-provided service; replays HL7 messages in real time |
| **Prometheus Alertmanager** | `prom-ui.coursework6:9093` | Course-provided instance; configured to email the team on absence alerts |
| **Azure Container Registry** | `imperialswemlsspring2026.azurecr.io/coursework4-spire` | Private registry; requires `az acr login` |
| **Kubernetes cluster** | Azure AKS `imperial-swemls-spring-2026` | Namespace: `spire` |

---

## Architecture

```
Hospital MLLP Server (:8440)
          │  TCP socket, HL7 messages framed in MLLP
          ▼
    mllp_client.py
          │  raw message bytes
          ▼
     decoder.py
          │  structured Python dict (admit / discharge / lab result)
          ▼
     processor.py
          │
          ├─ ADT^A01 (admit)     → PatientInfo.admit()
          ├─ ADT^A03 (discharge) → PatientInfo.discharge()
          └─ ORU^R01 (lab)       → CreatinineHistory.append()
                                   → CreatinineFeatures.build()
                                   → model.predict_proba()
                                   → threshold check + duplicate check
                                          │
                                          ▼ if AKI detected
                                      pager.py  ──→  POST /page (:8441)

    All activity ──→ metrics.py ──→ Prometheus scrape (:8000)
    On SIGTERM   ──→ state_manager.py ──→ /state PVC (pickle)
```

---

## Machine Learning Model

The model is trained offline using `saved_model/training.py` and the resulting artefacts (`model.pkl`, `threshold.pkl`) are baked into the Docker image.

**Algorithm:** `RandomForestClassifier` (300 estimators, stratified 5-fold cross-validation)

**Features (12 per patient):**

| Category | Features |
|---|---|
| Demographics | `age`, `sex` (binary: male=1, female=0) |
| Creatinine statistics | `max`, `min`, `mean`, `std`, `range`, `first`, `last` |
| Trend | `max_creatinine_increase` (max jump between consecutive readings) |
| Temporal | `num_measurements`, `measurement_span_days` |

**Evaluation metric:** F3 score — weights recall 3× more than precision, reflecting the clinical priority of catching AKI over minimising false alarms.

**Threshold:** Post-training sweep over validation set to find the probability cutoff maximising F3 score. Stored separately from the model so it can be updated without retraining.

To retrain:
```bash
python saved_model/training.py
```
This reads `data/training.csv`, trains the classifier, tunes the threshold, and overwrites `model.pkl` and `threshold.pkl`.

---

## Running Locally

### Prerequisites
- Docker
- The simulator running locally (or set environment variables to point at a remote instance)

### Build and run
```bash
docker build -t aki-detection .

docker run \
  -e MLLP_ADDRESS=localhost:8440 \
  -e PAGER_ADDRESS=localhost:8441 \
  -v $(pwd)/data:/data \
  -v $(pwd)/state:/state \
  -p 8000:8000 \
  aki-detection
```

Prometheus metrics are available at `http://localhost:8000/metrics`.

### Environment variables

| Variable | Description | Example |
|---|---|---|
| `MLLP_ADDRESS` | Host:port of the MLLP server | `localhost:8440` |
| `PAGER_ADDRESS` | Host:port of the pager HTTP service | `localhost:8441` |
| `PYTHONUNBUFFERED` | Set to `1` for real-time log output (set in Dockerfile) | `1` |

---

## Kubernetes Deployment

### Prerequisites
```bash
az login
az account set --subscription 4693832c-ac40-4623-80b9-79a0345fcfce
az acr login --name imperialswemlsspring2026
az aks get-credentials --resource-group imperial-swemls-spring-2026 \
  --name imperial-swemls-spring-2026 --overwrite-existing
kubelogin convert-kubeconfig -l azurecli
```

### Build and push image
```bash
# On Apple Silicon (M1/M2), cross-compile for the amd64 cluster nodes
docker build --platform=linux/amd64,linux/arm64 \
  -t imperialswemlsspring2026.azurecr.io/coursework4-spire .

docker push imperialswemlsspring2026.azurecr.io/coursework4-spire
```

### Deploy
```bash
kubectl apply -f coursework4.yaml

# Verify
kubectl --namespace=spire get pods
kubectl --namespace=spire get deployments

# Stream logs
kubectl logs --namespace=spire -l app=aki-detection -f
```

### Persistent state
The `/state` directory is backed by a 1Gi `ReadWriteOnce` PersistentVolumeClaim (`aki-detection-state`). State survives pod restarts automatically.

> **Important:** When switching simulators (e.g. from coursework4 to coursework6), the `/state` directory must be cleared to avoid stale patient history from a previous simulator session contaminating the new one. Either delete and recreate the PVC, or exec into the pod and remove the `.pkl` files before restarting.

### Switching to the coursework6 simulator
Update `coursework4.yaml` with the new simulator addresses and history image:
```yaml
env:
  - name: MLLP_ADDRESS
    value: spire-simulator.coursework6:8440
  - name: PAGER_ADDRESS
    value: spire-simulator.coursework6:8441

initContainers:
  - name: copy-hospital-history
    image: imperialswemlsspring2025.azurecr.io/coursework6-history
```
Then re-apply: `kubectl apply -f coursework4.yaml`

---

## Observability

The service exports the following metrics on port 8000 in Prometheus text format.

### Counters
| Metric | Description |
|---|---|
| `messages_received_total` | All HL7 messages received via MLLP |
| `blood_tests_received_total` | Creatinine results processed |
| `aki_predictions_total` | Total ML predictions run |
| `aki_positive_predictions_total` | Positive AKI detections |
| `pager_requests_total` | HTTP POST attempts to pager |
| `pager_http_errors_total` | Pager connection/timeout/non-200 errors |
| `pager_alerts_dropped_total` | Alerts lost after 3 failed retry attempts |
| `mllp_reconnections_total` | MLLP reconnection attempts |

### Histograms
| Metric | Description | Buckets |
|---|---|---|
| `blood_test_value` | Creatinine level distribution (μmol/L) | 20, 40, 60, 80, 100, 120, 150, 200, 300, 500, 1000 |
| `message_processing_latency_seconds` | End-to-end processing time per message | 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0 |

### Alertmanager integration
To connect to the course-provided Prometheus Alertmanager, add to your `prometheus.yml`:
```yaml
alerting:
  alertmanagers:
    - scheme: http
      static_configs:
        - targets:
            - "prom-ui.coursework6:9093"
```
Alerts must be tagged `group=spire` to be routed correctly. The Alertmanager is pre-configured to send email if the `aki-detection` job goes absent for more than 10 minutes.

To port-forward the metrics endpoint from a running pod:
```bash
kubectl -n spire port-forward <pod-name> 8000:8000
# then visit http://localhost:8000/metrics
```

---

## Failure Handling

| Failure | Behaviour |
|---|---|
| MLLP connection dropped | Exponential backoff reconnect (1s → 30s max), retries indefinitely |
| MLLP connection refused on startup | Same backoff; waits for simulator to become available |
| Pager HTTP error / timeout | Retry up to 3 times with backoff (0.5s → 1s max); drops alert and increments `pager_alerts_dropped_total` after 3 failures |
| SIGTERM received | Saves all in-memory state to `/state` PVC before exiting (graceful Kubernetes shutdown) |
| Pod restart | Warm-starts from `/state` PVC; no patient history is lost |
| First deployment (no PVC state) | Cold-starts by loading baseline creatinine history from `/data/history.csv` |

---

## Scoring (live period)

During the two-week live scoring period, the system is assessed as follows:

| Event | Points |
|---|---|
| Page sent for a true AKI event, within latency window | +10 |
| Page sent for a non-AKI event (false positive) | −3 |
| AKI event missed (no page sent) | −10 |

**Recovering missed alerts during an incident:** The pager API accepts a historical timestamp in the request body (`{mrn},{timestamp}`), allowing pages to be sent retroactively for blood test results already received. This can be used to recover points for the window covered by a declared incident, while the latency SLA is suspended.

---

## Dependencies

Key packages (see `requirements.txt` for pinned versions):

| Package | Purpose |
|---|---|
| `scikit-learn` | RandomForestClassifier, model serialisation |
| `pandas` / `numpy` | Feature engineering, data manipulation |
| `hl7` | HL7v2 message parsing |
| `requests` | HTTP client for pager integration |
| `prometheus_client` | Metrics counters, histograms, HTTP server |
| `joblib` | Model pickle serialisation |
| `python-dateutil` | Clinical timestamp parsing |
