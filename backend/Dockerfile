# ============================================
# Multi-Stage Dockerfile for Galaxy of Knowledge Backend
# Includes: FastAPI, ADK Agent, and MCP Server
# Optimized for Google Cloud Run
# ============================================

# Stage 1: Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Runtime stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Copy environment file and service account
# These will be overridden by Cloud Run secrets in production
COPY .env .env
COPY service_account.json service_account.json

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8080
ENV MCP_PORT=8081
ENV ADK_PORT=8082

# Expose ports
# Cloud Run will route external traffic to PORT (8080)
# Internal services can communicate on their respective ports
EXPOSE 8080
EXPOSE 8081
EXPOSE 8082

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Function to handle shutdown gracefully\n\
cleanup() {\n\
    echo "Shutting down services..."\n\
    kill -TERM "$fastapi_pid" "$mcp_pid" "$adk_pid" 2>/dev/null || true\n\
    wait "$fastapi_pid" "$mcp_pid" "$adk_pid" 2>/dev/null || true\n\
    echo "All services stopped"\n\
    exit 0\n\
}\n\
\n\
# Trap SIGTERM and SIGINT\n\
trap cleanup SIGTERM SIGINT\n\
\n\
echo "========================================"\n\
echo "Starting Galaxy of Knowledge Backend"\n\
echo "========================================"\n\
\n\
# Start MCP Server\n\
echo "🚀 Starting MCP Server on port ${MCP_PORT}..."\n\
python -m MCP_Server.sse_server --host 0.0.0.0 --port ${MCP_PORT} > /tmp/mcp_server.log 2>&1 &\n\
mcp_pid=$!\n\
echo "✅ MCP Server started (PID: $mcp_pid)"\n\
\n\
# Wait for MCP Server to be ready\n\
sleep 3\n\
\n\
# Start ADK Agent\n\
echo "🚀 Starting ADK Agent on port ${ADK_PORT}..."\n\
cd adk-agent && adk api_server --host 0.0.0.0 --port ${ADK_PORT} --allow_origins=https://galaxy-of-knowledge-eta.vercel.app > /tmp/adk_agent.log 2>&1 &\n\
adk_pid=$!\n\
echo "✅ ADK Agent started (PID: $adk_pid)"\n\
cd ..\n\
\n\
# Wait for ADK to be ready\n\
sleep 3\n\
\n\
# Start FastAPI Server (from /app directory where main.py is)\n\
echo "🚀 Starting FastAPI Server on port ${PORT}..."\n\
cd /app && uvicorn main:app --host 0.0.0.0 --port ${PORT} > /tmp/fastapi.log 2>&1 &\n\
fastapi_pid=$!\n\
echo "✅ FastAPI Server started (PID: $fastapi_pid)"\n\
\n\
echo "========================================"\n\
echo "✅ All services are running!"\n\
echo "FastAPI:    http://0.0.0.0:${PORT}"\n\
echo "MCP Server: http://0.0.0.0:${MCP_PORT}"\n\
echo "ADK Agent:  http://0.0.0.0:${ADK_PORT}"\n\
echo "========================================"\n\
\n\
# Monitor all services\n\
while kill -0 "$fastapi_pid" 2>/dev/null && \\\n\
      kill -0 "$mcp_pid" 2>/dev/null && \\\n\
      kill -0 "$adk_pid" 2>/dev/null; do\n\
    sleep 5\n\
done\n\
\n\
echo "⚠️ One or more services died, checking logs..."\n\
echo "=== FastAPI Logs ==="\n\
tail -n 50 /tmp/fastapi.log || true\n\
echo "=== MCP Server Logs ==="\n\
tail -n 50 /tmp/mcp_server.log || true\n\
echo "=== ADK Agent Logs ==="\n\
tail -n 50 /tmp/adk_agent.log || true\n\
\n\
cleanup\n\
' > /app/start.sh && chmod +x /app/start.sh

# Use the startup script as entrypoint
CMD ["/app/start.sh"]
