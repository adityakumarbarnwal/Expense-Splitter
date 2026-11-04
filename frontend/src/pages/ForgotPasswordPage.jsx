import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, KeyRound, Mail, ArrowRight, ArrowLeft, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { authApi } from '../services/api';

export default function ForgotPasswordPage() {
  const [step, setStep] = useState(1); // 1: Email, 2: OTP, 3: New Password, 4: Done
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Step 1: Request OTP
  const handleSendOTP = async (e) => {
    e.preventDefault();
    if (!email.trim()) {
      toast.error('Please enter your email address');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await authApi.forgotPassword({ email: email.trim() });
      toast.success('Verification code sent to your email');
      setStep(2);
    } catch (err) {
      const msg = err.message || 'Failed to send reset code';
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // Step 2: Verify OTP
  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    if (!otp.trim()) {
      toast.error('Please enter the 6-digit OTP');
      return;
    }
    if (otp.trim().length !== 6) {
      toast.error('OTP must be exactly 6 digits');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await authApi.verifyOTP({ email: email.trim(), otp: otp.trim() });
      const token = res.reset_token || res.token || res.data?.reset_token;
      if (!token) {
        throw new Error('No reset token returned from server');
      }
      setResetToken(token);
      toast.success('Code verified successfully');
      setStep(3);
    } catch (err) {
      const msg = err.message || 'Invalid or expired OTP';
      setError(msg);
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  };

  // Step 3: Reset Password
  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!newPassword || !confirmPassword) {
      toast.error('Please fill in both password fields');
      return;
    }
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters long');
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await authApi.resetPassword({
        reset_token: resetToken,
        new_password: newPassword,
      });
      toast.success('Password reset successfully!');
      setStep(4);
    } catch (err) {
      const msg = err.message || 'Failed to reset password. Please try again.';
      setError(msg);
      toast.error(msg);
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
          <p className="text-slate-500 text-sm mt-1 font-medium">
            {step === 4 ? 'Password updated' : 'Reset your password'}
          </p>
        </div>

        {/* Step indicator */}
        {step < 4 && (
          <div className="flex items-center justify-center gap-2 mb-6">
            <span className={`h-1.5 rounded-full transition-all ${step >= 1 ? 'w-8 bg-brand-600' : 'w-4 bg-slate-200'}`} />
            <span className={`h-1.5 rounded-full transition-all ${step >= 2 ? 'w-8 bg-brand-600' : 'w-4 bg-slate-200'}`} />
            <span className={`h-1.5 rounded-full transition-all ${step >= 3 ? 'w-8 bg-brand-600' : 'w-4 bg-slate-200'}`} />
          </div>
        )}

        {/* Card */}
        <div className="glass-card-elevated p-8 fade-up stagger-2">
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs font-semibold text-red-600">
              {error}
            </div>
          )}

          {/* STEP 1: Enter Email */}
          {step === 1 && (
            <form onSubmit={handleSendOTP} className="space-y-5">
              <div>
                <p className="text-xs text-slate-500 mb-3 font-medium">
                  Enter your registered email address and we'll send you a 6-digit verification code.
                </p>
                <label className="label" htmlFor="email">Email address</label>
                <div className="relative">
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input pl-10"
                    placeholder="you@example.com"
                    autoComplete="email"
                    required
                    autoFocus
                  />
                  <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base"
              >
                {submitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Sending OTP...
                  </>
                ) : (
                  <>
                    Send OTP <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* STEP 2: Enter OTP */}
          {step === 2 && (
            <form onSubmit={handleVerifyOTP} className="space-y-5">
              <div>
                <p className="text-xs text-slate-500 mb-3 font-medium">
                  Enter the 6-digit code sent to <strong className="text-slate-700">{email}</strong>.
                </p>
                <div className="flex items-center justify-between">
                  <label className="label" htmlFor="otp">Verification Code</label>
                  <button
                    type="button"
                    onClick={() => { setStep(1); setError(null); }}
                    className="text-xs text-brand-600 hover:underline mb-1"
                  >
                    Change email
                  </button>
                </div>
                <div className="relative">
                  <input
                    id="otp"
                    type="text"
                    pattern="[0-9]{6}"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    className="input pl-10 text-center tracking-widest text-lg font-bold"
                    placeholder="123456"
                    required
                    autoFocus
                  />
                  <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting || otp.length !== 6}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base"
              >
                {submitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Verifying...
                  </>
                ) : (
                  <>
                    Verify OTP <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* STEP 3: New Password */}
          {step === 3 && (
            <form onSubmit={handleResetPassword} className="space-y-4">
              <p className="text-xs text-slate-500 mb-2 font-medium">
                Create a strong new password with at least 8 characters.
              </p>

              <div>
                <label className="label" htmlFor="new-password">New Password</label>
                <div className="relative">
                  <input
                    id="new-password"
                    type={showPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="input pr-10"
                    placeholder="At least 8 characters"
                    minLength={8}
                    required
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(s => !s)}
                    tabIndex={-1}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="label" htmlFor="confirm-password">Confirm Password</label>
                <div className="relative">
                  <input
                    id="confirm-password"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input pr-10"
                    placeholder="Re-enter password"
                    minLength={8}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(s => !s)}
                    tabIndex={-1}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base mt-2"
              >
                {submitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Resetting...
                  </>
                ) : (
                  'Reset Password'
                )}
              </button>
            </form>
          )}

          {/* STEP 4: Success */}
          {step === 4 && (
            <div className="text-center py-2 space-y-4">
              <div className="w-14 h-14 rounded-2xl bg-emerald-100 text-emerald-600 mx-auto flex items-center justify-center">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-slate-900">Password Reset Complete!</h2>
                <p className="text-xs text-slate-500 mt-1">
                  Your password has been successfully updated. You can now sign in with your new password.
                </p>
              </div>
              <Link
                to="/login"
                className="btn-primary w-full flex items-center justify-center gap-2 py-3 text-base mt-2"
              >
                Sign In Now
              </Link>
            </div>
          )}
        </div>

        {/* Back to login link */}
        <p className="text-center text-sm text-slate-500 mt-6 fade-up stagger-3">
          <Link to="/login" className="text-brand-600 font-bold hover:text-brand-700 transition-colors inline-flex items-center gap-1.5">
            <ArrowLeft className="w-4 h-4" /> Back to Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}
