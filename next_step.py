- name: Trigger Airflow DAG (if tests pass)
  run: |
    curl -X POST https://<your-airflow-domain>/api/v1/dags/train_model/dagRuns \
      -H "Authorization: Basic ${{ secrets.AIRFLOW_API_AUTH }}" \
      -H "Content-Type: application/json" \
      -d '{"conf": {"commit_sha": "${{ github.sha }}"}}'




from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG("train_model", start_date=datetime(2023, 1, 1), schedule_interval=None, catchup=False) as dag:
    
    pull_docker_image = BashOperator(
        task_id="pull_image",
        bash_command="docker pull your-dockerhub-user/ai-drug-model:latest"
    )

    run_training = BashOperator(
        task_id="run_training",
        bash_command=(
            "docker run --gpus all -v /mnt/data:/mnt/data "
            "-e MLFLOW_TRACKING_URI=http://mlflow-server:5000 "
            "your-dockerhub-user/ai-drug-model:latest "
            "python train.py --data-path /mnt/data --real-run"
        )
    )

    pull_docker_image >> run_training

