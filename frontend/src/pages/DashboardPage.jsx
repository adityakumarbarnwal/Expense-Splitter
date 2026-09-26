import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, DollarSign, Users, Receipt,
  ArrowRight, AlertCircle, Sparkles, Plus, BarChart2, Zap
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import { dashboardApi, balancesApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, NetPositionBadge, StatWidget, ChartEmpty } from '../components/common/UI';
import { useAuth } from '../contexts/AuthContext';

function formatCurrency(amount) {
  return `₹${Math.abs(Number(amount)).toFixed(2)}`;
}
function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short',
  });
}
function greet(name) {
  const h = new Date().getHours();
  const first = name?.split(' ')[0] || 'there';
  if (h < 12) return `Good morning, ${first} ☀️`;
  if (h < 17) return `Good afternoon, ${first} 👋`;
  return `Good evening, ${first} 🌙`;
}

/* ── Recharts tooltip ── */
function CurrencyTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card-elevated px-4 py-3 text-sm">
      <p className="font-semibold text-slate-700">{label}</p>
      <p className="text-brand-600 font-bold mt-0.5">₹{Number(payload[0].value).toFixed(2)}</p>
    </div>
  );
}

const CHART_COLORS = ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboard = useCallback(async () => {
    try {
      setError(null);
      const res = await dashboardApi.get();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchDashboard} />;

  const net = Number(data?.net_balance ?? 0);
  const youOwe = Number(data?.you_owe ?? 0);
  const youAreOwed = Number(data?.you_are_owed ?? 0);
  const totalGroups = data?.total_groups ?? 0;

  /* Build monthly spending from recent_expenses */
  const monthlyMap = {};
  (data?.recent_expenses || []).forEach(exp => {
    const m = new Date(exp.created_at).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
    monthlyMap[m] = (monthlyMap[m] || 0) + Number(exp.amount);
  });
  const spendingChartData = Object.entries(monthlyMap)
    .slice(-6)
    .map(([month, total]) => ({ month, total }));

  /* Group net positions for pie */
  const groupPieData = (data?.groups || [])
    .slice(0, 5)
    .filter(g => g.user_net_balance !== undefined && g.user_net_balance !== null)
    .map(g => ({
      name: g.name.length > 14 ? g.name.slice(0, 13) + '…' : g.name,
      value: Math.abs(Number(g.user_net_balance)),
      net: Number(g.user_net_balance),
    }));

  return (
    <div className="space-y-8 fade-up">
      {/* ── Welcome ── */}
      <div className="stagger-1">
        <h1 className="text-3xl font-black text-slate-900">{greet(user?.name)}</h1>
        <p className="text-slate-500 mt-1 font-medium">Here's your expense overview</p>
      </div>

      {/* ── Financial Summary ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 stagger-2">
        <StatWidget
          icon={<Users className="w-5 h-5 text-brand-600" />}
          label="Active Groups"
          value={totalGroups}
          sublabel="You're a member of"
          colorClass="bg-brand-100/80"
        />
        <StatWidget
          icon={<TrendingDown className="w-5 h-5 text-red-500" />}
          label="You Owe"
          value={formatCurrency(youOwe)}
          sublabel="Across all groups"
          colorClass="bg-red-100/80"
        />
        <StatWidget
          icon={<TrendingUp className="w-5 h-5 text-emerald-600" />}
          label="You're Owed"
          value={formatCurrency(youAreOwed)}
          sublabel="Across all groups"
          colorClass="bg-emerald-100/80"
        />
        <StatWidget
          icon={<DollarSign className={`w-5 h-5 ${net >= 0 ? 'text-emerald-600' : 'text-red-500'}`} />}
          label="Net Balance"
          value={`${net >= 0 ? '+' : '-'}${formatCurrency(net)}`}
          sublabel={net > 0 ? 'You get back' : net < 0 ? 'Net owe' : 'All settled!'}
          colorClass={net >= 0 ? 'bg-emerald-100/80' : 'bg-red-100/80'}
        />
      </div>

      {/* ── Net Balance Alert ── */}
      {net !== 0 && (
        <div className={`glass-card p-4 flex items-start gap-3 border stagger-3 ${
          net < 0
            ? 'border-red-200/50 bg-red-50/40'
            : 'border-emerald-200/50 bg-emerald-50/40'
        }`}>
          {net < 0 ? (
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          ) : (
            <TrendingUp className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          )}
          <p className="text-sm font-medium text-slate-700">
            {net < 0 ? (
              <>You owe a net of <strong className="text-red-600">{formatCurrency(net)}</strong> across your groups.{' '}
              <Link to="/groups" className="text-brand-600 font-semibold hover:underline">Settle up →</Link></>
            ) : (
              <>Others owe you <strong className="text-emerald-600">{formatCurrency(net)}</strong> overall — you're in the clear! 🎉</>
            )}
          </p>
        </div>
      )}

      {/* ── Quick Actions ── */}
      <div className="stagger-3">
        <p className="section-title">Quick Actions</p>
        <div className="flex flex-wrap gap-3">
          <Link to="/groups" className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> New Group
          </Link>
          <Link
            to="/groups"
            className="btn-secondary flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4 text-violet-500" /> AI Expense
          </Link>
          <Link to="/groups" className="btn-secondary flex items-center gap-2">
            <BarChart2 className="w-4 h-4" /> View Balances
          </Link>
        </div>
      </div>

      {/* ── Charts row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 stagger-4">
        {/* Spending trend */}
        <div className="glass-card p-6 lg:col-span-2">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-lg bg-brand-100/80 flex items-center justify-center">
              <BarChart2 className="w-4 h-4 text-brand-600" />
            </div>
            <div>
              <h2 className="font-bold text-slate-900 text-sm">Spending Overview</h2>
              <p className="text-[11px] text-slate-400 font-medium">From recent activity</p>
            </div>
          </div>
          {spendingChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={spendingChartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                  tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
                <Tooltip content={<CurrencyTooltip />} />
                <Area type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={2.5}
                  fill="url(#spendGrad)" dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }}
                  activeDot={{ r: 6, fill: '#4338ca', strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <ChartEmpty message="Add expenses to see spending trends" />
          )}
        </div>

        {/* Group positions pie */}
        <div className="glass-card p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-lg bg-violet-100/80 flex items-center justify-center">
              <Users className="w-4 h-4 text-violet-600" />
            </div>
            <div>
              <h2 className="font-bold text-slate-900 text-sm">Group Balances</h2>
              <p className="text-[11px] text-slate-400 font-medium">Absolute net per group</p>
            </div>
          </div>
          {groupPieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie data={groupPieData} cx="50%" cy="50%" innerRadius={45} outerRadius={72}
                  paddingAngle={3} dataKey="value">
                  {groupPieData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} opacity={0.85} />
                  ))}
                </Pie>
                <Tooltip formatter={(v, name, props) => [
                  `₹${Number(v).toFixed(2)}`,
                  props.payload?.net >= 0 ? 'You\'re owed' : 'You owe'
                ]} />
                <Legend iconSize={8} iconType="circle"
                  formatter={v => <span className="text-xs text-slate-600 font-medium">{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <ChartEmpty message="No group balance data" />
          )}
        </div>
      </div>

      {/* ── Recent + Groups ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 stagger-5">
        {/* Recent Expenses */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Receipt className="w-4 h-4 text-slate-400" />
              <h2 className="font-bold text-slate-900">Recent Expenses</h2>
            </div>
          </div>
          {!data?.recent_expenses?.length ? (
            <p className="text-sm text-slate-400 text-center py-8">No recent expenses</p>
          ) : (
            <ul className="space-y-1">
              {data.recent_expenses.slice(0, 7).map((exp) => (
                <li key={exp.id} className="flex items-center justify-between py-2.5
                                             border-b border-slate-100/60 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-800 truncate">{exp.description}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {exp.payer_name} · {formatDate(exp.created_at)}
                    </p>
                  </div>
                  <span className="text-sm font-bold text-slate-700 flex-shrink-0 ml-3">
                    {formatCurrency(exp.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Groups preview */}
        <div className="glass-card p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-slate-400" />
              <h2 className="font-bold text-slate-900">Your Groups</h2>
            </div>
            <Link to="/groups"
              className="text-xs font-bold text-brand-600 hover:text-brand-700
                         flex items-center gap-1 transition-colors">
              View all <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {!data?.groups?.length ? (
            <div className="text-center py-8">
              <p className="text-sm text-slate-400 mb-3">No groups yet</p>
              <Link to="/groups" className="btn-primary text-sm">Create a Group</Link>
            </div>
          ) : (
            <ul className="space-y-1">
              {data.groups.slice(0, 5).map((g) => {
                const gnet = Number(g.user_net_balance ?? 0);
                return (
                  <li key={g.id}>
                    <Link
                      to={`/groups/${g.id}`}
                      className="flex items-center justify-between py-2.5
                                 border-b border-slate-100/60 last:border-0
                                 hover:bg-brand-50/30 -mx-2 px-2 rounded-lg
                                 transition-colors group"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-slate-800 truncate
                                      group-hover:text-brand-700 transition-colors">
                          {g.name}
                        </p>
                        <p className="text-xs text-slate-400">
                          {g.member_count} member{g.member_count !== 1 ? 's' : ''}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-3">
                        {g.user_net_balance !== undefined && g.user_net_balance !== null ? (
                          <NetPositionBadge netBalance={gnet} />
                        ) : null}
                        <ArrowRight className="w-3.5 h-3.5 text-slate-300 group-hover:text-brand-400 transition-colors" />
                      </div>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {/* ── AI Feature callout ── */}
      <div className="ai-insight-card flex items-center gap-4 stagger-6">
        <div className="w-12 h-12 rounded-2xl bg-brand-gradient flex items-center justify-center flex-shrink-0 shadow-brand">
          <Zap className="w-6 h-6 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-bold text-slate-900">AI-Powered Expense Entry</p>
          <p className="text-sm text-slate-500 mt-0.5">
            Type naturally — "Dinner with Rahul ₹800 split equally" — and SplitIt does the rest.
          </p>
        </div>
        <Link to="/groups" className="btn-primary flex-shrink-0 flex items-center gap-2">
          <Sparkles className="w-4 h-4" /> Try AI Entry
        </Link>
      </div>
    </div>
  );
}
