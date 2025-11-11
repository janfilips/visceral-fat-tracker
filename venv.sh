
#!/bin/bash
# Ensure this script is sourced, not executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "Please run this script with: source $0" >&2
  exit 1
fi

python3.13 -m venv .venv
source .venv/bin/activate
