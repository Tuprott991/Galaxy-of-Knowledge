# Frontend Environment Configuration Guide

## Overview
Your frontend now uses environment variables for API URLs, making it easy to switch between local development and production.

## Files Created

### 1. `.env.local` - Local Development
```env
VITE_API_URL=http://localhost:8000
VITE_ADK_URL=http://localhost:8082
```
**Usage**: Automatic when running `npm run dev`

### 2. `.env.production` - Production (Vercel)
```env
VITE_API_URL=https://your-backend-cloudrun-url
VITE_ADK_URL=https://your-backend-cloudrun-url
```
**Usage**: Automatic when running `npm run build`

### 3. `.env.example` - Template
Copy this to `.env.local` for new developers.

### 4. `src/config/api.ts` - API Configuration
Centralizes all API endpoints and URLs.

## Files Updated

### ✅ `src/api/axiosClient.ts`
**Before**:
```typescript
baseURL: "http://localhost:8000/api",
```

**After**:
```typescript
import { API_URL } from "@/config/api";

const axiosClient = axios.create({
  baseURL: `${API_URL}/api`,
  // ...
});
```

### ✅ `src/components/layout/chatbot.tsx`
**Before**:
```typescript
const API_BASE_URL = "http://localhost:8082";
```

**After**:
```typescript
import { ADK_ENDPOINTS } from "@/config/api";

// Usage:
fetch(ADK_ENDPOINTS.createSession(USER_ID, sessionId))
fetch(ADK_ENDPOINTS.runSSE)
```

## How It Works

### Vite Environment Variables
Vite automatically loads environment variables based on the mode:

1. **Development** (`npm run dev`):
   - Loads `.env.local`
   - Uses `http://localhost:8000` and `http://localhost:8082`

2. **Production** (`npm run build`):
   - Loads `.env.production`
   - Uses your Cloud Run URLs

### Accessing Variables
```typescript
// In any TypeScript/React file:
const apiUrl = import.meta.env.VITE_API_URL;
const adkUrl = import.meta.env.VITE_ADK_URL;
```

**Important**: Variables must be prefixed with `VITE_` to be exposed to the client!

## Setup for Local Development

### 1. Create `.env.local`
```bash
cd frontend
```

Create `.env.local` with:
```env
VITE_API_URL=http://localhost:8000
VITE_ADK_URL=http://localhost:8082
```

### 2. Start Development Server
```bash
npm run dev
```

The frontend will connect to:
- FastAPI: `http://localhost:8000`
- ADK Agent: `http://localhost:8082`

## Setup for Production (Vercel)

### Option 1: Using Vercel Dashboard (Recommended)

1. Go to: https://vercel.com/dashboard
2. Select your project: `galaxy-of-knowledge`
3. Go to **Settings** → **Environment Variables**
4. Add these variables:

| Name | Value | Environment |
|------|-------|-------------|
| `VITE_API_URL` | `https://your-backend-cloudrun-url` | Production |
| `VITE_ADK_URL` | `https://your-backend-cloudrun-url` | Production |

5. **Redeploy** your frontend

### Option 2: Using Vercel CLI

```bash
# Install Vercel CLI
npm i -g vercel

# Add environment variables
vercel env add VITE_API_URL production
# Enter: https://your-backend-cloudrun-url

vercel env add VITE_ADK_URL production
# Enter: https://your-backend-cloudrun-url

# Redeploy
vercel --prod
```

### After Backend Deployment

Once you deploy your backend to Cloud Run, you'll get a URL like:
```
https://galaxy-backend-xyz-uc.a.run.app
```

Update Vercel environment variables to use this URL:
```env
VITE_API_URL=https://galaxy-backend-xyz-uc.a.run.app
VITE_ADK_URL=https://galaxy-backend-xyz-uc.a.run.app
```

**Note**: ADK Agent runs on the same Cloud Run service (port 8082 internally, but accessed through the main URL).

## Configuration Hierarchy

```
┌─────────────────────────────────────┐
│  import.meta.env.VITE_API_URL       │
│         ↓                            │
│  src/config/api.ts                   │
│    ├─ API_URL                        │
│    ├─ ADK_URL                        │
│    └─ API_ENDPOINTS                  │
│         ↓                            │
│  Application Code                    │
│    ├─ axiosClient.ts                 │
│    ├─ chatbot.tsx                    │
│    └─ Other components               │
└─────────────────────────────────────┘
```

