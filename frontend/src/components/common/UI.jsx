import React from 'react';
import { AlertTriangle, RefreshCw, BarChart2 } from 'lucide-react';

/* ─── Skeleton Loaders ─── */
export function SkeletonCard({ lines = 3, className = '' }) {
  return (
    <div className={`glass-card p-6 space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-4 rounded-lg"
          style={{ width: `${90 - i * 15}%` }}
        />
      ))}
    </div>
  );
}

export function SkeletonStatGrid() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map(i => (
        <div key={i} className="glass-card p-5 space-y-3">
          <div className="flex items-start gap-3">
            <div className="skeleton w-11 h-11 rounded-xl flex-shrink-0" />
            <div className="flex-1 space-y-2">
              <div className="skeleton h-3 rounded w-3/4" />
              <div className="skeleton h-6 rounded w-1/2" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function SkeletonGroupCard() {
  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-start gap-3">
        <div className="skeleton w-10 h-10 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 rounded w-2/3" />
          <div className="skeleton h-3 rounded w-1/2" />
        </div>
      </div>
      <div className="skeleton h-8 rounded-xl w-full" />
    </div>
  );
}

/* ─── Loading Spinner ─── */
export function LoadingSpinner({ size = 'md', message }) {
  const sizes = { sm: 'w-5 h-5', md: 'w-9 h-9', lg: 'w-14 h-14' };
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16">
      <div className="relative">
        <div className={`${sizes[size]} rounded-full border-3 border-brand-100 border-t-brand-500 animate-spin`}
          style={{ borderWidth: '3px' }} />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
        </div>
      </div>
      {message && (
        <p className="text-sm text-slate-500 font-medium animate-pulse">{message}</p>
      )}
    </div>
  );
}

/* ─── Error Message ─── */
export function ErrorMessage({ message, onRetry }) {
  return (
    <div className="glass-card p-6 border border-red-200/50 fade-up">
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-xl bg-red-100/80 flex items-center justify-center flex-shrink-0">
          <AlertTriangle className="w-5 h-5 text-red-500" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-900 text-sm">Something went wrong</p>
          <p className="text-sm text-slate-500 mt-1">{message}</p>
          {onRetry && (
            <button
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-semibold
                         text-brand-600 hover:text-brand-700 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Empty State ─── */
export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="text-center py-20 fade-up">
      <div className="inline-flex w-20 h-20 rounded-3xl items-center justify-center mb-5
                      bg-gradient-to-br from-brand-50 to-violet-50
                      border border-brand-100/60 shadow-glass text-4xl">
        {icon}
      </div>
      <h3 className="text-lg font-bold text-slate-800 mb-2">{title}</h3>
      {description && (
        <p className="text-slate-500 text-sm max-w-xs mx-auto mb-6">{description}</p>
      )}
      {action}
    </div>
  );
}

/* ─── Net Position Badge ─── */
export function NetPositionBadge({ netBalance, className = '' }) {
  const net = Number(netBalance ?? 0);
  const abs = Math.abs(net).toFixed(2);

  if (net > 0.005) {
    return (
      <span className={`net-owed ${className}`}>
        ↑ You're owed ₹{abs}
      </span>
    );
  }
  if (net < -0.005) {
    return (
      <span className={`net-owe ${className}`}>
        ↓ You owe ₹{abs}
      </span>
    );
  }
  return (
    <span className={`net-settled ${className}`}>
      ✓ Settled
    </span>
  );
}

/* ─── Stat Widget ─── */
export function StatWidget({ icon, label, value, sublabel, colorClass, onClick }) {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag onClick={onClick} className={`stat-widget ${onClick ? 'cursor-pointer' : ''}`}>
      <div className={`w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 ${colorClass}`}>
        {icon}
      </div>
      <div className="min-w-0 text-left">
        <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{label}</p>
        <p className="text-2xl font-black text-slate-900 mt-0.5 leading-tight">{value}</p>
        {sublabel && <p className="text-xs text-slate-400 mt-0.5 font-medium">{sublabel}</p>}
      </div>
    </Tag>
  );
}

/* ─── Insight Card ─── */
export function InsightCard({ title, value, subtext, trend, icon, colorClass }) {
  return (
    <div className="insight-card">
      <div className="flex items-start justify-between">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400">{title}</p>
        {icon && (
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${colorClass || 'bg-brand-100'}`}>
            {icon}
          </div>
        )}
      </div>
      <p className="text-xl font-black text-slate-900 mt-1">{value}</p>
      {subtext && <p className="text-xs text-slate-500 font-medium">{subtext}</p>}
      {trend !== undefined && (
        <div className={`flex items-center gap-1 text-xs font-bold mt-1 ${
          trend > 0 ? 'text-red-500' : trend < 0 ? 'text-emerald-600' : 'text-slate-400'
        }`}>
          {trend > 0 ? '↑' : trend < 0 ? '↓' : '→'}
          {Math.abs(trend).toFixed(0)}% vs last month
        </div>
      )}
    </div>
  );
}

/* ─── Chart Empty placeholder ─── */
export function ChartEmpty({ message = 'No data yet' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-300">
      <BarChart2 className="w-10 h-10" />
      <p className="text-sm font-medium text-slate-400">{message}</p>
    </div>
  );
}
