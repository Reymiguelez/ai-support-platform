import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api } from '@/services/api';
import type { User, AuthTokens } from '@/types/auth';

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (data: Partial<User>) => Promise<void>;
}

interface RegisterData {
  email: string;
  username: string;
  full_name: string;
  password: string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    initAuth();
  }, []);

  const initAuth = async () => {
    const storedTokens = localStorage.getItem('auth_tokens');
    const storedUser = localStorage.getItem('auth_user');

    if (storedTokens && storedUser) {
      try {
        const parsedTokens = JSON.parse(storedTokens);
        const parsedUser = JSON.parse(storedUser);

        setTokens(parsedTokens);
        setUser(parsedUser);
        api.defaults.headers.common['Authorization'] = `Bearer ${parsedTokens.access_token}`;

        await refreshToken();
      } catch {
        clearAuth();
      }
    }

    setIsLoading(false);
  };

  const clearAuth = () => {
    localStorage.removeItem('auth_tokens');
    localStorage.removeItem('auth_user');
    setTokens(null);
    setUser(null);
    delete api.defaults.headers.common['Authorization'];
  };

  const storeAuth = (newTokens: AuthTokens, newUser: User) => {
    localStorage.setItem('auth_tokens', JSON.stringify(newTokens));
    localStorage.setItem('auth_user', JSON.stringify(newUser));
    setTokens(newTokens);
    setUser(newUser);
    api.defaults.headers.common['Authorization'] = `Bearer ${newTokens.access_token}`;
  };

  const login = async (email: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData);
    storeAuth(response.data, response.data.user);
  };

  const register = async (data: RegisterData) => {
    const response = await api.post('/auth/register', data);
    storeAuth(response.data, response.data.user);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      clearAuth();
    }
  };

  const refreshToken = async () => {
    if (!tokens?.refresh_token) return;

    try {
      const response = await api.post('/auth/refresh', { refresh_token: tokens.refresh_token });
      const newTokens = response.data;
      localStorage.setItem('auth_tokens', JSON.stringify(newTokens));
      setTokens(newTokens);
      api.defaults.headers.common['Authorization'] = `Bearer ${newTokens.access_token}`;
    } catch {
      clearAuth();
    }
  };

  const updateUser = async (data: Partial<User>) => {
    const response = await api.patch('/users/me', data);
    const updatedUser = { ...user, ...response.data } as User;
    localStorage.setItem('auth_user', JSON.stringify(updatedUser));
    setUser(updatedUser);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshToken,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}