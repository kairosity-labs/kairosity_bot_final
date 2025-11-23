from abc import ABC, abstractmethod
from typing import List, Dict, Union
import statistics

class BaseConsensus(ABC):
    @abstractmethod
    def aggregate(self, predictions: List[Dict[str, float]]) -> Dict[str, float]:
        pass

class MeanConsensus(BaseConsensus):
    def aggregate(self, predictions: List[Dict[str, float]]) -> Dict[str, float]:
        if not predictions:
            return {}
        
        keys = predictions[0].keys()
        result = {}
        for k in keys:
            values = [p.get(k, 0.0) for p in predictions]
            result[k] = statistics.mean(values)
        return result

class MedianConsensus(BaseConsensus):
    def aggregate(self, predictions: List[Dict[str, float]]) -> Dict[str, float]:
        if not predictions:
            return {}
        
        keys = predictions[0].keys()
        result = {}
        for k in keys:
            values = [p.get(k, 0.0) for p in predictions]
            result[k] = statistics.median(values)
        return result

class WeightedAverageConsensus(BaseConsensus):
    def __init__(self, weights: List[float] = None):
        self.weights = weights

    def aggregate(self, predictions: List[Dict[str, float]]) -> Dict[str, float]:
        if not predictions:
            return {}
        
        n = len(predictions)
        weights = self.weights if self.weights and len(self.weights) == n else [1.0/n] * n
        
        # Normalize weights if needed, but assuming they sum to 1 or user intends otherwise.
        # Let's normalize for safety if they don't sum to 1 roughly.
        total_w = sum(weights)
        if total_w == 0:
            weights = [1.0/n] * n
        else:
            weights = [w/total_w for w in weights]

        keys = predictions[0].keys()
        result = {}
        for k in keys:
            weighted_sum = sum(p.get(k, 0.0) * w for p, w in zip(predictions, weights))
            result[k] = weighted_sum
        return result
