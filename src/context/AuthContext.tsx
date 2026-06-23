import type React from 'react';
import { createContext, useContext, useEffect, useState } from 'react';
import { useToast } from '@/hooks/use-toast';
import { apiFetch, clearAuthTokens, setAuthTokens, getAccessToken } from '@/lib/api';

interface AuthUser {
  uid: string;
  email: string;
  displayName: string;
}

interface AuthContextType {
  currentUser: AuthUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  resetUserPassword: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  // On startup, if we have a stored token, ask the server who we are.
  useEffect(() => {
    const checkSession = async () => {
      if (!getAccessToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const response = await apiFetch('/auth/me');
        if (response.ok) {
          const user = await response.json();
          setCurrentUser(user);
        } else {
          clearAuthTokens();
        }
      } catch (error) {
        console.error('Session check failed:', error);
      } finally {
        setIsLoading(false);
      }
    };

    checkSession();
  }, []);

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to login');
      }
      const data = await response.json();
      setAuthTokens(data.tokens.access_token, data.tokens.refresh_token);
      setCurrentUser(data.user);
      toast({ title: 'Login successful', description: `Welcome back, ${data.user.displayName}!` });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to login';
      toast({ title: 'Error', description: message, variant: 'destructive' });
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, displayName: string) => {
    try {
      setIsLoading(true);
      const response = await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify({ email, password, displayName }),
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to register');
      }
      const data = await response.json();
      setAuthTokens(data.tokens.access_token, data.tokens.refresh_token);
      setCurrentUser(data.user);
      toast({ title: 'Registration successful', description: 'Your account has been created.' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to register';
      toast({ title: 'Error', description: message, variant: 'destructive' });
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      setIsLoading(true);
      await apiFetch('/auth/logout', { method: 'POST' }).catch(() => undefined);
      clearAuthTokens();
      setCurrentUser(null);
      toast({ title: 'Logout successful', description: 'You have been logged out.' });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to logout';
      toast({ title: 'Error', description: message, variant: 'destructive' });
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const resetUserPassword = async (_email: string) => {
    toast({
      title: 'Password reset',
      description: 'Self-serve password reset is not yet wired up — contact admin.',
    });
  };

  const value = { currentUser, isLoading, login, register, logout, resetUserPassword };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
