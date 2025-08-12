"""
Standardized types and interfaces for training functions.
This ensures all models follow the same input/output contract.
"""

from typing import Dict, Any, Protocol
from dataclasses import dataclass
import pandas as pd


@dataclass
class TrainingConfig:
    """Standard configuration for all models."""

    model_type: str
    model_script: str
    signature_files: list

    def __post_init__(self):
        """Validate required fields."""
        required_fields = ["model_type", "model_script", "signature_files"]
        for field in required_fields:
            if not getattr(self, field):
                raise ValueError(f"Required field '{field}' is missing")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "TrainingConfig":
        """Create TrainingConfig from dictionary, preserving extra fields."""
        # Extract known fields
        known_fields = {"model_type", "model_script", "signature_files"}
        config_kwargs = {k: v for k, v in config_dict.items() if k in known_fields}

        # Create instance
        instance = cls(**config_kwargs)

        # Add remaining fields as attributes
        for k, v in config_dict.items():
            if k not in known_fields:
                setattr(instance, k, v)

        return instance


@dataclass
class TrainingMetrics:
    """Standard metrics returned by all models."""

    rmse: float
    r2: float
    mae: float
    # Additional metrics can be added as needed

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for logging."""
        return {"rmse": self.rmse, "r2": self.r2, "mae": self.mae}


@dataclass
class TrainingResult:
    """Complete result from a training run."""

    model: Any  # The trained model object
    metrics: TrainingMetrics
    model_info: Dict[str, Any]  # Model metadata
    signature: str  # Content signature for deduplication


class TrainingFunction(Protocol):
    """Protocol that all training functions must implement."""

    def __call__(
        self, X_train: pd.DataFrame, y_train: pd.Series, config: TrainingConfig
    ) -> TrainingResult:
        """
        Pure training function interface.

        Args:
            X_train: Training features
            y_train: Training targets
            config: Training configuration

        Returns:
            TrainingResult with model, metrics, and metadata
        """
        ...


def validate_training_function(
    func: TrainingFunction,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    config: TrainingConfig,
) -> bool:
    """
    Validate that a training function follows the standard interface.

    Args:
        func: Training function to validate
        X_train: Sample training data
        y_train: Sample training targets
        config: Sample configuration

    Returns:
        True if function is valid

    Raises:
        ValueError if function doesn't follow interface
    """
    try:
        result = func(X_train, y_train, config)

        if not isinstance(result, TrainingResult):
            raise ValueError("Training function must return TrainingResult")

        if not isinstance(result.metrics, TrainingMetrics):
            raise ValueError("TrainingResult.metrics must be TrainingMetrics")

        if result.model is None:
            raise ValueError("TrainingResult.model cannot be None")

        return True

    except Exception as e:
        raise ValueError(f"Training function validation failed: {e}")
