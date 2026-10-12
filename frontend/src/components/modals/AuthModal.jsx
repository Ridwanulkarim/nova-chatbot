import React, { useState } from 'react';
import { X, Sparkles, AlertCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';

export function AuthModal({ theme }) {
  const isLight = theme === 'lavender-glow';
  const { isAuthModalOpen, setIsAuthModalOpen, login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        await register(email, password, fullName);
      } else {
        await login(email, password);
      }
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setError(null);
    setLoading(true);
    const demoEmail = 'guest.developer@nova-ai.local';
    const demoPw = 'NovaPass2026!';
    try {
      try {
        await login(demoEmail, demoPw);
      } catch (e) {
        await register(demoEmail, demoPw, 'Demo Engineer');
      }
    } catch (err) {
      setError(err.message || 'Could not launch demo session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm animate-fade-in ${
      isLight ? 'bg-slate-900/30' : 'bg-black/70'
    }`}>
      <div className={`relative w-full max-w-md rounded-2xl border shadow-2xl p-6 transition-colors ${
        isLight
          ? 'bg-white text-slate-900 border-purple-200/90 shadow-purple-950/10'
          : 'bg-slate-900 border-slate-800 text-slate-100 shadow-2xl'
      }`}>
        <button
          onClick={() => setIsAuthModalOpen(false)}
          className={`absolute top-4 right-4 p-1.5 rounded-lg transition-colors ${
            isLight
              ? 'text-slate-400 hover:text-slate-900 hover:bg-purple-50'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <X size={18} />
        </button>

        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-xl bg-purple-600 flex items-center justify-center text-white shadow-md shadow-purple-500/20">
            <Sparkles size={18} />
          </div>
          <h2 className={`text-lg font-bold ${
            isLight ? 'text-slate-900' : 'text-white'
          }`}>
            {isRegister ? 'Join Nova AI' : 'Sign in to Nova AI'}
          </h2>
        </div>
        <p className={`text-xs mb-6 ${
          isLight ? 'text-slate-500' : 'text-slate-400'
        }`}>
          Access multi-model AI reasoning, document intelligence, and saved history.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-rose-950/80 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle size={15} className="flex-shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegister && (
            <div>
              <label className={`block text-xs font-medium mb-1.5 ${
                isLight ? 'text-slate-700' : 'text-slate-300'
              }`}>
                Full Name
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Ada Lovelace"
                className={`w-full rounded-xl p-3 text-xs focus:outline-none border ${
                  isLight
                    ? 'bg-purple-50/60 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-400'
                    : 'bg-slate-950 border-slate-800 text-slate-100 placeholder-slate-400 focus:border-brand-500'
                }`}
              />
            </div>
          )}

          <div>
            <label className={`block text-xs font-medium mb-1.5 ${
              isLight ? 'text-slate-700' : 'text-slate-300'
            }`}>
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@domain.com"
              className={`w-full rounded-xl p-3 text-xs focus:outline-none border ${
                isLight
                  ? 'bg-purple-50/60 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-400'
                  : 'bg-slate-950 border-slate-800 text-slate-100 placeholder-slate-400 focus:border-brand-500'
              }`}
            />
          </div>

          <div>
            <label className={`block text-xs font-medium mb-1.5 ${
              isLight ? 'text-slate-700' : 'text-slate-300'
            }`}>
              Password
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className={`w-full rounded-xl p-3 text-xs focus:outline-none border ${
                isLight
                  ? 'bg-purple-50/60 border-purple-200 text-slate-900 placeholder-slate-400 focus:bg-white focus:border-purple-400'
                  : 'bg-slate-950 border-slate-800 text-slate-100 placeholder-slate-400 focus:border-brand-500'
              }`}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md shadow-purple-600/30 transition-all flex items-center justify-center"
          >
            {loading ? 'Please wait...' : isRegister ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        <div className="mt-4 pt-4 border-t border-purple-100 dark:border-slate-800 space-y-3">
          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={loading}
            className={`w-full py-2 rounded-xl text-xs font-medium border transition-colors ${
              isLight
                ? 'bg-purple-50 hover:bg-purple-100 text-purple-900 border-purple-200'
                : 'bg-slate-850 hover:bg-slate-800 text-brand-300 border-slate-700'
            }`}
          >
            ⚡ One-Click Instant Guest / Demo Session
          </button>

          <div className="text-center">
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError(null);
              }}
              className={`text-xs hover:underline ${
                isLight ? 'text-purple-700' : 'text-brand-400'
              }`}
            >
              {isRegister
                ? 'Already have an account? Sign In'
                : "Don't have an account? Register free"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
