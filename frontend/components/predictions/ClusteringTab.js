"use client";

import { useEffect, useState } from "react";
import { fetchClusteringAnalysis } from "../../lib/mlClient";
import styles from "./predictions.module.css";

const fmt = (val, digits = 4) =>
  val !== undefined && val !== null && !isNaN(val) ? Number(val).toFixed(digits) : "—";

const fmtPct = (val, digits = 1) =>
  val !== undefined && val !== null && !isNaN(val) ? `${(Number(val) * 100).toFixed(digits)}%` : "—";

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
    optimal_k,
    k_evaluations,
    methods_comparison,
    pca_summary,
    cluster_profiles,
    disclaimer,
    features_used,
    dataset_size,
  } = data;

  const optimalEval = k_evaluations?.find((e) => e.k === optimal_k) ?? k_evaluations?.[0] ?? {};

  return (
    <div>
      <aside className={styles.banner} aria-label="Educational disclaimer">
        <strong>Exploratory Archetype Notice:</strong> {disclaimer ?? "Exploratory operational clustering based on non-sensitive engagement data."}
      </aside>

      <section className={styles.card}>
        <h2>Clustering Quality & Algorithm Comparison</h2>
        <p>
          Evaluated {dataset_size?.toLocaleString() ?? "20,000"} patient engagement records across {features_used?.length ?? 6} non-sensitive features using <strong>K-Means</strong> and <strong>Agglomerative Hierarchical Clustering</strong>.
        </p>
        <div className={styles.facts}>
          <div>
            <dt>Optimal Clusters (k)</dt>
            <dd><strong>k = {optimal_k ?? 6}</strong></dd>
          </div>
          <div>
            <dt>K-Means Silhouette Score</dt>
            <dd><strong>{fmt(optimalEval.kmeans_silhouette ?? optimalEval.silhouette)}</strong></dd>
          </div>
          <div>
            <dt>Davies-Bouldin Index</dt>
            <dd>{fmt(optimalEval.kmeans_davies_bouldin ?? optimalEval.davies_bouldin)} (lower is better)</dd>
          </div>
          <div>
            <dt>Agglomerative Silhouette</dt>
            <dd>{fmt(optimalEval.agglomerative_silhouette ?? methods_comparison?.agglomerative_silhouette)}</dd>
          </div>
          <div>
            <dt>Adjusted Rand Index (ARI)</dt>
            <dd>{fmt(methods_comparison?.adjusted_rand_index)}</dd>
          </div>
          <div>
            <dt>Normalized Mutual Info (NMI)</dt>
            <dd>{fmt(methods_comparison?.normalized_mutual_info)}</dd>
          </div>
        </div>
        {methods_comparison?.method_comparison_summary && (
          <p className={styles.hint} style={{ marginTop: "0.75rem" }}>
            {methods_comparison.method_comparison_summary}
          </p>
        )}
      </section>

      {pca_summary && (
        <section className={styles.card}>
          <h2>2D PCA Dimensionality Reduction</h2>
          <p>
            Projected engagement features onto 2 orthogonal principal components, capturing{" "}
            <strong>{fmtPct(pca_summary.total_explained_variance)}</strong> of total variance:
          </p>
          <div className={styles.facts}>
            <div>
              <dt>PC1 Explained Variance</dt>
              <dd><strong>{fmtPct(pca_summary.explained_variance_ratio?.[0])}</strong></dd>
              <dd className={styles.hint}>{pca_summary.pc_interpretations?.PC1 ?? "History volume and consistency"}</dd>
            </div>
            <div>
              <dt>PC2 Explained Variance</dt>
              <dd><strong>{fmtPct(pca_summary.explained_variance_ratio?.[1])}</strong></dd>
              <dd className={styles.hint}>{pca_summary.pc_interpretations?.PC2 ?? "Lead time days and travel distance"}</dd>
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
                  <h3 className={styles.clusterTitle}>{profile.name ?? `Cluster ${profile.cluster_id}`}</h3>
                  <span className={styles.clusterSize}>
                    {profile.size?.toLocaleString() ?? "—"} patients ({fmt(profile.percentage, 1)}%)
                  </span>
                </div>
                <p className={styles.hint}>{profile.description}</p>
                {profile.traits && profile.traits.length > 0 && (
                  <>
                    <strong>Key Characteristic Traits:</strong>
                    <ul className={styles.traitList}>
                      {profile.traits.map((trait, idx) => (
                        <li key={idx}>{trait}</li>
                      ))}
                    </ul>
                  </>
                )}
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
