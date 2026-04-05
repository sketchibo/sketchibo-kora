#!/data/data/com.termux/files/usr/bin/bash

token_log="/data/data/com.termux/files/home/kora_local/tokens.log"

log_tokens() {
  local model="$1"
  local prompt="$2"
  local completion="$3"
  local total=$((prompt + completion))
  
  echo "$(date '+%Y-%m-%d %H:%M:%S') | $model | PROMPT:$prompt COMP:$completion TOTAL:$total" >> "$token_log"
  
  # Keep last 100 entries
  tail -100 "$token_log" > "$token_log.tmp" && mv "$token_log.tmp" "$token_log"
}

# Example usage (replace with actual API response parsing):
# log_tokens "qwen-235b" 42 18

# Generate live dashboard
plot_dashboard() {
  gnuplot << EOF
set terminal dumb
set title 'Token Usage (Last 24h)'
set xlabel 'Time'
set ylabel 'Tokens'
plot "$token_log" using 1:6 with lines title 'Total', \
     '' using 1:4 with lines title 'Prompt', \
     '' using 1:5 with lines title 'Completion'
EOF
}

plot_dashboard