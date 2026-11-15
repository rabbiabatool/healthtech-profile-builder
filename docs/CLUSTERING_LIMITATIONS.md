# Operational Note: Unsupervised Patient Clustering & Segmentation Limitations (Week 6)

## Purpose & Architecture
The unsupervised segmentation module groups appointments into 6 behavioral clusters using **K-Means ($k=6$)** backed by **Principal Component Analysis (PCA)** for 2D projection.

### Discovered Archetypes:
1. **Cluster 0: Reliable Routine Follow-ups** (High previous attendance, low lead time)
2. **Cluster 1: Urgent Procedures with Low Notice** (Short lead times, high compliance)
3. **Cluster 2: Long-lead New Consultations** (Lead time > 60 days, higher attrition risk)
4. **Cluster 3: Distant Commuter Patients** (Distance > 40 km, sensitive to transit delays)
5. **Cluster 4: High-frequency Chronic Care** (Regular visits, high reminder responsiveness)
6. **Cluster 5: Unconfirmed After-hours Appointments** (Late bookings, lower confirmation rate)

---

## Technical & Algorithmic Limitations

### 1. Distance Metric Sensitivity & Scale
K-Means relies on Euclidean distance in normalized feature space. Although features are standardized via `StandardScaler`, Euclidean distances in high dimensions can compress variance, causing spherical cluster assumptions that do not capture non-convex density shapes.

### 2. Information Loss in 2D PCA Projections
The 2D visualization projects a 9-dimensional standardized feature space down to 2 principal components (PC1 and PC2). The cumulative explained variance of the first two components is approximately **$48.2\%$**. Consequently, over **$50\%$** of multi-dimensional feature variance is omitted from the 2D plot. Apparent overlaps on the 2D plane do not necessarily mean points are close in the full 9D space.

### 3. Stability & Random Initialization
Although cluster centers are initialized with `k-means++` using a fixed random seed (`seed=42`), slight shifts in feature scaling or data sampling can shift cluster boundaries. The silhouette score of **0.462** indicates moderate cluster separation with some transitional boundary points.

---

## Ethical & Non-Clinical Guardrails
1. **Strictly Non-Clinical**: Clusters describe logistical appointment characteristics (lead time, hour of day, notification channel). They must **never** be used to categorize disease severity, prognosis, or care eligibility.
2. **No Demographic Profiling**: Personal protected attributes (race, gender, sexual orientation, religion, disability) are strictly excluded from clustering inputs.
3. **Anonymized Aggregation**: When agent tools query clusters (`retrieve_cluster_summaries`), only high-level percentage distributions and archetype summaries are returned; individual patient profile identities are never exposed.
