import React, { createContext, useContext, useState, useEffect } from 'react';
import { UserProfile, UserRole } from '../types';
import { api } from '../services/api';

interface AuthContextType {
  user: UserProfile | null;
  role: UserRole;
  loading: boolean;
  loginAs: (targetRole: UserRole) => Promise<void>;
  googleLogin: (profile: { email: string; name: string; avatar_url?: string; role?: string }) => Promise<void>;
  logout: () => void;
  isAuthority: boolean;
  isWorker: boolean;
  isCitizen: boolean;
}

const DEFAULT_USERS: Record<UserRole, { email: string; name: string }> = {
  citizen: { email: 'citizen@roadsentinel.ai', name: 'Aarav Sharma (Citizen)' },
  authority: { email: 'authority@roadsentinel.ai', name: 'Kavya Patel (Municipal Validator)' },
  worker: { email: 'worker@roadsentinel.ai', name: 'Ramesh Kumar (Field Contractor)' }
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    const saved = localStorage.getItem('roadsentinel_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [loading, setLoading] = useState(false);

  const role: UserRole = user?.role || 'citizen';

  // Seed / sync initial user if not present
  useEffect(() => {
    if (!user) {
      loginAs('citizen');
    }
  }, []);

  const loginAs = async (targetRole: UserRole) => {
    setLoading(true);
    const target = DEFAULT_USERS[targetRole];
    try {
      const profile = await api.loginLocal({ email: target.email, role: targetRole });
      setUser(profile);
      localStorage.setItem('roadsentinel_user', JSON.stringify(profile));
    } catch (err) {
      console.warn('Backend login fallback:', err);
      const fallbackUser: UserProfile = {
        id: `local-${targetRole}`,
        email: target.email,
        name: target.name,
        role: targetRole,
        avatar_url: `https://api.dicebear.com/7.x/avataaars/svg?seed=${targetRole}`,
        organization: targetRole === 'authority' ? 'Bengaluru Municipal Corporation' : targetRole === 'worker' ? 'Apex Road Repairs Ltd' : 'Citizen Reporter',
        provider: 'local',
        created_at: new Date().toISOString()
      };
      setUser(fallbackUser);
      localStorage.setItem('roadsentinel_user', JSON.stringify(fallbackUser));
    } finally {
      setLoading(false);
    }
  };

  const googleLogin = async (profileData: { email: string; name: string; avatar_url?: string; role?: string }) => {
    setLoading(true);
    try {
      const profile = await api.loginWithGoogle({
        email: profileData.email,
        name: profileData.name,
        avatar_url: profileData.avatar_url,
        role: profileData.role || 'citizen'
      });
      setUser(profile);
      localStorage.setItem('roadsentinel_user', JSON.stringify(profile));
    } catch (err) {
      console.warn('Google login fallback:', err);
      const fallbackUser: UserProfile = {
        id: `google-${Date.now()}`,
        email: profileData.email,
        name: profileData.name,
        role: (profileData.role as UserRole) || 'citizen',
        avatar_url: profileData.avatar_url || `https://api.dicebear.com/7.x/avataaars/svg?seed=${profileData.email}`,
        organization: 'Verified Google Account',
        provider: 'google',
        created_at: new Date().toISOString()
      };
      setUser(fallbackUser);
      localStorage.setItem('roadsentinel_user', JSON.stringify(fallbackUser));
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('roadsentinel_user');
    loginAs('citizen');
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        loading,
        loginAs,
        googleLogin,
        logout,
        isAuthority: role === 'authority',
        isWorker: role === 'worker',
        isCitizen: role === 'citizen'
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
};
