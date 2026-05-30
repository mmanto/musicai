#!/bin/bash
# Monitor MusicAI Logs
# Real-time log monitoring for debugging

echo "=== MusicAI Logs Monitor ==="
echo ""
echo "Monitoring logs from:"
echo "  - reasoning (port 8004)"
echo "  - musicai-backend (port 8000)"
echo "  - musicai-frontend (port 5173)"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "TIP: In another terminal, open http://localhost:5173 and send:"
echo "     'puedes hablarme sobre una cadencia conclusiva?'"
echo ""
echo "Watch for errors, timeouts, or exceptions below..."
echo ""
sleep 2

docker-compose logs -f --tail=20 reasoning musicai-backend musicai-frontend
