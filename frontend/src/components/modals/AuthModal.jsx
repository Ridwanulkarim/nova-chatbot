import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Eye,
  EyeOff,
  ArrowLeft,
  Mail,
  Lock,
  User,
} from 'lucide-react';
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  GoogleAuthProvider,
  sendPasswordResetEmail,
  updateProfile,
} from 'firebase/auth';
import { auth } from '../../firebase';
import { useAuth } from '../../contexts/AuthContext';

function GoogleIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  );
}

function getFriendlyAuthErrorMessage(error) {
  if (!error) return 'An unexpected error occurred. Please try again.';
  const code = error.code || '';
  switch (code) {
    case 'auth/invalid-email':
      return 'Please enter a valid email address.';
    case 'auth/user-not-found':
      return 'No account exists with this email address. Please sign up first.';
    case 'auth/wrong-password':
      return 'Incorrect password. Please try again or use the password reset link.';
    case 'auth/invalid-credential':
      return 'Incorrect email or password. Please double check and try again.';
    case 'auth/email-already-in-use':
      return 'This email address is already in use. Please sign in instead.';
    case 'auth/weak-password':
      return 'Password must be at least 6 characters long.';
    case 'auth/missing-password':
      return 'Please enter your password.';
    case 'auth/popup-closed-by-user':
      return 'Google Sign-In was closed before completing. Please try again.';
    case 'auth/popup-blocked':
      return 'Google Sign-In popup was blocked by your browser. Please allow popups for this site.';
    case 'auth/cancelled-popup-request':
      return 'Previous sign-in request was cancelled. Please try again.';
    case 'auth/too-many-requests':
      return 'Too many unsuccessful attempts. Access temporarily disabled. Please reset your password or try again later.';
    case 'auth/network-request-failed':
      return 'Network connection error. Please verify your internet connection.';
    case 'auth/user-disabled':
      return 'This user account has been disabled. Please contact support.';
    case 'auth/operation-not-allowed':
      return 'This sign-in method is currently disabled in your Firebase project settings.';
    case 'auth/unauthorized-domain':
      return 'This domain is not authorized in Firebase Authentication (Console > Auth > Settings > Authorized domains).';
    default: {
      const msg = error.message || '';
      return (
        msg
          .replace(/^Firebase:\s*/i, '')
          .replace(/\s*\([a-z0-9/-]+\)\.?$/i, '')
          .trim() || 'Authentication failed. Please check your credentials and try again.'
      );
    }
  }
}

