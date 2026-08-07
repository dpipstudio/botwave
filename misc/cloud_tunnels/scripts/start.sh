#!/bin/bash

# BotWave bore.pub Tunnel Starter

echo "Starting bore.pub tunnels..."
echo "This will expose your BotWave server to the internet."
echo ""

pkill bore 2>/dev/null || true
sleep 1

# Start tunnels (bore.pub assigns random ports)
bore local 9938 --to bore.pub > /tmp/bore_9938.log 2>&1 &
echo $! > /tmp/bore_9938.pid

bore local 9921 --to bore.pub > /tmp/bore_9921.log 2>&1 &
echo $! > /tmp/bore_9921.pid

sleep 1

echo ""
echo "=========================================="
WS_PORT=$(grep -oP 'listening at bore.pub:\K\d+' /tmp/bore_9938.log 2>/dev/null | head -1)
HTTP_PORT=$(grep -oP 'listening at bore.pub:\K\d+' /tmp/bore_9921.log 2>/dev/null | head -1)

if [ -n "$WS_PORT" ] && [ -n "$HTTP_PORT" ]; then
    echo "WebSocket: bore.pub:$WS_PORT (local 9938)"
    echo "HTTP:      bore.pub:$HTTP_PORT (local 9921)"
    echo "=========================================="
    echo ""
    echo "Connect with: sudo bw-client bore.pub --port $WS_PORT --fport $HTTP_PORT"
    echo ""
else
    echo "Error: Could not get tunnel ports."
    echo "Check logs:"
    echo "  /tmp/bore_9938.log"
    echo "  /tmp/bore_9921.log"
fi
echo "=========================================="