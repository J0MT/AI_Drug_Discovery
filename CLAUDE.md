# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production-ready pipeline for target-agnostic, structure-based drug discovery. The pipeline supports automated screening of ligands against protein targets from ChEMBL, extracting 2D fingerprints, ADMET properties, and generating 3D conformers for molecular docking. It transforms raw chemical and docking data into structured features for structure-function modeling (predicting IC₅₀ values).

The system integrates multiple ML models (Transformer, XGBoost, Random Forest) with MLflow experiment tracking, DVC data versioning, and Docker containerization.

## Architecture

### Core Components
- **Training Pipeline**: `train_dispatch.py` orchestrates training across all model configurations
- **Model Implementations**: Three model types in `models/` (transformer, xgb, rf)
- **Configuration**: YAML configs in `configs/` define model hyperparameters and training settings
- **Utilities**: `utils/` contains preprocessing, evaluation, and signature computation
- **Data Management**: DVC tracks data versions, MLflow tracks experiments

### Training Flow
1. `train_dispatch.py` iterates through all YAML configs in `configs/`
2. For each config, computes a signature hash from config + source code
3. Checks MLflow for existing runs with same signature (avoids retraining)
4. If not found, executes the model's training script with the config
5. Training script pulls data via DVC, preprocesses, trains, and logs to MLflow

### Signature System
The project uses content-based signatures to track model training state:
- Combines config parameters + source code hashes
- Prevents redundant training when code/config unchanged
- Implemented in `utils/signature.py` and used by `train_dispatch.py`

## Development Commands

### Local Development Environment Setup
```bash
# Using conda
conda env create -f environment.yml
conda activate AI_Drug_conda

# Using pip
pip install -r requirements.txt
```

### Local Data Management
```bash
# Pull latest data from DVC remote (S3)
dvc pull

# Specific file pull
dvc pull data/data_200.csv.dvc

# Configure DVC remote (one-time setup)
dvc remote add -d myremote s3://your-dvc-bucket/data
```

### Local Training (Development)
```bash
# Train all models with all configs locally
python train_dispatch.py

# Train specific model with specific config
python models/transformer/train.py --config configs/transformer.yaml

# Dry run (validation only)
python models/transformer/train.py --config configs/transformer.yaml --dry-run
```

### Testing and Linting
```bash
# Run all tests
PYTHONPATH=. pytest tests/

# Run specific test
PYTHONPATH=. pytest tests/test_model_training.py

# Code formatting
black .
black . --check  # check only, don't modify

# Linting
flake8 .
```

### Production Training Workflow
```bash
# Push to main branch triggers production training
git push origin main

# Monitor training progress
# - Airflow UI: http://EC2_IP:8080
# - MLflow UI: http://EC2_IP:5000
```

### AWS Infrastructure Management
```bash
# Deploy infrastructure (one-time)
cd aws/terraform
terraform init
terraform plan
terraform apply

# SSH to training instance
ssh -i your-key.pem ubuntu@EC2_IP

# Check training status on EC2
/home/ubuntu/check-training.sh

# Start MLflow manually (if needed)
/home/ubuntu/start-mlflow.sh
```

### MLflow Environments
- **Local Development**: `http://localhost:5000`
- **Production (AWS)**: `http://EC2_IP:5000`
- Experiments organized by model type
- Runs tagged with content signatures for deduplication

## Key Files to Understand

### Core Training Files
- `train_dispatch.py`: Local orchestration script
- `models/*/train.py`: Model-specific training implementations
- `utils/__init__.py`: Core utility functions (preprocess, split_data, evaluate)
- `configs/*.yaml`: Model configurations and hyperparameters
- `tests/test_model_training.py`: Parameterized tests for all model types

### AWS/Production Files
- `.github/workflows/ci.yml`: CI/CD pipeline with AWS integration
- `airflow/dags/ai_drug_training_dag.py`: Production training DAG
- `aws/ec2-setup.sh`: EC2 instance setup script
- `aws/terraform/main.tf`: Infrastructure as code

## Model Addition Pattern

To add a new model type:
1. Create `models/new_model/` directory with `__init__.py`, `model.py`, `train.py`
2. Implement `train(X_train, y_train, config)` function in `model.py`
3. Create training script in `train.py` following existing pattern
4. Add YAML config in `configs/` with model_type, model_script, signature_files
5. Update `tests/test_model_training.py` MODEL_PATHS dictionary
6. Update Airflow DAG to include new model in training tasks

# Claude Code Guidelines by Sabrina Ramonov

## Implementation Best Practices

### 0 — Purpose  

These rules ensure maintainability, safety, and developer velocity. 
**MUST** rules are enforced by CI; **SHOULD** rules are strongly recommended.

---

### 1 — Before Coding

- **BP-1 (MUST)** Ask the user clarifying questions.
- **BP-2 (SHOULD)** Draft and confirm an approach for complex work.  
- **BP-3 (SHOULD)** If ≥ 2 approaches exist, list clear pros and cons.
- **BP-4 (MUST)** Update or create `projectplan.md` with current project structure and flow breakdown before making any changes.

