import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, UserPlus } from 'lucide-react';
import toast from 'react-hot-toast';
import apiClient from '../services/api';

/**
 * RegisterPage — creates a new account then redirects to /login.
 *
 * Uses apiClient directly (not AuthContext.register) so we can:
 *   1. Redirect to /login on success rather than /dashboard.
 *   2. Handle 409 Conflict (duplicate email) with a targeted message.
 *   3. Handle 503 (DB temporarily unavailable) without claiming the
 *      account definitely does not exist.
 *
 * The backend register endpoint:
 *   - Returns 201 on success (account created, JWT cookie set)
 *   - Returns 409 on duplicate email
 *   - Returns 503 on database error (account may or may not have been created)
 */
export default function RegisterPage() {
  const navigate = useNavigate();

  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.email || !form.password) {
      toast.error('Please fill in all fields'); return;
    }
    if (form.password.length < 6) {
      toast.error('Password must be at least 6 characters'); return;
    }
    if (form.password !== form.confirmPassword) {
      toast.error('Passwords do not match'); return;
    }

    setSubmitting(true);
    try {
      await apiClient.post('/auth/register', {
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      });

      // Success: account created. Redirect to login so the user signs in normally.
      toast.success('Account created! Please log in to continue.');
      navigate('/login', { replace: true });

    } catch (err) {
      const httpStatus = err?.status ?? err?.response?.status ?? null;

      if (httpStatus === 409) {
        // Duplicate email — account already exists
        toast.error('An account with this email already exists. Please log in.');
        navigate('/login', { replace: true });
        return;
      }

      if (httpStatus === 503) {
        // Database temporarily unavailable — account may or may not have been created.
        // Do NOT let the user retry blindly as that could create a duplicate.
        toast.error(
          'The server is temporarily unavailable. ' +
          'Your account may have been created — try logging in first before registering again.'
        );
        // Redirect to login so the user can check whether their account exists
        navigate('/login', { replace: true });
        return;
      }

      // Other errors (validation, network, etc.)
      toast.error(err.message || 'Registration failed. Please try again.');
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
          <h1 className="text-3xl font-black text-slate-900">Join SplitIt</h1>
          <p className="text-slate-500 text-sm mt-1 font-medium">Split expenses effortlessly with AI</p>
        </div>

        {/* Card */}
        <div className="glass-card-elevated p-8 fade-up stagger-2">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label" htmlFor="name">Full Name</label>
              <input id="name" type="text" value={form.name}
                onChange={e => setForm(p => ({ ...p, name: e.target.value }))}
                className="input" placeholder="Aditya Kumar"
                autoComplete="name" required autoFocus maxLength={100} />
            </div>

            <div>
              <label className="label" htmlFor="email">Email address</label>
              <input id="email" type="email" value={form.email}
                onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                className="input" placeholder="you@example.com"
                autoComplete="email" required />
            </div>

            <div>
              <label className="label" htmlFor="password">Password</label>
              <div className="relative">
                <input id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                  className="input pr-10" placeholder="At least 6 characters"
                  autoComplete="new-password" required minLength={6} />
                <button type="button" onClick={() => setShowPassword(s => !s)} tabIndex={-1}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors">
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label className="label" htmlFor="confirmPassword">Confirm Password</label>
              <input id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                value={form.confirmPassword}
                onChange={e => setForm(p => ({ ...p, confirmPassword: e.target.value }))}
                className="input" placeholder="Re-enter your password"
                autoComplete="new-password" required />
            </div>

            <button type="submit" disabled={submitting}
              className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base mt-2">
              {submitting ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Creating account...
                </>
              ) : (
                <><UserPlus className="w-4 h-4" /> Create Account</>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-6 fade-up stagger-3">
          Already have an account?{' '}
          <Link to="/login" className="text-brand-600 font-bold hover:text-brand-700 transition-colors">
            Sign in →
          </Link>
        </p>
      </div>
    </div>
  );
}
