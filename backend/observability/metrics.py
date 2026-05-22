"""
Prometheus metrics registry for the lead generation pipeline.

All metric objects are module-level singletons — import them where needed.
"""
from prometheus_client import Counter, Histogram

# Lead pipeline throughput
leads_processed = Counter(
    "leads_processed_total",
    "Total leads processed by the pipeline",
    ["status"],   # qualified | disqualified | error
)

# Per-stage latency (research, qualification, sales, total)
stage_latency = Histogram(
    "lead_pipeline_stage_seconds",
    "Latency per pipeline stage",
    ["stage"],
    buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
)

# End-to-end pipeline duration
pipeline_duration = Histogram(
    "lead_pipeline_duration_seconds",
    "End-to-end pipeline duration",
    buckets=[5, 10, 20, 30, 45, 60, 90, 120],
)

# LLM call counter
llm_calls = Counter(
    "llm_calls_total",
    "Total LLM inference calls",
    ["agent"],   # research | qualification | sales
)

# Qualification score distribution
qualification_score_dist = Histogram(
    "lead_qualification_score",
    "Distribution of lead qualification scores",
    buckets=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

# RAG chunks retrieved per generation
rag_chunks_retrieved = Histogram(
    "rag_chunks_retrieved",
    "Number of RAG chunks retrieved per outreach generation",
    buckets=[0, 1, 2, 3, 4, 5],
)

# Hallucination self-critique results
hallucination_checks_total = Counter(
    "hallucination_checks_total",
    "Results of SelfCritiqueTool hallucination checks",
    ["is_grounded"],   # "true" | "false"
)