---

### 2 — While Coding

- **C-1 (MUST)** Follow TDD: scaffold stub -> write failing test -> implement.
- **C-2 (MUST)** Name functions with existing domain vocabulary for consistency.  
- **C-3 (SHOULD NOT)** Introduce classes when small testable functions suffice.  
- **C-4 (SHOULD)** Prefer simple, composable, testable functions.
- **C-5 (SHOULD)** Use type hints for function parameters and return values in Python
  ```python
  def preprocess(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:  # ✅ Good
  def preprocess(df):  # ❌ Bad
  ```
- **C-6 (SHOULD)** Use descriptive variable names that match the domain (e.g., `X_train`, `y_train`, `config`, `signature`).
- **C-7 (SHOULD NOT)** Add comments except for critical caveats; rely on self‑explanatory code.
- **C-8 (MUST)** Update `projectplan.md` after implementing any significant changes to reflect new structure or flow.
- **C-9 (SHOULD NOT)** Extract a new function unless it will be reused elsewhere, is the only way to unit-test otherwise untestable logic, or drastically improves readability of an opaque block.

---

### 3 — Testing

- **T-1 (MUST)** For simple functions, create unit tests in `tests/` directory.
- **T-2 (MUST)** For any model changes, add/extend integration tests in `tests/test_model_training.py`.
- **T-3 (MUST)** ALWAYS separate pure-logic unit tests from model training integration tests.
- **T-4 (SHOULD)** Prefer integration tests over heavy mocking.  
- **T-5 (SHOULD)** Unit-test complex algorithms thoroughly.
- **T-6 (SHOULD)** Test the entire structure in one assertion if possible
  ```python
  assert result == expected_output  # Good

  assert len(result) == 1  # Bad
  assert result[0] == expected_value  # Bad
  ```

---

### 4 — Data Management

- **D-1 (MUST)** Always use DVC for data versioning - run `dvc pull` before training.
- **D-2 (MUST)** Log all experiments to MLflow with proper tags and metrics.
- **D-3 (SHOULD)** Use the signature system to avoid redundant training runs.

---

### 5 — Code Organization

- **O-1 (MUST)** Place shared utilities in `utils/` only if used by ≥ 2 model types.
- **O-2 (MUST)** Follow the established model structure: `models/{model_name}/` with `__init__.py`, `model.py`, `train.py`.
- **O-3 (MUST)** Keep configurations in `configs/` as YAML files with consistent naming.

---

### 6 — Tooling Gates

- **G-1 (MUST)** `black . --check` passes (code formatting).  
- **G-2 (MUST)** `flake8 .` passes (linting).
- **G-3 (MUST)** `PYTHONPATH=. pytest tests/` passes (all tests).  

---

### 7 - Git

- **GH-1 (MUST)** Use Conventional Commits format when writing commit messages: https://www.conventionalcommits.org/en/v1.0.0
- **GH-2 (SHOULD NOT)** Refer to Claude or Anthropic in commit messages.

---

## Writing Functions Best Practices

When evaluating whether a function you implemented is good or not, use this checklist:

1. Can you read the function and HONESTLY easily follow what it's doing? If yes, then stop here.
2. Does the function have very high cyclomatic complexity? (number of independent paths, or, in a lot of cases, number of nesting if if-else as a proxy). If it does, then it's probably sketchy.
3. Are there any common data structures and algorithms that would make this function much easier to follow and more robust? Parsers, trees, stacks / queues, etc.
4. Are there any unused parameters in the function?
5. Are there any unnecessary type casts that can be moved to function arguments?
6. Is the function easily testable without mocking core features (e.g. sql queries, redis, etc.)? If not, can this function be tested as part of an integration test?
7. Does it have any hidden untested dependencies or any values that can be factored out into the arguments instead? Only care about non-trivial dependencies that can actually change or affect the function.
8. Brainstorm 3 better function names and see if the current name is the best, consistent with rest of codebase.

IMPORTANT: you SHOULD NOT refactor out a separate function unless there is a compelling need, such as:
  - the refactored function is used in more than one place
  - the refactored function is easily unit testable while the original function is not AND you can't test it any other way
  - the original function is extremely hard to follow and you resort to putting comments everywhere just to explain it

## Writing Tests Best Practices

When evaluating whether a test you've implemented is good or not, use this checklist:

1. SHOULD parameterize inputs; never embed unexplained literals such as 42 or "foo" directly in the test.
2. SHOULD NOT add a test unless it can fail for a real defect. Trivial asserts (e.g., expect(2).toBe(2)) are forbidden.
3. SHOULD ensure the test description states exactly what the final expect verifies. If the wording and assert don't align, rename or rewrite.
4. SHOULD compare results to independent, pre-computed expectations or to properties of the domain, never to the function's output re-used as the oracle.
5. SHOULD follow the same lint, type-safety, and style rules as prod code (prettier, ESLint, strict types).
6. SHOULD express invariants or axioms (e.g., commutativity, idempotence, round-trip) rather than single hard-coded cases whenever practical. Use `fast-check` library e.g.
```
import fc from 'fast-check';
import { describe, expect, test } from 'vitest';
import { getCharacterCount } from './string';

describe('properties', () => {
  test('concatenation functoriality', () => {
    fc.assert(
      fc.property(
        fc.string(),
        fc.string(),
        (a, b) =>
          getCharacterCount(a + b) ===
          getCharacterCount(a) + getCharacterCount(b)
      )
    );
  });
});
```

