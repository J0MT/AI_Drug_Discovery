from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.models import Variable
import subprocess
import os
import yaml
import glob
import mlflow

default_args = {
    'owner': 'ai-drug-discovery',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'ai_drug_training',
    default_args=default_args,
    description='AI Drug Discovery Training Pipeline',
    schedule_interval=None,  # Only triggered externally
    catchup=False,
    max_active_runs=1,
    tags=['ml', 'training', 'drug-discovery']
)

def setup_environment(**context):
    """Setup training environment and validate prerequisites"""
    print("Setting up training environment...")
    
    # Set environment variables
    os.environ['PYTHONPATH'] = '/home/ubuntu/AI_Drug'
    os.environ['MLFLOW_TRACKING_URI'] = 'http://localhost:5000'
    
    # Ensure MLflow server is running
    try:
        subprocess.run(['pgrep', '-f', 'mlflow'], check=True, capture_output=True)
        print("MLflow server is running")
    except subprocess.CalledProcessError:
        print("Starting MLflow server...")
        subprocess.Popen([
            'mlflow', 'server', 
            '--host', '0.0.0.0', 
            '--port', '5000',
            '--backend-store-uri', 'sqlite:///mlflow.db',
            '--default-artifact-root', './mlruns'
        ])
        
    # Wait for MLflow to be ready
    import time
    import requests
    for _ in range(30):  # Wait up to 5 minutes
        try:
            response = requests.get('http://localhost:5000/health')
            if response.status_code == 200:
                print("MLflow server is ready")
                break
        except:
            pass
        time.sleep(10)
    else:
        raise Exception("MLflow server failed to start")

def pull_data_and_code(**context):
    """Pull latest data from DVC and sync code"""
    print("Pulling data from DVC...")
    
    # Change to project directory
    os.chdir('/home/ubuntu/AI_Drug')
    
    # Pull latest code (if using git)
    github_sha = context['dag_run'].conf.get('github_sha')
    if github_sha:
        print(f"Checking out commit: {github_sha}")
        subprocess.run(['git', 'fetch', 'origin'], check=True)
        subprocess.run(['git', 'checkout', github_sha], check=True)
    
    # Pull data from DVC
    subprocess.run(['dvc', 'pull'], check=True)
    print("Data pulled successfully")

def discover_training_configs(**context):
    """Discover all training configurations"""
    configs = []
    config_files = glob.glob('/home/ubuntu/AI_Drug/configs/*.yaml')
    
    for config_path in config_files:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        config['config_path'] = config_path
        configs.append(config)
    
    print(f"Found {len(configs)} training configurations")
    
    # Store configs in XCom for downstream tasks
    return configs

def check_signatures_and_filter(**context):
    """Check MLflow for existing runs with same signatures"""
    from models.transformer.train import compute_training_signature
    
    configs = context['task_instance'].xcom_pull(task_ids='discover_configs')
    configs_to_train = []
    
    mlflow.set_tracking_uri("http://localhost:5000")
    
    for config in configs:
        signature = compute_training_signature(config, config["signature_files"])
        
        # Check if this signature already exists
        existing_runs = mlflow.search_runs(
            filter_string=f"tags.signature = '{signature}'"
        )
        
        if existing_runs.empty:
            config['signature'] = signature
            configs_to_train.append(config)
            print(f"Config {config['config_path']} needs training (new signature)")
        else:
            print(f"Config {config['config_path']} already trained (signature exists)")
    
    print(f"Configs to train: {len(configs_to_train)}")
    return configs_to_train

