import numpy as np
import pandas as pd

from app.recommend.service import recommend
from app.regime.baselines import fit_kmeans, fit_wasserstein_kmeans
from app.regime.hmm import fit_hmm
from app.regime.validate import validate_regimes


def _features() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    returns = np.r_[
        rng.normal(-0.01, 0.005, 80), rng.normal(0, 0.003, 80), rng.normal(0.01, 0.005, 80)
    ]
    index = pd.date_range("2020-01-01", periods=len(returns), tz="Asia/Kolkata", name="date")
    return pd.DataFrame(
        {
            "returns_pct": returns,
            "log_return": np.log1p(returns),
            "vol_20": pd.Series(returns).rolling(20).std().to_numpy(),
        },
        index=index,
    )


def test_regime_methods_and_validation() -> None:
    features = _features()
    hmm = fit_hmm(features, symbol="TEST.NS")
    kmeans = fit_kmeans(features)
    wkmeans = fit_wasserstein_kmeans(features)
    assert hmm.n_states == 3
    assert hmm.state_names == {0: "bear", 1: "sideways", 2: "bull"}
    assert len(kmeans) == len(wkmeans) == len(features.dropna())
    validation = validate_regimes(features, kmeans, wkmeans)
    assert validation.davies_bouldin is not None
    assert validation.transition_matrix is not None


def test_recommendation_contains_caveat() -> None:
    result = fit_hmm(_features(), symbol="TEST.NS")
    recommendation = recommend("TEST.NS", result)
    assert recommendation.suggested_strategy in recommendation.suitability
    assert "not investment advice" in recommendation.caveat.lower()
