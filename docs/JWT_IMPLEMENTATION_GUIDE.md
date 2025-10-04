# JWT Authentication Implementation Guide

> A complete guide to implementing JWT authentication with Access + Refresh Token mechanism, based on the Midas Touch project implementation.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Backend Implementation (Python/FastAPI)](#backend-implementation-pythonfastapi)
- [Frontend Implementation (TypeScript/Next.js)](#frontend-implementation-typescriptnextjs)
- [Complete Flow Diagrams](#complete-flow-diagrams)
- [Environment Variables](#environment-variables)
- [Security Best Practices](#security-best-practices)
- [Implementation Checklist](#implementation-checklist)
- [File Reference](#file-reference)

---

## Architecture Overview

This implementation uses a **dual-token mechanism**:

- **Access Token**: Short-lived (30 minutes), used for API authentication
- **Refresh Token**: Long-lived (7 days), used to obtain new access tokens

### Key Features
- ✅ Automatic token refresh before expiration
- ✅ Concurrent refresh protection
- ✅ Role-based access control (user, admin)
- ✅ Automatic logout on authentication failure
- ✅ Buffer time mechanism (proactive token refresh)
- ✅ localStorage persistence

### Token Flow
```
Registration/Login → Get token pair → Store in localStorage
                                          ↓
                                    Auto-attach to API requests
                                          ↓
                                    Token expired? → Auto-refresh → Continue
                                          ↓
                                    Refresh failed → Clear tokens → Redirect to login
```

---

## Backend Implementation (Python/FastAPI)

### File Structure
```
backend/
├── app/
│   ├── security/
│   │   ├── jwt_auth.py          # JWT core logic
│   │   └── auth.py              # Authentication middleware
│   └── routes/
│       ├── users.py             # Auth routes (login, register, refresh)
│       ├── projects.py          # Protected routes example
│       └── admin.py             # Admin-only routes example
```

### 1. JWT Core Module (`jwt_auth.py`)

```python
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, Any
import jwt
from fastapi import HTTPException, status

# Configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 120 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days

def get_jwt_secret() -> bytes:
    """Get JWT secret key from environment variable"""
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise ValueError("JWT_SECRET_KEY environment variable not set")
    return base64.b64decode(secret.encode())

class JWTManager:
    def __init__(self):
        self.secret_key = get_jwt_secret()
        self.algorithm = JWT_ALGORITHM

    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create access token with user data"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "display_name": user_data.get("display_name", ""),
            "role": user_data.get("role", "user"),
            "token_type": "access",
            "iat": now,        # issued at
            "exp": expire      # expiration time
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token"""
        now = datetime.utcnow()
        expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "user_id": user_id,
            "token_type": "refresh",
            "iat": now,
            "exp": expire
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Verify token type
            if payload.get("token_type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

# Global instance
jwt_manager = JWTManager()

def create_token_pair(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create both access and refresh tokens"""
    access_token = jwt_manager.create_access_token(user_data)
    refresh_token = jwt_manager.create_refresh_token(user_data["user_id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60  # in seconds
    }

def verify_access_token(token: str) -> Dict[str, Any]:
    """Verify access token"""
    return jwt_manager.verify_token(token, "access")

def refresh_token_pair(refresh_token: str, user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Refresh access token using refresh token"""
    # Verify refresh token
    jwt_manager.verify_token(refresh_token, "refresh")

    # Create new access token
    new_access_token = jwt_manager.create_access_token(user_data)

    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,  # Reuse existing refresh token
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }
```

### 2. Authentication Middleware (`auth.py`)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from .jwt_auth import verify_access_token

# HTTPBearer automatically extracts token from Authorization: Bearer {token}
security = HTTPBearer()

class CurrentUser(BaseModel):
    """Current authenticated user data"""
    user_id: str
    email: str
    display_name: str
    role: str

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> CurrentUser:
    """Get current authenticated user from JWT token"""
    try:
        token = credentials.credentials
        user_data = verify_access_token(token)

        return CurrentUser(
            user_id=user_data["user_id"],
            email=user_data["email"],
            display_name=user_data["display_name"],
            role=user_data["role"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

def require_user(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency that requires user authentication"""
    return current_user

def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Dependency that requires admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
```

### 3. Authentication Routes (`users.py`)

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.security.jwt_auth import create_token_pair, refresh_token_pair, jwt_manager
from app.security.auth import require_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["authentication"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class ApiResponse(BaseModel):
    statusCode: int
    body: dict

@router.post("/register", response_model=ApiResponse)
async def register(request: RegisterRequest):
    """Register new user and return JWT tokens"""
    # 1. Create user in your database (Supabase, PostgreSQL, etc.)
    # user = create_user_in_database(request.email, request.password, request.display_name)

    # Example user data (replace with your actual user creation logic)
    user_data = {
        "user_id": "user_123",  # From database
        "email": request.email,
        "display_name": request.display_name,
        "role": "user"
    }

    # 2. Create JWT token pair
    tokens = create_token_pair(user_data)

    return ApiResponse(
        statusCode=200,
        body={**user_data, **tokens}
    )

@router.post("/login", response_model=ApiResponse)
async def login(request: LoginRequest):
    """Login user and return JWT tokens"""
    # 1. Verify credentials (Supabase Auth, bcrypt, etc.)
    # user = verify_user_credentials(request.email, request.password)
    # if not user:
    #     raise HTTPException(status_code=401, detail="Invalid credentials")

    # Example user data (replace with your actual authentication logic)
    user_data = {
        "user_id": "user_123",
        "email": request.email,
        "display_name": "John Doe",
        "role": "user"
    }

    # 2. Create JWT token pair
    tokens = create_token_pair(user_data)

    return ApiResponse(
        statusCode=200,
        body={**user_data, **tokens}
    )

@router.post("/refresh", response_model=ApiResponse)
async def refresh_tokens(request: RefreshTokenRequest):
    """Refresh access token using refresh token"""
    # 1. Verify refresh token
    refresh_payload = jwt_manager.verify_token(request.refresh_token, "refresh")
    user_id = refresh_payload["user_id"]

    # 2. Get latest user data from database
    # user_info = get_user_from_database(user_id)
    # if not user_info:
    #     raise HTTPException(status_code=401, detail="User not found")

    # Example user data (replace with your database query)
    user_data = {
        "user_id": user_id,
        "email": "user@example.com",
        "display_name": "John Doe",
        "role": "user"
    }

    # 3. Create new token pair
    tokens = refresh_token_pair(request.refresh_token, user_data)

    return ApiResponse(
        statusCode=200,
        body={**user_data, **tokens}
    )

@router.get("/me", response_model=ApiResponse)
async def get_current_user_info(current_user: CurrentUser = Depends(require_user)):
    """Get current user information (requires authentication)"""
    return ApiResponse(
        statusCode=200,
        body={
            "user_id": current_user.user_id,
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role
        }
    )
```

### 4. Protected Routes Example

```python
from fastapi import APIRouter, Depends
from app.security.auth import require_user, require_admin, CurrentUser

router = APIRouter(prefix="/projects", tags=["projects"])

@router.get("/")
async def get_user_projects(current_user: CurrentUser = Depends(require_user)):
    """Get projects for authenticated user"""
    # Access user info: current_user.user_id, current_user.email, etc.
    projects = fetch_user_projects(current_user.user_id)
    return {"projects": projects}

@router.post("/")
async def create_project(
    project_data: dict,
    current_user: CurrentUser = Depends(require_user)
):
    """Create new project (authenticated users only)"""
    new_project = create_project_in_db(current_user.user_id, project_data)
    return {"project": new_project}

# Admin-only route
@router.get("/admin/all")
async def get_all_projects(current_admin: CurrentUser = Depends(require_admin)):
    """Get all projects (admin only)"""
    all_projects = fetch_all_projects()
    return {"projects": all_projects}
```

---

## Frontend Implementation (TypeScript/Next.js)

### File Structure
```
frontend/
├── lib/
│   ├── auth.ts              # JWT Manager
│   ├── http.ts              # HTTP client with auto JWT
│   └── api.ts               # API service layer
├── stores/
│   └── authStore.ts         # Auth state management (Zustand)
└── components/
    └── AuthPage.tsx         # Login/Register UI
```

### 1. JWT Manager (`lib/auth.ts`)

```typescript
export interface TokenData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  expires_at: number;  // Calculated expiration timestamp
}

class JWTManager {
  private static instance: JWTManager;
  private tokens: TokenData | null = null;
  private isRefreshing = false;
  private refreshPromise: Promise<string | null> | null = null;

  private constructor() {
    this.loadTokensFromStorage();
  }

  public static getInstance(): JWTManager {
    if (!JWTManager.instance) {
      JWTManager.instance = new JWTManager();
    }
    return JWTManager.instance;
  }

  /**
   * Load tokens from localStorage
   */
  private loadTokensFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem('jwt_tokens');
      if (stored) {
        this.tokens = JSON.parse(stored);
      }
    } catch (error) {
      console.error('Failed to load tokens from storage:', error);
      this.clearTokens();
    }
  }

  /**
   * Calculate buffer time for proactive token refresh
   * Short tokens: 25% buffer, min 5 seconds
   * Long tokens: 10% buffer, max 5 minutes
   */
  private calculateBufferTime(expiresIn: number): number {
    const fiveMinutes = 5 * 60;

    if (expiresIn < fiveMinutes) {
      return Math.max(expiresIn * 0.25, 5);
    } else {
      return Math.min(Math.max(expiresIn * 0.1, 10), 300);
    }
  }

  /**
   * Set tokens and save to localStorage
   */
  public setTokens(tokenData: Omit<TokenData, 'expires_at'>): void {
    const bufferTime = this.calculateBufferTime(tokenData.expires_in);
    const expiresAt = Date.now() + (tokenData.expires_in * 1000) - (bufferTime * 1000);

    this.tokens = { ...tokenData, expires_at: expiresAt };

    if (typeof window !== 'undefined') {
      localStorage.setItem('jwt_tokens', JSON.stringify(this.tokens));
    }
  }

  /**
   * Get current access token (without checking expiration)
   */
  public getAccessToken(): string | null {
    return this.tokens?.access_token || null;
  }

  /**
   * Get current refresh token
   */
  public getRefreshToken(): string | null {
    return this.tokens?.refresh_token || null;
  }

  /**
   * Check if access token is expired (with buffer time)
   */
  public isTokenExpired(): boolean {
    if (!this.tokens) return true;
    const now = Date.now();
    return now >= this.tokens.expires_at;
  }

  /**
   * Clear all tokens
   */
  public clearTokens(): void {
    this.tokens = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('jwt_tokens');
    }
  }

  /**
   * Refresh access token using refresh token
   * Prevents concurrent refresh requests
   */
  public async refreshAccessToken(): Promise<string | null> {
    // Prevent concurrent refreshes
    if (this.isRefreshing && this.refreshPromise) {
      return await this.refreshPromise;
    }

    if (!this.tokens?.refresh_token) {
      return null;
    }

    this.isRefreshing = true;
    this.refreshPromise = this.performTokenRefresh();

    try {
      return await this.refreshPromise;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  /**
   * Perform the actual token refresh API call
   */
  private async performTokenRefresh(): Promise<string | null> {
    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL;
      const response = await fetch(`${backendUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          refresh_token: this.tokens!.refresh_token
        })
      });

      if (!response.ok) {
        this.clearTokens();
        throw new Error('Token refresh failed');
      }

      const data = await response.json();

      // Update tokens
      this.setTokens({
        access_token: data.body.access_token,
        refresh_token: data.body.refresh_token || this.tokens!.refresh_token,
        token_type: data.body.token_type || 'bearer',
        expires_in: data.body.expires_in
      });

      return data.body.access_token;
    } catch (error) {
      this.clearTokens();
      throw error;
    }
  }

  /**
   * Get valid access token (auto-refresh if expired)
   */
  public async getValidAccessToken(): Promise<string | null> {
    if (!this.tokens) return null;

    if (!this.isTokenExpired()) {
      return this.tokens.access_token;
    }

    // Token expired, refresh it
    return await this.refreshAccessToken();
  }
}

// Export singleton instance
export const jwtManager = JWTManager.getInstance();
```

### 2. HTTP Client with Auto JWT (`lib/http.ts`)

```typescript
import { jwtManager } from './auth';

export interface RequestOptions extends RequestInit {
  skipAuth?: boolean;   // Skip JWT authentication
  skipRetry?: boolean;  // Skip retry on 401
}

/**
 * Handle authentication failure
 */
function handleAuthFailure(): void {
  // Clear JWT tokens
  jwtManager.clearTokens();

  // Clear auth store
  try {
    const { default: useAuthStore } = require('@/stores/authStore');
    const authStore = useAuthStore.getState();
    authStore.logout();
  } catch (error) {
    console.warn('Could not access auth store:', error);
  }

  // Redirect to login
  if (typeof window !== 'undefined') {
    const currentPath = window.location.pathname;

    if (!currentPath.includes('/login') && !currentPath.includes('/register')) {
      window.location.href = '/login?redirect=' + encodeURIComponent(currentPath);
    }
  }
}

/**
 * Fetch with automatic JWT attachment
 */
export async function apiFetch(url: string, options: RequestOptions = {}): Promise<Response> {
  const { skipAuth = false, skipRetry = false, ...fetchOptions } = options;
  const headers = new Headers(fetchOptions.headers);

  // Add JWT authentication (unless skipAuth=true)
  if (!skipAuth) {
    try {
      // Check if token is expired
      if (jwtManager.isTokenExpired()) {
        // Auto-refresh token
        const newToken = await jwtManager.refreshAccessToken();
        if (!newToken) {
          handleAuthFailure();
          throw new Error('Authentication failed');
        }
        headers.set('Authorization', `Bearer ${newToken}`);
      } else {
        const token = jwtManager.getAccessToken();
        if (token) {
          headers.set('Authorization', `Bearer ${token}`);
        }
      }
    } catch (error) {
      if (!skipRetry) {
        handleAuthFailure();
      }
      throw error;
    }
  }

  const response = await fetch(url, { ...fetchOptions, headers });

  // Handle 401 Unauthorized
  if (response.status === 401 && !skipAuth && !skipRetry) {
    handleAuthFailure();
    throw new Error('Unauthorized - please login again');
  }

  return response;
}

/**
 * Generic API request with JSON response
 */
export async function apiRequest<T>(url: string, options?: RequestOptions): Promise<T> {
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_API_URL;
  const fullUrl = url.startsWith('http') ? url : `${backendUrl}${url}`;

  const headers = new Headers(options?.headers);
  headers.set('Content-Type', 'application/json');
  headers.set('Accept', 'application/json');

  const response = await apiFetch(fullUrl, {
    ...options,
    headers
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error: ${response.status} ${errorText}`);
  }

  return await response.json();
}

/**
 * Convenience methods
 */
export async function apiGet<T>(url: string, options?: RequestOptions): Promise<T> {
  return apiRequest<T>(url, { ...options, method: 'GET' });
}

export async function apiPost<T>(url: string, body?: any, options?: RequestOptions): Promise<T> {
  return apiRequest<T>(url, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined
  });
}

export async function apiPut<T>(url: string, body?: any, options?: RequestOptions): Promise<T> {
  return apiRequest<T>(url, {
    ...options,
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined
  });
}

export async function apiDelete<T>(url: string, options?: RequestOptions): Promise<T> {
  return apiRequest<T>(url, { ...options, method: 'DELETE' });
}
```

### 3. API Service Layer (`lib/api.ts`)

```typescript
import { apiPost } from './http';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface ApiResponse<T = any> {
  statusCode: number;
  body: T;
}

export interface AuthResponse {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Login user
 */
export async function loginUser(data: LoginRequest): Promise<ApiResponse<AuthResponse>> {
  return apiPost<ApiResponse<AuthResponse>>('/auth/login', data, { skipAuth: true });
}

/**
 * Register new user
 */
export async function registerUser(data: RegisterRequest): Promise<ApiResponse<AuthResponse>> {
  return apiPost<ApiResponse<AuthResponse>>('/auth/register', data, { skipAuth: true });
}

/**
 * Get current user info
 */
export async function getCurrentUser(): Promise<ApiResponse<any>> {
  return apiPost<ApiResponse<any>>('/auth/me');
}
```

### 4. Auth State Management (`stores/authStore.ts`)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { jwtManager } from '@/lib/auth';
import { loginUser, registerUser, LoginRequest, RegisterRequest } from '@/lib/api';

export interface User {
  user_id: string;
  email: string;
  display_name: string;
  role: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (loginData: LoginRequest) => Promise<void>;
  register: (registerData: RegisterRequest) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (loginData: LoginRequest) => {
        try {
          set({ isLoading: true, error: null });

          // Call login API
          const response = await loginUser(loginData);

          const userData: User = {
            user_id: response.body.user_id,
            email: response.body.email,
            display_name: response.body.display_name,
            role: response.body.role,
          };

          // Store JWT tokens
          jwtManager.setTokens({
            access_token: response.body.access_token,
            refresh_token: response.body.refresh_token,
            token_type: response.body.token_type || 'bearer',
            expires_in: response.body.expires_in
          });

          // Update auth state
          set({
            user: userData,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });

        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || "Login failed",
            user: null,
            isAuthenticated: false
          });
          throw error;
        }
      },

      register: async (registerData: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null });

          // Call register API
          const response = await registerUser(registerData);

          const userData: User = {
            user_id: response.body.user_id,
            email: response.body.email,
            display_name: response.body.display_name,
            role: response.body.role,
          };

          // Store JWT tokens
          jwtManager.setTokens({
            access_token: response.body.access_token,
            refresh_token: response.body.refresh_token,
            token_type: response.body.token_type || 'bearer',
            expires_in: response.body.expires_in
          });

          set({
            user: userData,
            isAuthenticated: true,
            isLoading: false,
            error: null
          });

        } catch (error: any) {
          set({
            isLoading: false,
            error: error.message || "Registration failed",
            user: null,
            isAuthenticated: false
          });
          throw error;
        }
      },

      logout: () => {
        // Clear JWT tokens
        jwtManager.clearTokens();

        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "auth-store",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;
```

### 5. Usage Examples

#### In React Components

```typescript
'use client';

import { useEffect } from 'react';
import useAuthStore from '@/stores/authStore';
import { apiGet, apiPost } from '@/lib/http';

export default function DashboardPage() {
  const { user, isAuthenticated, logout } = useAuthStore();

  useEffect(() => {
    // Fetch data with automatic JWT
    const fetchProjects = async () => {
      try {
        const projects = await apiGet('/projects/');
        console.log(projects);
      } catch (error) {
        console.error('Failed to fetch projects:', error);
      }
    };

    if (isAuthenticated) {
      fetchProjects();
    }
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return <div>Please login</div>;
  }

  return (
    <div>
      <h1>Welcome, {user?.display_name}</h1>
      <button onClick={logout}>Logout</button>
    </div>
  );
}
```

#### Login Component

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/stores/authStore';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading, error } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      await login({ email, password });
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <button type="submit" disabled={isLoading}>
        {isLoading ? 'Logging in...' : 'Login'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
```

---

## Complete Flow Diagrams

### 1. Registration Flow
```
User fills registration form
    ↓
POST /auth/register (skipAuth: true)
    ↓
Backend:
  - Create user in database
  - Generate token pair (create_token_pair)
    ↓
Response: { user_id, email, display_name, role, access_token, refresh_token, expires_in }
    ↓
Frontend:
  - jwtManager.setTokens() → Save to localStorage
  - authStore.setState() → Update auth state
  - router.push('/dashboard') → Redirect
```

### 2. Login Flow
```
User fills login form
    ↓
POST /auth/login (skipAuth: true)
    ↓
Backend:
  - Verify credentials
  - Generate token pair
    ↓
Response: { user_id, email, display_name, role, access_token, refresh_token, expires_in }
    ↓
Frontend:
  - Save tokens to localStorage
  - Update authStore
  - Redirect to dashboard
```

### 3. API Request Flow
```
Component calls API (e.g., apiGet('/projects/'))
    ↓
apiFetch() checks authentication:
  - jwtManager.isTokenExpired()
    ↓
Token NOT expired:
  - Attach Authorization: Bearer {access_token}
  - Send request
    ↓
Token expired:
  - jwtManager.refreshAccessToken()
  - POST /auth/refresh { refresh_token }
  - Get new access_token
  - Attach new token to header
  - Send request
    ↓
Backend:
  - HTTPBearer() extracts token
  - get_current_user() verifies token
  - verify_access_token() decodes & validates
  - Returns CurrentUser object
    ↓
Route handler uses current_user.user_id for business logic
    ↓
Return API response
```

### 4. Token Refresh Flow
```
Frontend detects access_token expiring soon
    ↓
jwtManager.refreshAccessToken() initiated
  - Prevent concurrent refresh (isRefreshing flag)
    ↓
POST /auth/refresh
body: { refresh_token: "xxx" }
    ↓
Backend:
  - verify_token(refresh_token, "refresh")
  - Fetch latest user data from database
  - Generate new access_token
  - Return new token pair
    ↓
Frontend:
  - setTokens() → Update localStorage
  - Return new access_token to requester
```

### 5. Logout Flow
```
User clicks logout button
    ↓
authStore.logout() executes:
  - jwtManager.clearTokens() → Remove from localStorage
  - setState({ user: null, isAuthenticated: false })
    ↓
Redirect to /login
```

### 6. 401 Error Handling Flow
```
API request returns 401 Unauthorized
    ↓
apiFetch() detects response.status === 401
    ↓
handleAuthFailure() executes:
  - jwtManager.clearTokens()
  - authStore.logout()
  - window.location.href = '/login?redirect={current_path}'
    ↓
User redirected to login page, can return after login
```

---

## Environment Variables

### Backend `.env`

```bash
# JWT Configuration (REQUIRED!)
JWT_SECRET_KEY="your-base64-encoded-secret-key"

# Database & Auth (example with Supabase)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
SUPABASE_SERVICE_KEY="your-service-key"

# Optional: AI services
OPENAI_API_KEY="sk-..."
```

#### Generate JWT Secret Key

```python
import base64
import secrets

# Generate 256-bit random secret
secret = secrets.token_bytes(32)
base64_secret = base64.b64encode(secret).decode()
print(base64_secret)  # Use this value in .env
```

Or using command line:
```bash
python -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

### Frontend `.env`

```bash
# Backend API URL
NEXT_PUBLIC_BACKEND_API_URL="http://localhost:8000"
# Or production: https://api.yourdomain.com
```

---

## Security Best Practices

### Token Security

1. **Short-lived Access Tokens**: 30 minutes expiration reduces hijacking risk
2. **Long-lived Refresh Tokens**: 7 days for better UX
3. **Token Type Validation**: Always verify `token_type` field
4. **Base64 Encoded Secret**: Increases secret key complexity
5. **HS256 Algorithm**: Symmetric encryption with good performance

### Frontend Security

1. **localStorage Storage**: Client-side only (consider httpOnly cookies for production)
2. **Automatic Token Refresh**: Reduces re-authentication frequency
3. **Concurrent Refresh Protection**: Prevents multiple simultaneous refresh requests
4. **Buffer Time Mechanism**: Proactive refresh before expiration
5. **Auto-logout on 401**: Clear tokens and redirect when unauthorized

### Backend Security

1. **HTTPBearer Standard**: Standardized Bearer token handling
2. **Dependency Injection**: FastAPI's `Depends()` ensures verification on every request
3. **Role-based Access Control**: `require_admin` enforces admin-only routes
4. **Token Expiration**: Automatic `exp` field validation
5. **Unified Exception Handling**: Consistent `HTTPException` responses

### Production Recommendations

1. **Use HTTPS**: Always use SSL/TLS in production
2. **HttpOnly Cookies**: Consider using httpOnly cookies instead of localStorage for XSS protection
3. **CORS Configuration**: Properly configure CORS origins
4. **Rate Limiting**: Implement rate limiting on auth endpoints
5. **Refresh Token Rotation**: Rotate refresh tokens on each use
6. **Token Blacklist**: Implement token revocation for logout
7. **Secure Secret Storage**: Use environment variables or secret management services

---

## Implementation Checklist

### Backend Setup

- [ ] Install dependencies: `pip install python-jose[cryptography] passlib[bcrypt]`
- [ ] Create `security/jwt_auth.py` with JWT core logic
- [ ] Create `security/auth.py` with authentication middleware
- [ ] Create `routes/users.py` with auth endpoints (register, login, refresh)
- [ ] Generate JWT secret key and add to `.env`
- [ ] Set up user database (Supabase, PostgreSQL, etc.)
- [ ] Implement user registration logic
- [ ] Implement user login/authentication logic
- [ ] Test token generation and verification
- [ ] Add protected routes using `Depends(require_user)`
- [ ] Test token refresh mechanism

### Frontend Setup

- [ ] Install dependencies: `npm install zustand`
- [ ] Create `lib/auth.ts` with JWTManager class
- [ ] Create `lib/http.ts` with auto-JWT HTTP client
- [ ] Create `lib/api.ts` with API service functions
- [ ] Create `stores/authStore.ts` with Zustand store
- [ ] Add `NEXT_PUBLIC_BACKEND_API_URL` to `.env`
- [ ] Create login/register pages
- [ ] Implement login form with authStore.login()
- [ ] Implement register form with authStore.register()
- [ ] Add logout functionality
- [ ] Test automatic token refresh
- [ ] Test 401 error handling and redirect
- [ ] Add protected routes/pages

### Testing

- [ ] Test registration flow end-to-end
- [ ] Test login flow end-to-end
- [ ] Test protected API calls with valid token
- [ ] Test token expiration and auto-refresh
- [ ] Test refresh token mechanism
- [ ] Test logout clears tokens
- [ ] Test 401 redirects to login
- [ ] Test concurrent API requests don't cause multiple refreshes
- [ ] Test role-based access (user vs admin)
- [ ] Test expired refresh token behavior

---

## File Reference

### Backend Files (from Midas Touch project)

| File | Path | Description |
|------|------|-------------|
| JWT Core | `app/security/jwt_auth.py` | Token generation, verification, refresh logic |
| Auth Middleware | `app/security/auth.py` | HTTPBearer, get_current_user, require_user, require_admin |
| Auth Routes | `app/routes/users.py` | Register, login, refresh endpoints |
| Protected Routes | `app/routes/projects.py` | Example of protected user routes |
| Admin Routes | `app/routes/admin.py` | Example of admin-only routes |
| Environment | `.env` | JWT_SECRET_KEY and other configs |

### Frontend Files (from Midas Touch project)

| File | Path | Description |
|------|------|-------------|
| JWT Manager | `lib/auth.ts` | Token storage, refresh, expiration checks |
| HTTP Client | `lib/http.ts` | Auto-attach JWT, handle 401 errors |
| API Service | `lib/api.ts` | API wrapper functions |
| Auth Store | `stores/authStore.ts` | Zustand state management |
| Auth UI | `components/AuthPage.tsx` | Login/Register component |
| Login Page | `app/login/page.tsx` | Login page route |
| Register Page | `app/register/page.tsx` | Register page route |
| Environment | `.env` | NEXT_PUBLIC_BACKEND_API_URL |

---

## Quick Start

### 1. Backend (FastAPI)

```bash
# Install dependencies
pip install fastapi python-jose[cryptography] passlib[bcrypt]

# Generate JWT secret
python -c "import base64, secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"

# Add to .env
echo "JWT_SECRET_KEY=<generated-secret>" >> .env

# Create security modules
# Copy jwt_auth.py and auth.py code from this guide

# Create auth routes
# Copy users.py code from this guide

# Run server
uvicorn main:app --reload
```

### 2. Frontend (Next.js)

```bash
# Install dependencies
npm install zustand

# Add to .env
echo "NEXT_PUBLIC_BACKEND_API_URL=http://localhost:8000" >> .env.local

# Create JWT modules
# Copy auth.ts, http.ts, api.ts, authStore.ts code from this guide

# Create login page
# Copy login page code from this guide

# Run dev server
npm run dev
```

### 3. Test It

```bash
# 1. Register a user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123","display_name":"Test User"}'

# 2. Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'

# 3. Use access token
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <access_token>"

# 4. Refresh token
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

---

## Troubleshooting

### Common Issues

1. **"JWT_SECRET_KEY environment variable not set"**
   - Ensure `.env` file exists and contains `JWT_SECRET_KEY`
   - Make sure it's base64 encoded
   - Restart the backend server after adding

2. **"Token has expired"**
   - Check system clock is synchronized
   - Verify `ACCESS_TOKEN_EXPIRE_MINUTES` configuration
   - Frontend should auto-refresh before expiration

3. **"Invalid token type"**
   - Ensure you're using access token for API requests
   - Use refresh token only for `/auth/refresh` endpoint

4. **"CORS error" in browser**
   - Add CORS middleware to FastAPI
   - Allow your frontend origin in CORS settings

5. **Tokens not persisting after refresh**
   - Check localStorage in browser DevTools
   - Ensure `jwtManager.setTokens()` is called after login
   - Verify zustand persist configuration

---

## Additional Resources

### Dependencies

**Backend (Python):**
```bash
fastapi>=0.104.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
```

**Frontend (TypeScript):**
```bash
zustand>=4.4.0
```

### Related Documentation

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io](https://jwt.io/)
- [Zustand](https://github.com/pmndrs/zustand)
- [Next.js Authentication](https://nextjs.org/docs/authentication)

---

## License

This implementation guide is based on the Midas Touch project. Feel free to use and modify for your own projects.

---

**Last Updated**: 2025-10-04