def train_single_model(config_path, **context):
    """Train a single model configuration"""
    print(f"Training model with config: {config_path}")
    
    os.chdir('/home/ubuntu/AI_Drug')
    
    # Load config to get model script
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Execute training script
    cmd = ['python', config['model_script'], '--config', config_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Training failed for {config_path}")
        print(f"Error: {result.stderr}")
        raise Exception(f"Training failed: {result.stderr}")
    
    print(f"Training completed successfully for {config_path}")
    print(f"Output: {result.stdout}")

def aggregate_results(**context):
    """Aggregate training results and log summary"""
    print("Aggregating training results...")
    
    # Get all configs that were trained
    configs_trained = context['task_instance'].xcom_pull(task_ids='check_signatures')
    
    if not configs_trained:
        print("No models were trained (all signatures already exist)")
        return
    
    # Query MLflow for latest runs
    mlflow.set_tracking_uri("http://localhost:5000")
    
    summary = {
        'total_configs': len(configs_trained),
        'training_timestamp': datetime.now().isoformat(),
        'github_sha': context['dag_run'].conf.get('github_sha', 'unknown')
    }
    
    for config in configs_trained:
        model_type = config.get('model_type', 'unknown')
        
        # Get latest run for this model type
        runs = mlflow.search_runs(
            experiment_names=[model_type],
            order_by=["start_time DESC"],
            max_results=1
        )
        
        if not runs.empty:
            run = runs.iloc[0]
            summary[f'{model_type}_rmse'] = run.get('metrics.rmse', 'N/A')
            summary[f'{model_type}_r2'] = run.get('metrics.r2', 'N/A')
    
    print("Training Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")

def cleanup_and_shutdown(**context):
    """Cleanup resources and optionally shutdown instance"""
    print("Cleaning up resources...")
    
    # Clean up temporary files
    os.chdir('/home/ubuntu/AI_Drug')
    subprocess.run(['find', '.', '-name', '*.pyc', '-delete'], check=False)
    subprocess.run(['find', '.', '-name', '__pycache__', '-type', 'd', '-exec', 'rm', '-rf', '{}', '+'], check=False)
    
    # Optional: Stop MLflow server (if desired)
    # subprocess.run(['pkill', '-f', 'mlflow'], check=False)
    
    print("Cleanup completed")
    
    # Optional: Shutdown EC2 instance (uncomment if desired)
    # print("Shutting down EC2 instance...")
    # subprocess.run(['sudo', 'shutdown', '-h', '+5'], check=False)

# Define tasks
start_task = DummyOperator(
    task_id='start',
    dag=dag
)

setup_env_task = PythonOperator(
    task_id='setup_environment',
    python_callable=setup_environment,
    dag=dag
)

pull_data_task = PythonOperator(
    task_id='pull_data_and_code',
    python_callable=pull_data_and_code,
    dag=dag
)

discover_configs_task = PythonOperator(
    task_id='discover_configs',
    python_callable=discover_training_configs,
    dag=dag
)

check_signatures_task = PythonOperator(
    task_id='check_signatures',
    python_callable=check_signatures_and_filter,
    dag=dag
)

# Dynamic task creation for parallel training
def create_training_tasks():
    """Create training tasks dynamically based on configs"""
    training_tasks = []
    
    # Create tasks for each model type (will be filtered by signatures at runtime)
    model_configs = [
        {'name': 'transformer', 'config_path': 'configs/transformer.yaml'},
        # Add more configs as they're created
        # {'name': 'xgb', 'config_path': 'configs/xgb.yaml'},
        # {'name': 'rf', 'config_path': 'configs/rf.yaml'},
    ]
    
    for model_config in model_configs:
        task = PythonOperator(
            task_id=f'train_{model_config["name"]}',
            python_callable=train_single_model,
            op_args=[model_config['config_path']],
            dag=dag
        )
        training_tasks.append(task)
    
    return training_tasks

training_tasks = create_training_tasks()

aggregate_task = PythonOperator(
    task_id='aggregate_results',
    python_callable=aggregate_results,
    dag=dag
)

cleanup_task = PythonOperator(
    task_id='cleanup_and_shutdown',
    python_callable=cleanup_and_shutdown,
    dag=dag
)

end_task = DummyOperator(
    task_id='end',
    dag=dag
)

# Define task dependencies
start_task >> setup_env_task >> pull_data_task >> discover_configs_task >> check_signatures_task

# Training tasks run in parallel after signature check
for training_task in training_tasks:
    check_signatures_task >> training_task >> aggregate_task

aggregate_task >> cleanup_task >> end_task