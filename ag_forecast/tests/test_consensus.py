import pytest
from ag_forecast.src.consensus.base import MeanConsensus, MedianConsensus, WeightedAverageConsensus

def test_mean_consensus():
    predictions = [{"yes": 0.2}, {"yes": 0.4}, {"yes": 0.9}]
    consensus = MeanConsensus()
    result = consensus.aggregate(predictions)
    assert result["yes"] == 0.5

def test_median_consensus():
    predictions = [{"yes": 0.2}, {"yes": 0.4}, {"yes": 0.9}]
    consensus = MedianConsensus()
    result = consensus.aggregate(predictions)
    assert result["yes"] == 0.4

def test_weighted_consensus():
    predictions = [{"yes": 0.2}, {"yes": 0.8}]
    weights = [0.9, 0.1]
    consensus = WeightedAverageConsensus(weights)
    result = consensus.aggregate(predictions)
    # 0.2*0.9 + 0.8*0.1 = 0.18 + 0.08 = 0.26
    assert abs(result["yes"] - 0.26) < 1e-6
