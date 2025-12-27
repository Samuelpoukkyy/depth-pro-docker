#!/bin/bash
# MCP 服务器启动脚本
cd /app
export PYTHONPATH=/app/src
python3 mcp_server.py
