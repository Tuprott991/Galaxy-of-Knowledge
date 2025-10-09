# ✅ Frontend Environment Variables - Complete Setup

## What Was Changed

Your frontend was using **hardcoded localhost URLs**. I've updated it to use **environment variables** for proper local/production separation.

## Changes Summary

### Files Created (4):
1. ✅ `.env.local` - Local development config
2. ✅ `.env.production` - Production config template
3. ✅ `.env.example` - Template for developers
4. ✅ `src/config/api.ts` - Centralized API configuration

### Files Updated (2):
1. ✅ `src/api/axiosClient.ts` - Now uses `VITE_API_URL`
2. ✅ `src/components/layout/chatbot.tsx` - Now uses `VITE_ADK_URL`

## Before vs After

### Before ❌
```typescript
// Hardcoded in code
const baseURL = "http://localhost:8000/api";
const API_BASE_URL = "http://localhost:8082";
```

### After ✅
```typescript
// From environment variables
import { API_URL, ADK_URL } from "@/config/api";

// Automatically uses:
// - .env.local in development
// - Vercel env vars in production
```

## Quick Start

### 1. Local Development
```bash
cd frontend
npm run dev
# Uses .env.local → localhost:8000 & localhost:8082
```

### 2. After Backend Deployment
Once you deploy backend to Cloud Run, you'll get a URL like:
```
https://galaxy-backend-xyz-uc.a.run.app
```

### 3. Update Vercel Environment Variables

Go to: https://vercel.com/dashboard → Your Project → Settings → Environment Variables

Add these:
| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://galaxy-backend-xyz-uc.a.run.app` |
| `VITE_ADK_URL` | `https://galaxy-backend-xyz-uc.a.run.app` |

Then **Redeploy** your frontend on Vercel.

## Architecture

```
┌──────────────────────────────────────┐
│  Development (.env.local)            │
│  VITE_API_URL=http://localhost:8000  │
│  VITE_ADK_URL=http://localhost:8082  │
└───────────────┬──────────────────────┘
                │
                ↓
┌──────────────────────────────────────┐
│  src/config/api.ts                   │
│  - API_URL                           │
│  - ADK_URL                           │
│  - API_ENDPOINTS                     │
│  - ADK_ENDPOINTS                     │
└───────────────┬──────────────────────┘
                │
                ↓
┌──────────────────────────────────────┐
│  Application Code                    │
│  - axiosClient.ts                    │
│  - chatbot.tsx                       │
│  - Other components                  │
└──────────────────────────────────────┘
```

## Production Flow

```
1. Deploy Backend to Cloud Run
   ↓
2. Get Cloud Run URL: https://galaxy-backend-xyz.run.app
   ↓
3. Set Vercel Environment Variables
   - VITE_API_URL = Cloud Run URL
   - VITE_ADK_URL = Cloud Run URL
   ↓
4. Redeploy Frontend on Vercel
   ↓
5. ✅ Frontend connects to Cloud Run backend
```

## Important Notes

✅ **Same URL for Both**: ADK Agent runs on the same Cloud Run service  
✅ **Must Start with VITE_**: Only `VITE_*` variables are exposed to client  
✅ **Restart Dev Server**: After changing `.env.local`, restart `npm run dev`  
✅ **Git Safe**: `.env.local` is in `.gitignore`, won't be committed  

## Testing

### Local Test
```bash
cd frontend
npm run dev
# Open http://localhost:5173
# Check console: Should show localhost URLs
```

### Production Test (After Setup)
```bash
# Visit: https://galaxy-of-knowledge-eta.vercel.app
# Open browser console
# Should see no CORS errors
# API calls should go to Cloud Run URL
```

## Deployment Steps

### Step 1: Deploy Backend
```powershell
cd backend
.\deploy-cloud-run.ps1
# Note the Cloud Run URL
```

### Step 2: Update Vercel
1. Go to Vercel dashboard
2. Settings → Environment Variables
3. Add `VITE_API_URL` and `VITE_ADK_URL`
4. Use your Cloud Run URL for both
5. Click "Redeploy" or push to Git

### Step 3: Test
Visit https://galaxy-of-knowledge-eta.vercel.app and verify:
- ✅ No CORS errors
- ✅ Papers load correctly
- ✅ Chatbot works
- ✅ Network tab shows correct URLs

## Full Documentation

See `ENVIRONMENT_SETUP.md` for complete documentation including:
- Detailed configuration options
- Troubleshooting guide
- Advanced usage
- Debugging tips

**Your frontend is now production-ready with proper environment configuration!** 🚀
