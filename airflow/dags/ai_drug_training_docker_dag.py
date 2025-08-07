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
    'ai_drug_training_docker',
    default_args=default_args,
    description='AI Drug Discovery Training Pipeline with Docker Registry',
    schedule_interval=None,  # Only triggered externally
    catchup=False,
    max_active_runs=1,
    tags=['ml', 'training', 'drug-discovery', 'docker']
)

def setup_environment(**context):
    """Setup training environment and validate prerequisites"""
    print("Setting up Docker-based training environment...")
    
    # Get Docker image from DAG run configuration
    docker_image = context['dag_run'].conf.get('docker_image', 'ghcr.io/j0mt/ai-drug-training:latest')
    github_sha = context['dag_run'].conf.get('github_sha', 'unknown')
    
    print(f"Using Docker image: {docker_image}")
    print(f"GitHub SHA: {github_sha}")
    
    # Set environment variables
    os.environ['DOCKER_IMAGE'] = docker_image
    os.environ['MLFLOW_TRACKING_URI'] = 'http://localhost:5000'
    
    # Change to project directory
    os.chdir('/home/ubuntu/AI_Drug')
    
    # Ensure MLflow and PostgreSQL are running
    print("Starting MLflow and PostgreSQL containers...")
    subprocess.run([
        'docker-compose', '-f', 'docker-compose.training.yml', 
        'up', '-d', 'mlflow', 'postgres'
    ], check=True)
    
    # Wait for MLflow to be ready
    import time
    import requests
    for i in range(30):  # Wait up to 5 minutes
        try:
            response = requests.get('http://localhost:5000/health')
            if response.status_code == 200:
                print("MLflow server is ready")
                break
        except:
            pass
        time.sleep(10)
        print(f"Waiting for MLflow... attempt {i+1}/30")
    else:
        raise Exception("MLflow server failed to start")

def pull_docker_image(**context):
    """Pull the latest Docker image with training code"""
    docker_image = context['dag_run'].conf.get('docker_image', 'ghcr.io/j0mt/ai-drug-training:latest')
    
    print(f"Pulling Docker image: {docker_image}")
    
    # Pull the Docker image
    result = subprocess.run(['docker', 'pull', docker_image], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Failed to pull Docker image: {result.stderr}")
        raise Exception(f"Docker pull failed: {result.stderr}")
    
    print("Docker image pulled successfully")
    print(f"Output: {result.stdout}")

def discover_training_configs(**context):
    """Discover all training configurations from Docker image"""
    docker_image = context['dag_run'].conf.get('docker_image', 'ghcr.io/j0mt/ai-drug-training:latest')
    
    print("Discovering training configurations from Docker image...")
    
    # Run container to list config files
    result = subprocess.run([
        'docker', 'run', '--rm', docker_image,
        'find', '/app/configs', '-name', '*.yaml'
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"Failed to discover configs: {result.stderr}")
        raise Exception(f"Config discovery failed: {result.stderr}")
    
    config_files = result.stdout.strip().split('\n')
    config_files = [f for f in config_files if f]  # Remove empty strings
    
    configs = []
    for config_path in config_files:
        # Extract config content from Docker image
        result = subprocess.run([
            'docker', 'run', '--rm', docker_image,
            'cat', config_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            config['config_path'] = config_path
            configs.append(config)
    
    print(f"Found {len(configs)} training configurations")
    
    # Store configs in XCom for downstream tasks
    return configs

def check_signatures_and_filter(**context):
    """Check MLflow for existing runs with same signatures"""
    docker_image = context['dag_run'].conf.get('docker_image', 'ghcr.io/j0mt/ai-drug-training:latest')
    configs = context['task_instance'].xcom_pull(task_ids='discover_configs')
    configs_to_train = []
    
    mlflow.set_tracking_uri("http://localhost:5000")
    
    for config in configs:
        # Compute signature using Docker container
        signature_files = config.get('signature_files', [])
        signature_cmd = [
            'docker', 'run', '--rm', docker_image,
            'python', '-c', f'''
import sys
sys.path.append("/app")
from utils.signature import compute_training_signature
import yaml

config = {repr(config)}
signature_files = {repr(signature_files)}
signature = compute_training_signature(config, signature_files)
print(signature)
'''
        ]
        
        result = subprocess.run(signature_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Failed to compute signature for {config['config_path']}: {result.stderr}")
            continue
            
        signature = result.stdout.strip()
        
        # Check if this signature already exists
        existing_runs = mlflow.search_runs(
            filter_string=f"tags.signature = '{signature}'"
        )
        
        if existing_runs.empty:
            config['signature'] = signature
            configs_to_train.append(config)
            print(f"Config {config['config_path']} needs training (new signature: {signature[:8]}...)")
        else:
            print(f"Config {config['config_path']} already trained (signature exists: {signature[:8]}...)")
    
    print(f"Configs to train: {len(configs_to_train)}")
    return configs_to_train

def train_models_with_docker(**context):
    """Train all models that need training using Docker containers"""
    docker_image = context['dag_run'].conf.get('docker_image', 'ghcr.io/j0mt/ai-drug-training:latest')
    configs_to_train = context['task_instance'].xcom_pull(task_ids='check_signatures')
    
    if not configs_to_train:
        print("No models need training - all signatures already exist")
        return
    
    os.chdir('/home/ubuntu/AI_Drug')
    
    # Set environment variables for training
    env = os.environ.copy()
    env['TRAINING_IMAGE'] = docker_image
    
    for config in configs_to_train:
        config_path = config['config_path']
        model_script = config.get('model_script', 'train_dispatch.py')
        
        print(f"Training model: {config_path}")
        
        # Run training in Docker container
        cmd = [
            'docker-compose', '-f', 'docker-compose.training.yml',
            '--profile', 'training', 'run', '--rm', 'training',
            'python', model_script, '--config', config_path
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Training failed for {config_path}")
            print(f"Error: {result.stderr}")
            raise Exception(f"Training failed for {config_path}: {result.stderr}")
        
        print(f"Training completed successfully for {config_path}")
        print(f"Output: {result.stdout}")

def aggregate_results(**context):
    """Aggregate training results and log summary"""
    print("Aggregating training results...")
    
    configs_trained = context['task_instance'].xcom_pull(task_ids='check_signatures')
    
    if not configs_trained:
        print("No models were trained (all signatures already exist)")
        return
    
    # Query MLflow for latest runs
    mlflow.set_tracking_uri("http://localhost:5000")
    
    summary = {
        'total_configs': len(configs_trained),
        'training_timestamp': datetime.now().isoformat(),
        'docker_image': context['dag_run'].conf.get('docker_image', 'unknown'),
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
    
    os.chdir('/home/ubuntu/AI_Drug')
    
    # Clean up Docker containers and images
    subprocess.run(['docker', 'system', 'prune', '-f'], check=False)
    
    # Keep MLflow running for result access
    print("Keeping MLflow running for result access")
    
    print("Cleanup completed")
    
    # Optional: Shutdown EC2 instance after delay
    print("Scheduling instance shutdown in 30 minutes for cost optimization...")
    subprocess.run(['sudo', 'shutdown', '-h', '+30'], check=False)

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

pull_image_task = PythonOperator(
    task_id='pull_docker_image',
    python_callable=pull_docker_image,
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

train_models_task = PythonOperator(
    task_id='train_models',
    python_callable=train_models_with_docker,
    dag=dag
)

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
(start_task >> setup_env_task >> pull_image_task >> discover_configs_task >> 
 check_signatures_task >> train_models_task >> aggregate_task >> cleanup_task >> end_task)