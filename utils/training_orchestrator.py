"""
Training orchestrator handling pure training functions and MLflow logging.
Connects pure training logic to experiment tracking.
"""

from typing import List, Optional
import importlib.util
import pandas as pd
import mlflow
import mlflow.sklearn
import mlflow.pytorch
import pickle
import tempfile
from pathlib import Path

from .training_types import TrainingConfig, TrainingResult, TrainingFunction
from .signature import compute_training_signature


class TrainingOrchestrator:
    """Orchestrates training and experiment logging."""

    def __init__(self, mlflow_tracking_uri: str = "http://localhost:5000"):
        """
        Initialize orchestrator.

        Args:
            mlflow_tracking_uri: MLflow server URI
        """
        self.mlflow_tracking_uri = mlflow_tracking_uri
        mlflow.set_tracking_uri(mlflow_tracking_uri)

    def load_training_function(self, config: TrainingConfig) -> TrainingFunction:
        """
        Dynamically load training function from model script.

        Args:
            config: Training configuration

        Returns:
            Training function that follows the standard interface
        """
        # Load the module containing the training function
        script_path = Path(config.model_script.replace(".", "/") + ".py")

        spec = importlib.util.spec_from_file_location("training_module", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the training function (should be called 'train')
        if not hasattr(module, "train"):
            raise ValueError(
                f"Training module {script_path} must have a 'train' function"
            )

        return module.train

    def run_exists_with_tag(self, tag_key: str, tag_value: str) -> bool:
        """
        Check if any MLflow run exists with specific tag value.

        Args:
            tag_key: Tag key to search for
            tag_value: Tag value to match

        Returns:
            True if run exists with this tag, False otherwise
        """
        try:
            existing_runs = mlflow.search_runs(
                filter_string=f"tags.{tag_key} = '{tag_value}'"
            )
            return not existing_runs.empty
        except Exception as e:
            print(f"[WARNING] MLflow search failed: {e}")
            return False

    def check_if_already_trained(self, config: TrainingConfig) -> bool:
        """
        Check if model with this configuration has already been trained.
        Uses both legacy signature and composite run key if available.

        Args:
            config: Training configuration

        Returns:
            True if already trained, False otherwise
        """
        # Check composite run key first (new idempotency method)
        if hasattr(config, "composite_run_key"):
            return self.run_exists_with_tag(
                "composite_run_key", config.composite_run_key
            )

        # Fallback to legacy signature method
        signature = compute_training_signature(config.__dict__, config.signature_files)
        return self.run_exists_with_tag("signature", signature)

    def run_training(
        self,
        config: TrainingConfig,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: Optional[pd.DataFrame] = None,
        y_test: Optional[pd.Series] = None,
        force_retrain: bool = False,
    ) -> Optional[TrainingResult]:
        """
        Run training with external logging.

        Args:
            config: Training configuration
            X_train: Training features
            y_train: Training targets
            X_test: Test features (optional)
            y_test: Test targets (optional)
            force_retrain: Force training even if already done

        Returns:
            TrainingResult if training was performed, None if skipped
        """
        # Check if already trained
        if not force_retrain and self.check_if_already_trained(config):
            print(
                f"[SKIP] Model {config.model_type} already trained with current configuration"
            )
            return None

        print(f"[TRAIN] Training model: {config.model_type}")

        # Load the pure training function
        train_func = self.load_training_function(config)

        # Set MLflow experiment
        mlflow.set_experiment(config.model_type)

        # Start MLflow run and execute training
        with mlflow.start_run():
            # Log composite run key if available (new idempotency method)
            if hasattr(config, "composite_run_key"):
                mlflow.set_tag("composite_run_key", config.composite_run_key)

            # Compute and log legacy signature for backward compatibility
            signature = compute_training_signature(
                config.__dict__, config.signature_files
            )
            mlflow.set_tag("signature", signature)

            # Log configuration parameters (excluding internal fields)
            config_dict = config.__dict__.copy()
            internal_fields = ["model_script", "signature_files"]
            params = {k: v for k, v in config_dict.items() if k not in internal_fields}
            mlflow.log_params(params)

            # Execute pure training function
            result = train_func(X_train, y_train, config)

            # Log metrics
            mlflow.log_metrics(result.metrics.to_dict())

            # Log model
            self._log_model(result.model, config.model_type)

            # Log model info as tags
            for key, value in result.model_info.items():
                mlflow.set_tag(f"model_{key}", str(value))

            print(f"[COMPLETE] Training finished for {config.model_type}")
            print(f"  RMSE: {result.metrics.rmse:.4f}")
            print(f"  R2: {result.metrics.r2:.4f}")

            return result

    def _log_model(self, model, model_type: str):
        """Log model to MLflow using appropriate format."""
        try:
            # Try sklearn format first
            if hasattr(model, "fit") and hasattr(model, "predict"):
                mlflow.sklearn.log_model(model, "model")
                return
        except Exception:
            pass

        try:
            # Try PyTorch format
            if hasattr(model, "state_dict"):
                mlflow.pytorch.log_model(model, "model")
                return
        except Exception:
            pass

        # Fallback to pickle
        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            pickle.dump(model, f)
            mlflow.log_artifact(f.name, "model")

    def train_multiple_configs(
        self,
        configs: List[TrainingConfig],
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: Optional[pd.DataFrame] = None,
        y_test: Optional[pd.Series] = None,
    ) -> List[TrainingResult]:
        """
        Train multiple configurations.

        Args:
            configs: List of training configurations
            X_train: Training features
            y_train: Training targets
            X_test: Test features (optional)
            y_test: Test targets (optional)

        Returns:
            List of training results
        """
        results = []

        for config in configs:
            try:
                result = self.run_training(config, X_train, y_train, X_test, y_test)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[ERROR] Training failed for {config.model_type}: {e}")
                continue

        return results
