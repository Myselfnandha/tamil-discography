#!/usr/bin/env bash
# Antigravity Clean MCP NPX Runner
# Ensures pure, unpolluted JSON-RPC stdio by suppressing all npm notices and ANSI escape codes.
export NO_COLOR=1
export npm_config_loglevel=silent
export FORCE_COLOR=0

exec npx --silent -y "$@"
