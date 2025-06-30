#!/bin/bash
# Usage: ./bench.sh <oss_name> <model_name> <metric>

oss_name=$1
model_name=$2
metrics=$3

current_dir=$(pwd)

# Split the metrics by comma
IFS=',' read -ra METRICS <<< "$metrics"

# Loop through each metric and run the corresponding benchmark
for metric in "${METRICS[@]}"; do
    if [ "$metric" = "compilability" ]; then
        echo "Running compilability benchmark for OSS: $oss_name, Model: $model_name..."
        tmux kill-session -t oss-bench-compilability 2>/dev/null
        tmux new-session -d -s oss-bench-compilability
        tmux send-keys -t oss-bench-compilability "cd $current_dir && python3 main.py --OSS $oss_name --model $model_name --linear-execution; tmux detach" C-m
        # Wait for the tmux session to complete
        while tmux has-session -t oss-bench-compilability 2>/dev/null; do
            sleep 2
        done
        echo "Compilability benchmark completed."
    elif [ "$metric" = "test" ]; then
        echo "Running test for OSS: $oss_name, Model: $model_name..."
        tmux kill-session -t oss-bench-dataset-gen 2>/dev/null
        tmux kill-session -t oss-bench-test 2>/dev/null
        echo "Starting dataset generation. Wait 60 seconds for it to complete..."
        tmux new-session -d -s oss-bench-dataset-gen
        tmux send-keys -t oss-bench-dataset-gen "cd $current_dir && python3 main.py --OSS $oss_name --model $model_name --dataset-generation" C-m
        sleep 60
        tmux new-session -d -s oss-bench-test
        tmux send-keys -t oss-bench-test "cd $current_dir && python3 main.py --OSS $oss_name --model $model_name --test; echo 'Press Enter to continue...'; read" C-m
        echo "Test benchmark completed."
    else
        echo "Invalid metric specified: $metric. Please use 'compilability' or 'test'."
    fi
done