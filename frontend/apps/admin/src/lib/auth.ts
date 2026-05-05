/**
 * Auth utilities - JWT token handling, redirect logic
 */
import { jwtDecode } from 'jwt-decode';
import { tokenStorage, type AdminUser } from './api';

export interface DecodedToken {
  sub: string;
  exp: number;
  iat: number;
}

// Check if user is authenticated
export const isAuthenticated = (): boolean => {
  const token = tokenStorage.get();
  if (!token) return false;
  
  try {
    const decoded = jwtDecode<DecodedToken>(token);
    const now = Date.now() / 1000;
    
    // Check if token is expired
    if (decoded.exp < now) {
      tokenStorage.remove();
      return false;
    }
    
    return true;
  } catch {
    return false;
  }
};

// Get current user from localStorage
export const getCurrentUser = (): AdminUser | null => {
  if (typeof window === 'undefined') return null;
  
  const userStr = localStorage.getItem('admin_user');
  if (!userStr) return null;
  
  try {
    return JSON.parse(userStr) as AdminUser;
  } catch {
    return null;
  }
};

// Get token expiry time
export const getTokenExpiry = (): Date | null => {
  const token = tokenStorage.get();
  if (!token) return null;
  
  try {
    const decoded = jwtDecode<DecodedToken>(token);
    return new Date(decoded.exp * 1000);
  } catch {
    return null;
  }
};

// Check if token expires soon (within 5 minutes)
export const isTokenExpiringSoon = (): boolean => {
  const expiry = getTokenExpiry();
  if (!expiry) return true;
  
  const now = new Date();
  const fiveMinutes = 5 * 60 * 1000;
  
  return expiry.getTime() - now.getTime() < fiveMinutes;
};

// Redirect to login if not authenticated
export const requireAuth = (): void => {
  if (!isAuthenticated()) {
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
};

// Logout and redirect
export const logout = (): void => {
  tokenStorage.remove();
  if (typeof window !== 'undefined') {
    window.location.href = '/login';
  }
};

// Format bytes to human readable
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

// Format number with commas
export const formatNumber = (num: number): string => {
  return num.toLocaleString();
};

// Format date
export const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('vi-VN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

// Format relative time
export const formatRelativeTime = (dateStr: string): string => {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  
  if (diffMins < 1) return 'Vừa xong';
  if (diffMins < 60) return `${diffMins} phút trước`;
  if (diffHours < 24) return `${diffHours} giờ trước`;
  if (diffDays < 7) return `${diffDays} ngày trước`;
  
  return formatDate(dateStr);
};

// cn utility (classnames)
export const cn = (...classes: (string | undefined | null | false)[]): string => {
  return classes.filter(Boolean).join(' ');
};
