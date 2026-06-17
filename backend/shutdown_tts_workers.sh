#!/bin/bash

echo "Stopping TTS workers..."

PIDS=$(pgrep -f "app.workers.tts_worker")

if [ -z "$PIDS" ]; then
    echo "No TTS workers running."
    exit 0
fi

echo "Found workers:"
echo "$PIDS"

kill $PIDS

sleep 2

REMAINING=$(pgrep -f "app.workers.tts_worker")

if [ -z "$REMAINING" ]; then
    echo "✅ All workers stopped."
else
    echo "⚠️ Some workers still running. Force stopping..."
    kill -9 $REMAINING
    echo "✅ Workers force stopped."
fi