7. Unit tests for a function should be grouped under `describe(functionName, () => ...`.
8. Use `expect.any(...)` when testing for parameters that can be anything (e.g. variable ids).
9. ALWAYS use strong assertions over weaker ones e.g. `expect(x).toEqual(1)` instead of `expect(x).toBeGreaterThanOrEqual(1)`.
10. SHOULD test edge cases, realistic input, unexpected input, and value boundaries.
11. SHOULD NOT test conditions that are caught by the type checker.

## Project Structure

- `models/` - ML model implementations (transformer, xgb, rf)
  - `models/{model_name}/model.py` - Model architecture and training logic
  - `models/{model_name}/train.py` - Training script with MLflow integration
- `utils/` - Shared utilities for preprocessing, evaluation, and signatures
- `configs/` - YAML configuration files for model hyperparameters
- `tests/` - Unit and integration tests
- `data/` - DVC-tracked datasets

## Remember Shortcuts

Remember the following shortcuts which the user may invoke at any time.

### QNEW

When I type "qnew", this means:

```
Understand all BEST PRACTICES listed in CLAUDE.md.
Your code SHOULD ALWAYS follow these best practices.
```

### QPLAN
When I type "qplan", this means:
```
Analyze similar parts of the codebase and determine whether your plan:
- is consistent with rest of codebase
- introduces minimal changes
- reuses existing code
```

## QCODE

When I type "qcode", this means:

```
Implement your plan and make sure your new tests pass.
Always run tests to make sure you didn't break anything else.
Always run `black .` on the newly created files to ensure standard formatting.
Always run `flake8 .` to make sure linting passes.
Update `projectplan.md` to reflect the implemented changes.
```

### QCHECK

When I type "qcheck", this means:

```
You are a SKEPTICAL senior software engineer.
Perform this analysis for every MAJOR code change you introduced (skip minor changes):

1. CLAUDE.md checklist Writing Functions Best Practices.
2. CLAUDE.md checklist Writing Tests Best Practices.
3. CLAUDE.md checklist Implementation Best Practices.
```

### QCHECKF

When I type "qcheckf", this means:

```
You are a SKEPTICAL senior software engineer.
Perform this analysis for every MAJOR function you added or edited (skip minor changes):

1. CLAUDE.md checklist Writing Functions Best Practices.
```

### QCHECKT

When I type "qcheckt", this means:

```
You are a SKEPTICAL senior software engineer.
Perform this analysis for every MAJOR test you added or edited (skip minor changes):

1. CLAUDE.md checklist Writing Tests Best Practices.
```

### QUX

When I type "qux", this means:

```
Imagine you are a human UX tester of the feature you implemented. 
Output a comprehensive list of scenarios you would test, sorted by highest priority.
```

### QGIT

When I type "qgit", this means:

```
Add all changes to staging, create a commit, and push to remote.

Follow this checklist for writing your commit message:
- SHOULD use Conventional Commits format: https://www.conventionalcommits.org/en/v1.0.0
- SHOULD NOT refer to Claude or Anthropic in the commit message.
- SHOULD structure commit message as follows:
<type>[optional scope]: <description>
[optional body]
[optional footer(s)]
- commit SHOULD contain the following structural elements to communicate intent: 
fix: a commit of the type fix patches a bug in your codebase (this correlates with PATCH in Semantic Versioning).
feat: a commit of the type feat introduces a new feature to the codebase (this correlates with MINOR in Semantic Versioning).
BREAKING CHANGE: a commit that has a footer BREAKING CHANGE:, or appends a ! after the type/scope, introduces a breaking API change (correlating with MAJOR in Semantic Versioning). A BREAKING CHANGE can be part of commits of any type.
types other than fix: and feat: are allowed, for example @commitlint/config-conventional (based on the Angular convention) recommends build:, chore:, ci:, docs:, style:, refactor:, perf:, test:, and others.
footers other than BREAKING CHANGE: <description> may be provided and follow a convention similar to git trailer format.
``` where relevant

---

## 8 - Communication Style

- **CS-1 (MUST)** When explaining technical concepts, use the "Container Breakdown" format:
  - Start with **Off-the-shelf Components** vs **Custom Components** distinction
  - List each component with its **Purpose** and **Role**  
  - End with **Why This Architecture?** section explaining the design decisions
  - Keep explanations concise but complete
- **CS-2 (SHOULD)** Structure complex explanations as:
  1. **What**: Brief summary of what's happening
  2. **Components**: Break down each piece and its role
  3. **Why**: Explain the reasoning behind the design
- **CS-3 (SHOULD)** Use bullet points and clear headers for easy scanning
- **CS-4 (SHOULD)** End technical explanations with a clear next action question