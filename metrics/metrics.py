from prometheus_client import Counter, Histogram, start_http_server

# Counters
MESSAGES_RECEIVED = Counter(
    "messages_received_total",
    "Total number of HL7 messages received via MLLP"
)

BLOOD_TESTS_RECEIVED = Counter(
    "blood_tests_received_total",
    "Total number of creatinine blood test results received"
)

AKI_PREDICTIONS_TOTAL = Counter(
    "aki_predictions_total",
    "Total number of AKI predictions made by the model"
)

AKI_POSITIVE_PREDICTIONS = Counter(
    "aki_positive_predictions_total",
    "Total number of positive AKI predictions"
)

PAGER_REQUESTS = Counter(
    "pager_requests_total",
    "Total number of pager HTTP requests sent"
)

PAGER_ERRORS = Counter(
    "pager_http_errors_total",
    "Total number of pager HTTP errors (non-200, timeout, connection)"
)

MLLP_RECONNECTIONS = Counter(
    "mllp_reconnections_total",
    "Total number of MLLP reconnection attempts"
)

# Histograms
BLOOD_TEST_VALUES = Histogram(
    "blood_test_value",
    "Distribution of creatinine blood test result values",
    buckets=[20, 40, 60, 80, 100, 120, 150, 200, 300, 500, 1000]
)

MESSAGE_PROCESSING_LATENCY = Histogram(
    "message_processing_latency_seconds",
    "Time taken to process each HL7 message end-to-end",
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)


def start_metrics_server(port=8000):
    """Start the Prometheus metrics HTTP server on a daemon thread."""
    start_http_server(port)