export function AuthModal({ theme }) {
  const isLight = theme === 'lavender-glow';
  const { isAuthModalOpen, setIsAuthModalOpen, authMode, setAuthMode } = useAuth();

  const [mode, setMode] = useState('login'); // 'login' | 'signup' | 'reset'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingAction, setLoadingAction] = useState(null); // 'email' | 'google' | 'reset' | 'demo'
  const [error, setError] = useState(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  const emailInputRef = useRef(null);

  // Sync mode with context authMode if provided
  useEffect(() => {
    if (authMode && ['login', 'signup', 'reset'].includes(authMode)) {
      setMode(authMode);
    }
  }, [authMode, isAuthModalOpen]);

  // Reset errors and auto-focus email on open or mode switch
  useEffect(() => {
    if (isAuthModalOpen) {
      setError(null);
      setResetSuccess(false);
      const timer = setTimeout(() => {
        emailInputRef.current?.focus();
      }, 60);
      return () => clearTimeout(timer);
    }
  }, [isAuthModalOpen, mode]);

  // Handle Escape key to close modal
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isAuthModalOpen && !loading) {
        handleClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAuthModalOpen, loading]);

  if (!isAuthModalOpen) return null;

  const handleClose = () => {
    if (loading) return;
    setIsAuthModalOpen(false);
    setError(null);
    setResetSuccess(false);
    setPassword('');
  };

  const switchMode = (newMode) => {
    if (loading) return;
    setMode(newMode);
    if (setAuthMode) setAuthMode(newMode);
    setError(null);
    setResetSuccess(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Password reset mode
    if (mode === 'reset') {
      if (!email.trim()) {
        setError('Please enter your email address to receive a reset link.');
        return;
      }
      setLoading(true);
      setLoadingAction('reset');
      try {
        await sendPasswordResetEmail(auth, email.trim());
        setResetSuccess(true);
      } catch (err) {
        setError(getFriendlyAuthErrorMessage(err));
      } finally {
        setLoading(false);
        setLoadingAction(null);
      }
      return;
    }

    // Account creation mode
    if (mode === 'signup') {
      if (password.length < 6) {
        setError('Password must be at least 6 characters long.');
        return;
      }
      setLoading(true);
      setLoadingAction('email');
      try {
        const userCred = await createUserWithEmailAndPassword(auth, email.trim(), password);
        if (fullName?.trim()) {
          try {
            await updateProfile(userCred.user, { displayName: fullName.trim() });
          } catch (e) {
            console.warn('Failed to update displayName:', e);
          }
        }
        handleClose();
      } catch (err) {
        setError(getFriendlyAuthErrorMessage(err));
      } finally {
        setLoading(false);
        setLoadingAction(null);
      }
      return;
    }

    // Default: Email/Password login mode
    setLoading(true);
    setLoadingAction('email');
    try {
      await signInWithEmailAndPassword(auth, email.trim(), password);
      handleClose();
    } catch (err) {
      setError(getFriendlyAuthErrorMessage(err));
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  };

  const handleGoogleSignIn = async () => {
    setError(null);
    setLoading(true);
    setLoadingAction('google');
    try {
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: 'select_account' });
      await signInWithPopup(auth, provider);
      handleClose();
    } catch (err) {
      setError(getFriendlyAuthErrorMessage(err));
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  };

  const handleDemoSignIn = async () => {
    setError(null);
    setLoading(true);
    setLoadingAction('demo');
    const demoEmail = 'guest.demo@plutochatbot.firebaseapp.com';
    const demoPw = 'PlutoDemoPass2026!';
    try {
      try {
        await signInWithEmailAndPassword(auth, demoEmail, demoPw);
      } catch (e) {
        const cred = await createUserWithEmailAndPassword(auth, demoEmail, demoPw);
        await updateProfile(cred.user, { displayName: 'Demo Explorer' });
      }
      handleClose();
    } catch (err) {
      setError(getFriendlyAuthErrorMessage(err));
    } finally {
      setLoading(false);
      setLoadingAction(null);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
      className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-md transition-all animate-fade-in ${
        isLight ? 'bg-slate-900/40' : 'bg-black/75'
      }`}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div
        className={`relative w-full max-w-[420px] rounded-3xl border shadow-2xl p-6 sm:p-8 max-h-[92dvh] overflow-y-auto transition-all ${
          isLight
            ? 'bg-white text-slate-900 border-purple-200/90 shadow-purple-950/10'
            : 'bg-[#18181b] border-white/10 text-slate-100 shadow-2xl shadow-black/80'
        }`}
      >
        {/* Close Button */}
        <button
          onClick={handleClose}
          disabled={loading}
          className={`absolute top-4 right-4 p-2 rounded-full transition-colors ${
            isLight
              ? 'text-slate-400 hover:text-slate-900 hover:bg-purple-50'
              : 'text-slate-400 hover:text-white hover:bg-white/10'
          }`}
          title="Close"
          aria-label="Close authentication modal"
        >
          <X size={18} />
        </button>

        {/* Brand Icon & Heading */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-purple-600/30 mb-3">
            <Sparkles size={22} />
          </div>
          <h2
            id="auth-modal-title"
            className={`text-xl font-bold tracking-tight ${
              isLight ? 'text-slate-900' : 'text-white'
            }`}
          >
            {mode === 'login'
              ? 'Welcome back'
              : mode === 'signup'
              ? 'Create your account'
              : 'Reset your password'}
          </h2>
          <p
            className={`text-xs mt-1.5 max-w-xs ${
              isLight ? 'text-slate-500' : 'text-slate-400'
            }`}
          >
            {mode === 'login'
              ? 'Sign in to Pluto AI to access your chat history, vision intelligence, and models.'
              : mode === 'signup'
              ? 'Sign up to get started with Pluto AI reasoning, web search, and document intelligence.'
              : "Enter your email address and we'll send you instructions to reset your password."}
          </p>
        </div>

        {/* Error Notification */}
        {error && (
          <div
            role="alert"
            className="mb-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-start gap-2.5 leading-relaxed animate-fade-in"
          >
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5 text-rose-500" />
            <span className="flex-1">{error}</span>
          </div>
        )}

        {/* Password Reset Success Notification */}
        {mode === 'reset' && resetSuccess && (
          <div
            role="status"
            className="mb-4 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-start gap-2.5 leading-relaxed animate-fade-in"
          >
            <CheckCircle2 size={16} className="flex-shrink-0 mt-0.5 text-emerald-400" />
            <div className="flex-1">
              <p className="font-semibold text-emerald-300">Reset link sent!</p>
              <p className="mt-0.5 text-[11px] text-emerald-400/90">
                Check your inbox at <span className="font-medium underline">{email}</span>. If you don't see it within a minute, check your spam folder.
              </p>
            </div>
          </div>
        )}

        {/* Google Sign-In Button (Login & Signup modes) */}
        {mode !== 'reset' && (
          <>
            <button
              type="button"
              onClick={handleGoogleSignIn}
              disabled={loading}
              className={`w-full py-2.5 px-4 rounded-xl border font-medium text-xs flex items-center justify-center gap-3 transition-all cursor-pointer shadow-xs ${
                isLight
                  ? 'bg-white border-slate-200 hover:bg-slate-50 text-slate-800 hover:border-slate-300'
                  : 'bg-white/5 border-white/10 hover:bg-white/10 text-white hover:border-white/20'
              } ${loading ? 'opacity-50 cursor-not-allowed' : 'active:scale-[0.99]'}`}
            >
              {loadingAction === 'google' ? (
                <>
                  <Loader2 size={16} className="animate-spin text-purple-400" />
                  <span>Connecting to Google...</span>
                </>
              ) : (
                <>
                  <GoogleIcon />
                  <span>Continue with Google</span>
                </>
              )}
            </button>

            {/* Divider OR */}
            <div className="relative my-4 flex items-center justify-center">
              <div
                className={`w-full border-t ${
                  isLight ? 'border-slate-200' : 'border-white/10'
                }`}
              />
              <span
                className={`absolute px-3 text-[10px] uppercase font-semibold tracking-wider ${
                  isLight ? 'bg-white text-slate-400' : 'bg-[#18181b] text-slate-500'
                }`}
              >
                or
              </span>
            </div>
          </>
        )}

        {/* Email/Password Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5">
          {mode === 'signup' && (
            <div>
              <label
                className={`block text-xs font-medium mb-1.5 ${
                  isLight ? 'text-slate-700' : 'text-slate-300'
                }`}
              >
                Full Name <span className="text-[10px] text-slate-400 font-normal">(Optional)</span>
              </label>
              <div className="relative">
                <input
                  type="text"
                  disabled={loading}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Ridwanul Karim"
                  className={`w-full rounded-xl pl-9 pr-3 py-2.5 text-xs focus:outline-none border transition-all ${
                    isLight
                      ? 'bg-purple-50/40 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/10'
                      : 'bg-black/40 border-white/10 text-white placeholder-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20'
                  }`}
                />
                <User size={14} className="absolute left-3 top-3 text-slate-400 pointer-events-none" />
              </div>
            </div>
          )}

          <div>
            <label
              className={`block text-xs font-medium mb-1.5 ${
                isLight ? 'text-slate-700' : 'text-slate-300'
              }`}
            >
              Email Address
            </label>
            <div className="relative">
              <input
                ref={emailInputRef}
                type="email"
                required
                disabled={loading}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@domain.com"
                className={`w-full rounded-xl pl-9 pr-3 py-2.5 text-xs focus:outline-none border transition-all ${
                  isLight
                    ? 'bg-purple-50/40 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/10'
                    : 'bg-black/40 border-white/10 text-white placeholder-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20'
                }`}
              />
              <Mail size={14} className="absolute left-3 top-3 text-slate-400 pointer-events-none" />
            </div>
          </div>

          {mode !== 'reset' && (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  className={`block text-xs font-medium ${
                    isLight ? 'text-slate-700' : 'text-slate-300'
                  }`}
                >
                  Password
                </label>
                {mode === 'login' ? (
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => switchMode('reset')}
                    className="text-[11px] text-purple-600 dark:text-purple-400 hover:underline transition-colors"
                  >
                    Forgot password?
                  </button>
                ) : (
                  <span
                    className={`text-[10px] ${
                      password.length > 0 && password.length < 6
                        ? 'text-rose-500 font-semibold'
                        : isLight
                        ? 'text-slate-500'
                        : 'text-slate-400'
                    }`}
                  >
                    Min. 6 characters ({password.length}/6)
                  </span>
                )}
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  disabled={loading}
                  minLength={mode === 'signup' ? 6 : undefined}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className={`w-full rounded-xl pl-9 pr-10 py-2.5 text-xs focus:outline-none border transition-all ${
                    isLight
                      ? 'bg-purple-50/40 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-500 focus:ring-2 focus:ring-purple-500/10'
                      : 'bg-black/40 border-white/10 text-white placeholder-slate-500 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20'
                  } ${
                    mode === 'signup' && password.length > 0 && password.length < 6
                      ? 'border-rose-400 ring-1 ring-rose-400/30'
                      : ''
                  }`}
                />
                <Lock size={14} className="absolute left-3 top-3 text-slate-400 pointer-events-none" />
                <button
                  type="button"
                  tabIndex={-1}
                  disabled={loading}
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-200 transition-colors p-0.5"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
          )}

          {/* Primary Action Button */}
          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md shadow-purple-600/30 transition-all flex items-center justify-center gap-2 cursor-pointer ${
              loading ? 'opacity-50 cursor-not-allowed' : 'active:scale-[0.99]'
            }`}
          >
            {loading && loadingAction === (mode === 'reset' ? 'reset' : 'email') ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                <span>
                  {mode === 'login'
                    ? 'Signing in...'
                    : mode === 'signup'
                    ? 'Creating account...'
                    : 'Sending reset link...'}
                </span>
              </>
            ) : (
              <span>
                {mode === 'login'
                  ? 'Sign in with Email'
                  : mode === 'signup'
                  ? 'Create Account'
                  : 'Send Reset Link'}
              </span>
            )}
          </button>
        </form>

        {/* Switcher & Secondary Actions */}
        <div className="mt-5 pt-4 border-t border-slate-200/60 dark:border-white/10 space-y-3 text-center">
          {mode === 'login' && (
            <p className={`text-xs ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
              Don't have an account?{' '}
              <button
                type="button"
                disabled={loading}
                onClick={() => switchMode('signup')}
                className="font-semibold text-purple-600 dark:text-purple-400 hover:underline transition-colors"
              >
                Sign up free
              </button>
            </p>
          )}

          {mode === 'signup' && (
            <p className={`text-xs ${isLight ? 'text-slate-600' : 'text-slate-400'}`}>
              Already have an account?{' '}
              <button
                type="button"
                disabled={loading}
                onClick={() => switchMode('login')}
                className="font-semibold text-purple-600 dark:text-purple-400 hover:underline transition-colors"
              >
                Sign in
              </button>
            </p>
          )}

          {mode === 'reset' && (
            <button
              type="button"
              disabled={loading}
              onClick={() => switchMode('login')}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-purple-600 dark:text-purple-400 hover:underline transition-colors"
            >
              <ArrowLeft size={13} />
              <span>Back to sign in</span>
            </button>
          )}

          {/* Quick Demo Session */}
          <div className="pt-1">
            <button
              type="button"
              onClick={handleDemoSignIn}
              disabled={loading}
              className={`text-[11px] underline-offset-2 hover:underline transition-colors ${
                isLight ? 'text-slate-400 hover:text-purple-700' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {loadingAction === 'demo' ? 'Launching guest demo session...' : '⚡ Try instant guest demo session'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
