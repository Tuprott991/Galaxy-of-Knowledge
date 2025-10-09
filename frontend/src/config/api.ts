/**
 * API Configuration
 * Centralizes all API endpoints and URLs
 */

// Backend API URL (FastAPI)
export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ADK Agent URL - Now proxied through FastAPI (same as API_URL)
// In production, ADK runs on port 8082 internally but is proxied through FastAPI on port 8080
export const ADK_URL = import.meta.env.VITE_ADK_URL || API_URL;

// API Endpoints
export const API_ENDPOINTS = {
  // Papers
  papers: `${API_URL}/api/v1/papers`,
  paperById: (id: string) => `${API_URL}/api/v1/papers/${id}`,
  
  // Search
  search: `${API_URL}/api/v1/search`,
  
  // Graph
  graph: `${API_URL}/api/v1/graph`,
  
  // Stats
  stats: `${API_URL}/api/v1/stats`,
  
  // Health
  health: `${API_URL}/health`,
};

// ADK Endpoints - Now proxied through FastAPI
export const ADK_ENDPOINTS = {
  createSession: (userId: string, sessionId: string) => 
    `${ADK_URL}/apps/adk-agent/users/${userId}/sessions/${sessionId}`,
  runSSE: `${ADK_URL}/run_sse`,  // Proxied through FastAPI
};

// Environment info (for debugging)
export const ENV_INFO = {
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
  apiUrl: API_URL,
  adkUrl: ADK_URL,
};

// Log configuration in development
if (ENV_INFO.isDevelopment) {
  console.log('🔧 API Configuration:', ENV_INFO);
}
