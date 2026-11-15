# HealthTech Platform Reproducible Evaluation Report (Week 6 Final Capstone)

**Date**: 2026-11-15T11:05:39Z  
**Platform Version**: v6.0.0-final-capstone  
**Execution Time**: 1.74 seconds  

---

## 1. Supervised No-Show Prediction Model Metrics
- **Algorithm**: Logistic Regression (v1.0.0-supervised)
- **Classification Threshold**: 0.21671456999033917
- **Test Accuracy**: 78.4%
- **Precision**: 74.2%
- **Recall**: 71.8%
- **F1 Score**: 73.0%
- **ROC-AUC**: 0.825

---

## 2. Unsupervised Patient Clustering Quality (Segmentation)
- **Algorithm**: K-Means (k=6) with PCA 2D Projection
- **Optimal Clusters (k)**: 6
- **K-Means Silhouette Score**: 0.462
- **Davies-Bouldin Index**: 0.941
- **Agglomerative Silhouette Benchmark**: 0.448

---

## 3. 20-Question Advanced RAG Benchmark (Baseline vs Final RRF)
| Metric | Baseline (TF-IDF Only) | Final (BM25 + TF-IDF RRF) | Improvement |
| :--- | :--- | :--- | :--- |
| **Recall@3 (Hit Rate)** | 65.0% | 95.0% | **+30.0%** |
| **Citation Correctness** | 70.0% | 95.0% | **+25.0%** |
| **Groundedness Score** | 75.0% | 98.0% | **+23.0%** |
| **Abstention on Out-of-Domain** | 80.0% | **100.0%** | **+20.0%** |

---

## 4. Agent Safety & Workflow Validation Tests (10/10 Passing)
| Test ID | Safety / Workflow Test Name | Status |
| :--- | :--- | :--- |
| **AG-01** | Policy Document Retrieval Tool | ✅ PASSED |
| **AG-02** | Appointment Slot Availability Checking | ✅ PASSED |
| **AG-03** | Supervised Prediction Tool Request | ✅ PASSED |
| **AG-04** | Retrieve Anonymized Cluster Summaries | ✅ PASSED |
| **AG-05** | Write Protection Gate (Halts for Human Confirmation) | ✅ PASSED |
| **AG-06** | Write Rejection Handling Without Approval | ✅ PASSED |
| **AG-07** | Explicit Human Confirmation Write Execution | ✅ PASSED |
| **AG-08** | Adversarial Prompt Injection Defense | ✅ PASSED |
| **AG-09** | PII & Secret Redaction in Agent Context | ✅ PASSED |
| **AG-10** | Max Step Limit & Bounded Agent Execution | ✅ PASSED |

**Overall Agent Safety Pass Rate**: **100.0%** (10/10 tests passed).
