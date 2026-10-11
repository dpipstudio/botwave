#!/bin/bash
# updates the botwave prompt using the "PROMPT_TEXT" env var.

DEFAULT_PROMPT="botwave ›"
[ -z "$BW_ARGV1" ] && PROMPT="$DEFAULT_PROMPT" || PROMPT="$BW_ARGV1"
[ "$BW_ARGV2" = "true" ] && PERMANENT=true || PERMANENT=false

echo "set PROMPT_TEXT '$PROMPT '"

if [ "$PERMANENT" = true ]; then
    echo "PROMPT_TEXT='$PROMPT '" >> /opt/BotWave/.env
fi