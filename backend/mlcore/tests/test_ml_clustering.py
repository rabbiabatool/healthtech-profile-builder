"""Tests for Week 4 Unsupervised Learning (Clustering & PCA)."""
import json
from pathlib import Path

import numpy as np
import pytest

from mlcore import clustering, config, schema
from mlcore.data_generation import generate_appointments


@pytest.fixture(scope="module")
def sample_appointments():
    return generate_appointments(n_patients=500, n_appointments=1500, seed=config.SEED)


@pytest.fixture(scope="module")
def engagement_data(sample_appointments):
    return clustering.extract_engagement_features(sample_appointments)


def test_engagement_features_excludes_forbidden_and_target(sample_appointments):
    df_feat = clustering.extract_engagement_features(sample_appointments)
    for col in schema.FORBIDDEN_COLUMNS:
        assert col not in df_feat.columns
    assert schema.TARGET_COLUMN not in df_feat.columns
    assert "attendance_ratio" in df_feat.columns
    assert (df_feat["attendance_ratio"] >= 0.0).all()
    assert (df_feat["attendance_ratio"] <= 1.0).all()


def test_preprocessing_scales_and_imputes(engagement_data):
    scaled, imputer, scaler = clustering.build_preprocessed_features(engagement_data)
    assert not np.isnan(scaled).any()
    assert scaled.shape == engagement_data.shape
    # Check approximately standard normal
    assert np.allclose(scaled.mean(axis=0), 0.0, atol=1e-2)
    assert np.allclose(scaled.std(axis=0), 1.0, atol=1e-2)


def test_cluster_range_evaluation(engagement_data):
    scaled, _, _ = clustering.build_preprocessed_features(engagement_data)
    eval_res = clustering.evaluate_cluster_range(scaled, k_range=range(2, 5), sample_size=500, seed=config.SEED)
    
    assert "k_evaluations" in eval_res
    assert len(eval_res["k_evaluations"]) == 3
    for entry in eval_res["k_evaluations"]:
        assert entry["k"] in [2, 3, 4]
        assert entry["kmeans_inertia"] > 0
        assert -1.0 <= entry["kmeans_silhouette"] <= 1.0
        assert -1.0 <= entry["agglomerative_silhouette"] <= 1.0
        assert entry["kmeans_davies_bouldin"] > 0


def test_pca_2d_projection_and_variance(engagement_data):
    scaled, _, _ = clustering.build_preprocessed_features(engagement_data)
    pca_coords, pca_model, pca_meta = clustering.fit_pca_projection(scaled, n_components=2, seed=config.SEED)

    assert pca_coords.shape == (len(engagement_data), 2)
    assert len(pca_meta["explained_variance_ratio"]) == 2
    assert 0.0 < pca_meta["total_explained_variance"] <= 1.0
    assert "PC1" in pca_meta["component_loadings"]
    assert "PC2" in pca_meta["component_loadings"]


def test_methods_comparison():
    km_labels = np.array([0, 0, 1, 1, 2, 2])
    agg_labels = np.array([0, 0, 1, 1, 2, 2])
    comp = clustering.compare_clustering_methods(km_labels, agg_labels)
    assert comp["adjusted_rand_index"] == 1.0
    assert comp["normalized_mutual_info"] == 1.0
    assert "contingency_matrix" in comp


def test_cluster_profiles_and_disclaimer(engagement_data):
    scaled, _, _ = clustering.build_preprocessed_features(engagement_data)
    kmeans = clustering.KMeans(n_clusters=3, random_state=config.SEED, n_init=10)
    labels = kmeans.fit_predict(scaled)

    profiles = clustering.profile_clusters(engagement_data, labels, n_clusters=3)
    assert len(profiles) == 3
    for p in profiles:
        assert p["name"]
        assert p["description"]
        assert p["size"] > 0
        assert p["percentage"] > 0
        assert "lead_time_days" in p["feature_means"]
        assert "attendance_ratio" in p["feature_means"]
        assert p["operational_recommendation"]

    assert "EXPLORATORY OPERATIONAL ARCHETYPES" in clustering.NON_CLINICAL_DISCLAIMER
