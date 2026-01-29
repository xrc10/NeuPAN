echo "Waiting for debugger to attach..."
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client example/run_exp.py -e dyna_non_obs  -d omni
echo "Debugger attached"
echo "Running..."