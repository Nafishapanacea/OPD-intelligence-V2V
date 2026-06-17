#!/bin/bash
# =============================================================
# Redis Queue Maintenance Script
# Flush stale TTS tasks and check queue health
# Usage: bash flush_redis_queue.sh
# =============================================================

echo "============================================"
echo "  Redis Queue Maintenance"
echo "============================================"

# Check current queue depth
DEPTH=$(redis-cli LLEN tts_tasks)
echo "Current tts_tasks queue depth: $DEPTH"

# Count stale results
RESULT_COUNT=$(redis-cli KEYS "tts_result:*" | wc -l)
echo "Stale TTS results in cache: $RESULT_COUNT"

if [ "$DEPTH" -gt 0 ]; then
    echo ""
    read -p "Flush all $DEPTH stale tasks from queue? (y/N): " CONFIRM
    if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
        redis-cli DEL tts_tasks
        echo "✅ Queue flushed."
    else
        echo "Skipped queue flush."
    fi
fi

if [ "$RESULT_COUNT" -gt 0 ]; then
    echo ""
    read -p "Delete all $RESULT_COUNT stale TTS results? (y/N): " CONFIRM2
    if [ "$CONFIRM2" = "y" ] || [ "$CONFIRM2" = "Y" ]; then
        redis-cli KEYS "tts_result:*" | xargs -r redis-cli DEL
        echo "✅ Stale results cleared."
    else
        echo "Skipped result cleanup."
    fi
fi

echo ""
echo "Final queue depth: $(redis-cli LLEN tts_tasks)"
echo "Done."
