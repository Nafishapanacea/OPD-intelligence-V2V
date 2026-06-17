#!/bin/bash
# =============================================================
# TTS Worker Launcher for Linux (omen machine)
# Usage: bash start_tts_workers.sh [NUM_WORKERS] [MAX_CONCURRENT]
# Example: bash start_tts_workers.sh 2 2
# =============================================================

NUM_WORKERS=${1:-2}
MAX_CONCURRENT=${2:-2}

echo "============================================"
echo "  TTS Worker Launcher (Linux)"
echo "  Workers: $NUM_WORKERS"
echo "  Max Concurrent per Worker: $MAX_CONCURRENT"
echo "============================================"

# Kill any existing TTS worker processes
echo "Stopping existing workers..."
pkill -f "app.workers.tts_worker" 2>/dev/null || true
sleep 1

# Clear stale tasks from Redis queue (optional - uncomment to flush on restart)
# echo "Flushing stale TTS tasks from Redis..."
# redis-cli DEL tts_tasks

# Change to backend directory (script's directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $(pwd)"

# Launch workers
for i in $(seq 1 $NUM_WORKERS); do
    echo "Starting TTS Worker #$i (MAX_CONCURRENT=$MAX_CONCURRENT)..."
    
    WORKER_ID=$i MAX_CONCURRENT=$MAX_CONCURRENT \
        python -m app.workers.tts_worker \
        > "tts_worker_${i}.log" 2>&1 &
    
    WORKER_PID=$!
    echo "  Worker #$i started with PID: $WORKER_PID"
done

echo ""
echo "============================================"
echo "  All $NUM_WORKERS workers launched!"
echo "  Monitor logs with:"
echo "    tail -f tts_worker_1.log"
echo "    tail -f tts_worker_2.log"
echo "  Stop all workers with:"
echo "    pkill -f 'app.workers.tts_worker'"
echo "============================================"

# Wait for all background processes
wait
