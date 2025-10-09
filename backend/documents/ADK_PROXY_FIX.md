# ADK Agent Proxy Fix

## Problem
AWS App Runner only exposes ONE port (8080) to the public internet. The ADK Agent running on port 8082 was not accessible from the frontend, causing 404 errors.

## Solution
Added ADK Agent proxy endpoints to FastAPI so all traffic goes through port 8080.

---

## Changes Made

### 1. Backend - `main.py`
**Added:**
- `httpx` import for HTTP client
- ADK proxy endpoints:
  - `/apps/{path:path}` - Proxies all ADK Agent app endpoints
  - `/run_sse` - Proxies Server-Sent Events for chat streaming

**Configuration:**
```python
ADK_AGENT_URL = os.getenv("ADK_AGENT_URL", "http://localhost:8082")
```

### 2. Backend - `requirements.txt`
**Added:**
```
httpx>=0.25.0  # For ADK Agent proxy
```

### 3. Frontend - `src/config/api.ts`
**Changed:**
```typescript
// Before: Direct connection to ADK Agent
export const ADK_URL = import.meta.env.VITE_ADK_URL || "http://localhost:8082";

// After: Proxy through FastAPI
export const ADK_URL = import.meta.env.VITE_ADK_URL || API_URL;
```

### 4. Frontend - `.env.local`
**Changed:**
```bash
# Before
VITE_ADK_URL=http://localhost:8082

# After (proxied through FastAPI)
VITE_ADK_URL=http://localhost:8000
```

### 5. Frontend - `.env.production`
**Will be:**
```bash
VITE_API_URL=https://YOUR_SERVICE_URL.awsapprunner.com
VITE_ADK_URL=https://YOUR_SERVICE_URL.awsapprunner.com  # Same URL!
```

---

## Architecture

### Before (Broken on AWS App Runner):
```
Frontend → FastAPI (port 8080) ✅
Frontend → ADK Agent (port 8082) ❌ Not accessible
```

### After (Working):
```
Frontend → FastAPI (port 8080) → ADK Agent (port 8082) ✅
```

All traffic flows through port 8080, and FastAPI internally proxies requests to the ADK Agent.

---

## How It Works

1. **Create Session Request:**
   ```
   POST https://your-app.awsapprunner.com/apps/adk-agent/users/123/sessions/456
   
   → FastAPI receives request
   → Proxies to http://localhost:8082/apps/adk-agent/users/123/sessions/456
   → Returns response
   ```

2. **SSE Streaming (Chat):**
   ```
   POST https://your-app.awsapprunner.com/run_sse
   
   → FastAPI receives request
   → Opens SSE stream to http://localhost:8082/run_sse
   → Streams events back to frontend
   ```

---

## Testing Locally

### 1. Install httpx
```bash
cd backend
pip install httpx>=0.25.0
```

### 2. Test FastAPI with Proxy
```bash
# Terminal 1: Start all services
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
python -m MCP_Server.sse_server
cd adk-agent && adk api_server --port 8082

# Terminal 2: Test proxy
curl http://localhost:8000/health
curl http://localhost:8000/apps/adk-agent/  # Should proxy to ADK
```

### 3. Test Frontend
```bash
cd frontend
npm run dev

# Open http://localhost:5173
# Try chatbot - should work now!
```

---

## Deploying to AWS App Runner

### 1. Update Environment
```bash
cd backend

# Make sure .env has:
# DATABASE_URL=your_database_url
# PORT=8080
# ADK_AGENT_URL=http://localhost:8082  # Internal proxy
```

### 2. Rebuild and Deploy
```powershell
cd backend
.\deploy-aws.ps1 -Region "ap-southeast-1"
```

### 3. Update Vercel Frontend
After deployment, update Vercel environment variables:

```bash
VITE_API_URL=https://YOUR_SERVICE_URL.awsapprunner.com
VITE_ADK_URL=https://YOUR_SERVICE_URL.awsapprunner.com  # Same as API URL
```

**Important:** Both variables should have the SAME value!

---

## Verification

After deployment:

1. **Test API:**
   ```bash
   curl https://YOUR_SERVICE_URL.awsapprunner.com/health
   ```

2. **Test ADK Proxy:**
   ```bash
   curl https://YOUR_SERVICE_URL.awsapprunner.com/apps/adk-agent/
   ```

3. **Test Frontend:**
   - Open https://galaxy-of-knowledge-eta.vercel.app
   - Click chatbot
   - Should create session without 404 errors

---

## Benefits

1. ✅ **Single Port:** Only port 8080 needs to be exposed
2. ✅ **Simplified CORS:** All requests to same domain
3. ✅ **Better Security:** Internal services not directly exposed
4. ✅ **AWS App Runner Compatible:** Works perfectly with single-port restriction
5. ✅ **No Code Changes:** Frontend code works same way, just different URL

---

## Troubleshooting

### "502 Bad Gateway" on ADK endpoints
- Check if ADK Agent is running: `ps aux | grep adk`
- Check Docker logs: `docker logs <container_id>`
- Verify ADK_AGENT_URL environment variable

### "Connection timeout"
- Increase httpx timeout in main.py
- Check if ADK Agent started successfully
- Look for ADK Agent logs in startup script

### Frontend still getting 404
- Clear browser cache
- Verify Vercel environment variables updated
- Check frontend console for actual URL being called
- Ensure VITE_ADK_URL = VITE_API_URL

---

## Summary

**Before:** ADK Agent on port 8082 → Not accessible on AWS App Runner
**After:** FastAPI proxies ADK Agent → Everything through port 8080 ✅

**Frontend Change:** Use same URL for both API and ADK
**Backend Change:** Added proxy endpoints to FastAPI
**Result:** Chatbot now works in production! 🎉
