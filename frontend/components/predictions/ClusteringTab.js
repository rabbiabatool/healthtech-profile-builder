"use client";

import { useEffect, useState } from "react";
import { fetchClusteringAnalysis } from "../../lib/mlClient";
import styles from "./predictions.module.css";

export default function ClusteringTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchClusteringAnalysis()
      .then(({ status, data: resData }) => {
        if (status === 200) {
          setData(resData);
        } else {
          setError(`Failed to load clustering analysis (status ${status}).`);
        }
      })
      .catch((err) => setError(err.message || "Network error"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className={styles.card}><p>Loading unsupervised clustering analysis and PCA projection...</p></div>;
  }

  if (error || !data) {
    return (
      <div className={styles.card}>
        <p className={styles.error}>{error || "Unable to display clustering analysis."}</p>
      </div>
    );
  }

  const {
    kmeans_optimal_k,
    silhouette_score,
    davies_bouldin_index,
    method_comparison,
    pca_2d_summary,
    cluster_profiles,
    disclaimer,
  } = data;

  return (
    <div>
      <aside className={styles.banner} aria-label="Educational disclaimer">
        <strong>Exploratory Archetype Notice:</strong> {disclaimer}
      </aside>

      <section className={styles.card}>
        <h2>Clustering Quality & Algorithm Comparison</h2>
        <p>
          Evaluated non-sensitive patient engagement metrics using <strong>K-Means</strong> and <strong>Agglomerative Hierarchical Clustering</strong>.
        </p>
        <div className={styles.facts}>
          <div>
            <dt>Optimal Clusters (k)</dt>
            <dd><strong>{kmeans_optimal_k}</strong></dd>
          </div>
          <div>
            <dt>K-Means Silhouette Score</dt>
            <dd><strong>{silhouette_score?.toFixed(4)}</strong></dd>
          </div>
          <div>
            <dt>Davies-Bouldin Index</dt>
            <dd>{davies_bouldin_index?.toFixed(4)} (lower is better)</dd>
          </div>
          <div>
            <dt>Agglomerative Silhouette</dt>
            <dd>{method_comparison?.agglomerative_silhouette?.toFixed(4)}</dd>
          </div>
          <div>
            <dt>Adjusted Rand Index (ARI)</dt>
            <dd>{method_comparison?.adjusted_rand_index?.toFixed(4)}</dd>
          </div>
          <div>
            <dt>Normalized Mutual Info (NMI)</dt>
            <dd>{method_comparison?.normalized_mutual_info?.toFixed(4)}</dd>
          </div>
        </div>
      </section>

      {pca_2d_summary && (
        <section className={styles.card}>
          <h2>2D PCA Dimensionality Reduction</h2>
          <p>
            Projected 6 standardized engagement features onto 2 orthogonal principal components, capturing{" "}
            <strong>{pca_2d_summary.total_explained_variance_pct}%</strong> of total variance:
          </p>
          <div className={styles.facts}>
            <div>
              <dt>PC1 Explained Variance</dt>
              <dd><strong>{pca_2d_summary.explained_variance_ratio_pc1_pct}%</strong></dd>
              <dd className={styles.hint}>Dominant driver: {pca_2d_summary.top_features_pc1?.join(", ")}</dd>
            </div>
            <div>
              <dt>PC2 Explained Variance</dt>
              <dd><strong>{pca_2d_summary.explained_variance_ratio_pc2_pct}%</strong></dd>
              <dd className={styles.hint}>Dominant driver: {pca_2d_summary.top_features_pc2?.join(", ")}</dd>
            </div>
          </div>
        </section>
      )}

      <section className={styles.card}>
        <h2>Discovered Exploratory Personas ({cluster_profiles?.length || 0})</h2>
        <p>
          Clusters represent neutral operational patterns to assist clinic staffing and communication, never individual health statuses:
        </p>
        <div className={styles.clusterGrid}>
          {cluster_profiles?.map((profile) => (
            <article key={profile.cluster_id} className={styles.clusterCard}>
              <div>
                <div className={styles.clusterHeader}>
                  <h3 className={styles.clusterTitle}>{profile.persona_name}</h3>
                  <span className={styles.clusterSize}>
                    {profile.patient_count?.toLocaleString()} patients ({profile.percentage?.toFixed(1)}%)
                  </span>
                </div>
                <p className={styles.hint}>{profile.description}</p>
                <strong>Key Characteristic Traits:</strong>
                <ul className={styles.traitList}>
                  {profile.characteristic_traits?.map((trait, idx) => (
                    <li key={idx}>{trait}</li>
                  ))}
                </ul>
              </div>
              <div className={styles.recBox}>
                <strong>Operational Strategy:</strong>
                <p style={{ margin: "0.25rem 0 0 0" }}>{profile.operational_recommendation}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

