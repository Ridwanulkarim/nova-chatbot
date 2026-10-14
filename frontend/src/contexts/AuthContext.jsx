import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  sendPasswordResetEmail,
  signOut,
  updateProfile,
} from 'firebase/auth';
import { auth } from '../firebase';
import { api, getAuthToken, setAuthToken } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState('login'); // 'login' | 'signup' | 'reset'

  useEffect(() => {
    // Listen to Firebase authentication state changes
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        try {
          const token = await firebaseUser.getIdToken();
          setAuthToken(token);
        } catch (e) {
          console.warn('Could not extract Firebase ID token:', e);
        }
        setUser({
          id: firebaseUser.uid,
          uid: firebaseUser.uid,
          email: firebaseUser.email,
          full_name:
            firebaseUser.displayName ||
            (firebaseUser.email ? firebaseUser.email.split('@')[0] : 'User'),
          displayName: firebaseUser.displayName,
          photoURL: firebaseUser.photoURL,
          photo_url: firebaseUser.photoURL,
        });
        setLoading(false);
      } else {
        // Fallback: check if legacy backend session exists
        const token = getAuthToken();
        if (token) {
          try {
            const userData = await api.getMe();
            setUser(userData);
          } catch (err) {
            setAuthToken(null);
            setUser(null);
          }
        } else {
          setUser(null);
        }
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  const loginWithEmail = async (email, password) => {
    const cred = await signInWithEmailAndPassword(auth, email, password);
    return cred.user;
  };

  const registerWithEmail = async (email, password, fullName) => {
    const cred = await createUserWithEmailAndPassword(auth, email, password);
    if (fullName?.trim()) {
      try {
        await updateProfile(cred.user, { displayName: fullName.trim() });
      } catch (e) {
        console.warn('Could not update profile displayName:', e);
      }
    }
    return cred.user;
  };

  const loginWithGoogle = async () => {
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: 'select_account' });
    const cred = await signInWithPopup(auth, provider);
    return cred.user;
  };

  const resetPassword = async (email) => {
    return await sendPasswordResetEmail(auth, email);
  };

  const logout = async () => {
    try {
      await signOut(auth);
    } catch (e) {
      console.warn('Firebase signOut error:', e);
    }
    setAuthToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login: loginWithEmail,
        register: registerWithEmail,
        loginWithEmail,
        registerWithEmail,
        loginWithGoogle,
        resetPassword,
        logout,
        isAuthModalOpen,
        setIsAuthModalOpen,
        authMode,
        setAuthMode,
        openLoginModal: () => {
          setAuthMode('login');
          setIsAuthModalOpen(true);
        },
        openSignupModal: () => {
          setAuthMode('signup');
          setIsAuthModalOpen(true);
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
