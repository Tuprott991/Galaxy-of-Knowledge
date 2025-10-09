# Frontend URL Configuration

## Your Frontend
**Production URL**: https://galaxy-of-knowledge-eta.vercel.app/

## CORS Configuration Applied

### 1. FastAPI Backend (`main.py`)
Updated CORS middleware to allow:
```python
allow_origins=[
    "https://galaxy-of-knowledge-eta.vercel.app",  # Production frontend
    "http://localhost:5173",  # Local Vite dev server
    "http://localhost:3000",  # Alternative local dev port
]
```

### 2. ADK Agent (Both Dockerfiles)
Updated to allow only your frontend:
```bash
--allow-origins=https://galaxy-of-knowledge-eta.vercel.app
```

## Security Benefits

✅ **More Secure**: Only your specific frontend can access the backend  
✅ **Production Ready**: No wildcard (`*`) CORS in production  
✅ **Local Development**: Localhost ports still work for testing  
✅ **Prevents Abuse**: Other websites cannot call your API  

## Testing Configuration

### Local Development
Your local frontend (http://localhost:5173) can still access:
- FastAPI backend ✅
- ADK Agent ❌ (only allows Vercel URL in Docker)

**Note**: For local ADK testing, you may want to temporarily add localhost to the ADK origins.

### Production (Cloud Run)
Your Vercel frontend can access:
- FastAPI backend ✅
- ADK Agent ✅
- MCP Server ✅ (internal only)

## Frontend Environment Configuration

Update your frontend environment variables to point to your Cloud Run backend:

### For Vercel Deployment
Create/update `.env.production` in your frontend:
```env
VITE_API_URL=https://your-cloudrun-url
VITE_ADK_URL=https://your-cloudrun-url:8082
```

### For Local Development
Create/update `.env.local` in your frontend:
```env
VITE_API_URL=http://localhost:8080
VITE_ADK_URL=http://localhost:8082
```

## If You Need Additional Origins

### Add More Allowed Origins
Edit `main.py` to add more URLs:
```python
allow_origins=[
    "https://galaxy-of-knowledge-eta.vercel.app",
    "https://your-custom-domain.com",
    "https://staging.yourdomain.com",
    "http://localhost:5173",
]
```

### For ADK Agent
Edit both Dockerfiles and add comma-separated origins:
```bash
--allow-origins=https://galaxy-of-knowledge-eta.vercel.app,https://staging.yourdomain.com
```

## Deployment Checklist

Before deploying to Cloud Run:
- [x] FastAPI CORS configured with your Vercel URL
- [x] ADK Agent configured with your Vercel URL
- [ ] Rebuild Docker image
- [ ] Deploy to Cloud Run
- [ ] Update Vercel environment variables with Cloud Run URL
- [ ] Test CORS from your frontend

## Quick Commands

### Rebuild Docker Image
```powershell
docker build -t galaxy-backend .
```

### Deploy to Cloud Run
```powershell
.\deploy-cloud-run.ps1
```

### Test CORS from Browser Console
```javascript
// On https://galaxy-of-knowledge-eta.vercel.app
fetch('https://your-backend-url/api/v1/papers')
  .then(r => r.json())
  .then(console.log)
  .catch(console.error)
```

## Troubleshooting CORS

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Solution 1**: Verify URL matches exactly (including https://)
```
✅ https://galaxy-of-knowledge-eta.vercel.app
❌ https://galaxy-of-knowledge-eta.vercel.app/
❌ http://galaxy-of-knowledge-eta.vercel.app
```

**Solution 2**: Check if credentials are needed:
```javascript
fetch(url, { credentials: 'include' })
```

**Solution 3**: For local testing, temporarily add `*`:
```python
allow_origins=["*"]  # Development only!
```

### Issue: "405 Method Not Allowed"
This is NOT a CORS issue - check your API endpoint and HTTP method.

### Issue: Preflight requests fail
Ensure `allow_methods=["*"]` and `allow_headers=["*"]` are set.

## Next Steps

1. **Test Locally** (optional):
   ```powershell
   docker-compose up
   # Update ADK origins to include localhost if needed
   ```

2. **Deploy to Cloud Run**:
   ```powershell
   .\deploy-cloud-run.ps1
   ```

3. **Update Frontend**: 
   - Add backend URL to Vercel environment variables
   - Redeploy frontend

4. **Test CORS**:
   - Open https://galaxy-of-knowledge-eta.vercel.app
   - Open browser console
   - Make API calls
   - Verify no CORS errors

## Your Configuration is Production-Ready! 🚀

The backend is now securely configured to accept requests only from your Vercel frontend while still allowing local development.
