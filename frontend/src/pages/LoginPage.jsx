import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, LogIn, Zap, Shield, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../contexts/AuthContext';

const features = [
  { icon: <Users className="w-4 h-4" />, text: 'Group expense splitting' },
  { icon: <Zap className="w-4 h-4" />, text: 'AI-powered entry' },
  { icon: <Shield className="w-4 h-4" />, text: 'Real-time balances' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/dashboard';

  const [form, setForm] = useState({ email: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password) {
      toast.error('Please fill in all fields');
      return;
    }
    setSubmitting(true);
    try {
      await login(form.email.trim(), form.password);
      toast.success('Welcome back!');
      navigate(from, { replace: true });
    } catch (err) {
      toast.error(err.message || 'Login failed. Check your credentials.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">

        {/* Brand */}
        <div className="text-center mb-8 fade-up">
          <div className="inline-flex w-16 h-16 rounded-3xl bg-brand-gradient items-center justify-center
                          shadow-brand mb-4">
            <span className="text-white font-black text-2xl">S</span>
          </div>
          <h1 className="text-3xl font-black text-slate-900">SplitIt</h1>
          <p className="text-slate-500 text-sm mt-1 font-medium">Sign in to your account</p>
        </div>

        {/* Features */}
        <div className="flex justify-center gap-4 mb-8 fade-up stagger-2">
          {features.map((f, i) => (
            <div key={i} className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
              <span className="text-brand-500">{f.icon}</span>
              {f.text}
            </div>
          ))}
        </div>

        {/* Card */}
        <div className="glass-card-elevated p-8 fade-up stagger-3">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="label" htmlFor="email">Email address</label>
              <input
                id="email" type="email" value={form.email}
                onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                className="input" placeholder="you@example.com"
                autoComplete="email" required autoFocus
              />
            </div>

            <div>
              <label className="label" htmlFor="password">Password</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                  className="input pr-10"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  required
                />
                <button type="button" onClick={() => setShowPassword(s => !s)} tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={submitting}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base">
              {submitting ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Signing in...
                </>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  Sign In
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-6 fade-up stagger-4">
          Don't have an account?{' '}
          <Link to="/register" className="text-brand-600 font-bold hover:text-brand-700 transition-colors">
            Create one free →
          </Link>
        </p>
      </div>
    </div>
  );
}