## Using the API Config

### Recommended Way
```typescript
import { API_ENDPOINTS, ADK_ENDPOINTS } from "@/config/api";

// Fetch papers
fetch(API_ENDPOINTS.papers)

// Fetch specific paper
fetch(API_ENDPOINTS.paperById("PMC123456"))

// ADK session
fetch(ADK_ENDPOINTS.createSession(userId, sessionId))

// ADK streaming
fetch(ADK_ENDPOINTS.runSSE)
```

### Direct Access (Not Recommended)
```typescript
// Works, but harder to maintain
const url = `${import.meta.env.VITE_API_URL}/api/v1/papers`;
```

## Debugging Environment Variables

### Check Current Configuration
Open browser console on your app:
```javascript
// Will show current API configuration in development
// Check the console when app loads
```

### Manual Check
```typescript
console.log('API URL:', import.meta.env.VITE_API_URL);
console.log('ADK URL:', import.meta.env.VITE_ADK_URL);
console.log('Mode:', import.meta.env.MODE);
console.log('Dev:', import.meta.env.DEV);
console.log('Prod:', import.meta.env.PROD);
```

## Troubleshooting

### Variables are `undefined`

**Problem**: `import.meta.env.VITE_API_URL` is `undefined`

**Solutions**:
1. Make sure variable starts with `VITE_`
2. Restart dev server after creating `.env.local`
3. Check `.env.local` is in the `frontend/` directory
4. Verify no syntax errors in `.env.local`

### CORS Errors in Production

**Problem**: CORS errors when frontend calls backend

**Solutions**:
1. Check backend CORS configuration allows your Vercel URL
2. Verify backend URL in Vercel env vars is correct
3. Ensure URL has `https://` (not `http://`)
4. Check URL doesn't have trailing slash

### Different Behavior Local vs Production

**Problem**: Works locally but not in production

**Solutions**:
1. Check Vercel environment variables are set correctly
2. Verify backend is deployed and accessible
3. Check browser console for actual URLs being called
4. Test backend URL directly: `https://your-backend-url/health`

## Complete Deployment Checklist

### Local Testing
- [ ] `.env.local` created with localhost URLs
- [ ] `npm run dev` starts successfully
- [ ] Can fetch papers from local backend
- [ ] Chatbot connects to local ADK agent
- [ ] No console errors

### Backend Deployment
- [ ] Deploy backend to Cloud Run
- [ ] Copy Cloud Run URL
- [ ] Test: `curl https://your-backend-url/health`
- [ ] Verify CORS allows Vercel domain

### Frontend Deployment
- [ ] Update `.env.production` with Cloud Run URL
- [ ] Set Vercel environment variables:
  - [ ] `VITE_API_URL`
  - [ ] `VITE_ADK_URL`
- [ ] Push to Git (triggers Vercel deployment)
- [ ] Or manually: `vercel --prod`
- [ ] Test production site
- [ ] Check browser console for errors

## Git Configuration

Add to `.gitignore` (already done):
```gitignore
# Environment files
.env.local
.env.production.local
.env.development.local

# Keep these for reference
!.env.example
!.env.production
```

## Summary

✅ **Before**: Hardcoded URLs in code  
✅ **After**: Environment variables for flexibility  

✅ **Local Dev**: Uses `.env.local` → localhost  
✅ **Production**: Uses Vercel env vars → Cloud Run  

✅ **Centralized**: All endpoints in `config/api.ts`  
✅ **Type-safe**: TypeScript configuration  

## Next Steps

1. **Test Locally**:
   ```bash
   cd frontend
   npm run dev
   # Verify it connects to localhost:8000 and localhost:8082
   ```

2. **Deploy Backend**:
   ```bash
   cd backend
   .\deploy-cloud-run.ps1
   # Note the Cloud Run URL
   ```

3. **Update Vercel**:
   - Add environment variables with Cloud Run URL
   - Redeploy frontend

4. **Test Production**:
   - Visit https://galaxy-of-knowledge-eta.vercel.app
   - Check if API calls work
   - Verify no CORS errors

**Your frontend is now properly configured for both local and production environments!** 🎉
