# ADK Agent CORS Configuration Update

## What Changed

Added `--allow-origins=*` flag to the ADK API server in all Docker configurations to allow Cross-Origin Resource Sharing (CORS) from any origin.

## Files Updated

### 1. `Dockerfile` (Main Production)
Updated ADK Agent start command:
```bash
cd adk-agent && adk api_server --host 0.0.0.0 --port ${ADK_PORT} --allow-origins=* > /tmp/adk_agent.log 2>&1 &
```

### 2. `Dockerfile.supervisor` (Supervisor Version)
Updated supervisor configuration:
```ini
[program:adk_agent]
command=bash -c "cd adk-agent && adk api_server --host 0.0.0.0 --port ${ADK_PORT} --allow-origins=*"
```

## What This Does

The `--allow-origins=*` flag allows the ADK API server to accept requests from **any origin**, which is useful for:

- ✅ Frontend development (localhost, different ports)
- ✅ Cloud Run deployment (different domains)
- ✅ API testing tools (Postman, curl, etc.)
- ✅ Third-party integrations

## Security Note

⚠️ **For Production**: Consider restricting origins to specific domains instead of `*`:

```bash
# Instead of --allow-origins=*
--allow-origins=https://your-frontend.com,https://api.yourdomain.com
```

## Testing

### Local Testing
```powershell
# Build and run
docker-compose up

# Test ADK endpoint with CORS
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8082/
```

### After Deployment
Your ADK Agent will accept requests from any origin, including:
- Your frontend application
- API testing tools
- Other services

## Next Steps

1. ✅ Rebuild Docker image: `docker build -t galaxy-backend .`
2. ✅ Test locally: `docker-compose up`
3. ✅ Deploy to Cloud Run: `.\deploy-cloud-run.ps1`

## Alternative: Environment Variable

For more flexibility, you could also make this configurable via environment variable:

```bash
# In Dockerfile
--allow-origins=${ADK_ALLOW_ORIGINS:-*}

# Then set in .env or deployment
ADK_ALLOW_ORIGINS=https://your-frontend.com,https://api.yourdomain.com
```

This allows you to:
- Use `*` for development
- Specify exact origins for production
- Change without rebuilding the image
