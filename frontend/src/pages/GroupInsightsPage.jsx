import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  BarChart2, TrendingUp, TrendingDown, Users, Receipt,
  Zap, RefreshCw, AlertCircle, CheckCircle, Sparkles,
  Award, Target
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts';
import { insightsApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, InsightCard, ChartEmpty } from '../components/common/UI';

function formatCurrency(amount) {
  return `₹${Math.abs(Number(amount || 0)).toFixed(2)}`;
}

const CHART_COLORS = ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'];

function CurrencyTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card-elevated px-3 py-2.5 text-xs">
      <p className="font-semibold text-slate-600">{label}</p>
      <p className="text-brand-600 font-bold mt-0.5">₹{Number(payload[0].value).toFixed(2)}</p>
    </div>
  );
}

/** AI Insights panel */
function AIInsightsPanel({ groupId, stats }) {
  const [aiData, setAIData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tried, setTried] = useState(false);

  const fetchAI = useCallback(async () => {
    setLoading(true);
    setTried(true);
    try {
      const result = await insightsApi.getAIInsights(groupId, stats);
      setAIData(result);
    } catch {
      setAIData({ success: false, error: 'AI insights are temporarily unavailable.' });
    } finally {
      setLoading(false);
    }
  }, [groupId, stats]);

  if (!tried) {
    return (
      <div className="ai-insight-card">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-brand">
            <Sparkles className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-900 text-sm">AI Group Insights</p>
            <p className="text-xs text-slate-500">Powered by Gemini</p>
          </div>
        </div>
        <p className="text-xs text-slate-500 mb-4">
          Get personalized AI analysis of your group's spending patterns and financial health.
        </p>
        <button onClick={fetchAI} className="btn-primary flex items-center gap-2 text-sm">
          <Zap className="w-3.5 h-3.5" /> Generate AI Insights
        </button>
      </div>
    );
  }

  if (loading) return (
    <div className="ai-insight-card flex items-center gap-3">
      <div className="w-5 h-5 border-2 border-brand-200 border-t-brand-500 rounded-full animate-spin flex-shrink-0" />
      <p className="text-sm text-slate-600">Gemini is analyzing your group data...</p>
    </div>
  );

  if (!aiData?.success) return (
    <div className="ai-insight-card">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-slate-400" />
          <p className="text-sm font-semibold text-slate-600">AI Insights</p>
        </div>
        <button onClick={fetchAI} className="text-xs text-brand-600 hover:underline flex items-center gap-1">
          <RefreshCw className="w-3 h-3" /> Retry
        </button>
      </div>
      <p className="text-xs text-slate-500">
        {aiData?.error || 'AI insights are temporarily unavailable.'}
      </p>
    </div>
  );

  return (
    <div className="ai-insight-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-gradient flex items-center justify-center shadow-brand">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="font-bold text-slate-900 text-sm">AI Group Insights</p>
            <p className="text-[10px] text-brand-500 font-medium">Powered by Gemini</p>
          </div>
        </div>
        <button onClick={fetchAI} className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1">
          <RefreshCw className="w-3 h-3" />
        </button>
      </div>

      {aiData.summary && (
        <p className="text-sm text-slate-700 font-medium leading-relaxed mb-4 pb-4 border-b border-violet-100/60">
          {aiData.summary}
        </p>
      )}

      {aiData.insights?.length > 0 && (
        <ul className="space-y-2">
          {aiData.insights.map((insight, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
              <span className="text-brand-500 font-black mt-0.5 flex-shrink-0">✦</span>
              {insight}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function GroupInsightsPage() {
  const { groupId } = useParams();
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchInsights = useCallback(async () => {
    try {
      setError(null);
      const data = await insightsApi.getGroupInsights(groupId);
      setInsights(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => { fetchInsights(); }, [fetchInsights]);

  if (loading) return <LoadingSpinner message="Calculating insights..." />;
  if (error) return (
    <div className="space-y-4">
      <ErrorMessage message={error} onRetry={fetchInsights} />
      <p className="text-xs text-slate-400 text-center">
        Insights couldn't be loaded. Check your connection and try again.
      </p>
    </div>
  );

  if (!insights) return null;

  const noExpenses = insights.expense_count === 0;
  const userNet = Number(insights.user_net_balance);
  const memberChartData = insights.member_spending.map(m => ({
    name: m.name.split(' ')[0],
    paid: m.paid,
    share: m.share,
  }));

  return (
    <div className="space-y-6 fade-up">
      {/* No data state */}
      {noExpenses ? (
        <div className="glass-card p-8 text-center">
          <div className="text-4xl mb-3">📊</div>
          <h3 className="font-bold text-slate-800 mb-2">No expense data yet</h3>
          <p className="text-slate-500 text-sm">
            Add your first expense to start seeing group insights.
          </p>
          <Link to={`/groups/${groupId}/expenses`} className="btn-primary inline-flex mt-4">
            Add Expense
          </Link>
        </div>
      ) : (
        <>
          {/* ── Key stats ── */}
          <div>
            <p className="section-title">Key Statistics</p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <InsightCard
                title="Total Spending"
                value={formatCurrency(insights.total_spent)}
                subtext={`${insights.expense_count} expense${insights.expense_count !== 1 ? 's' : ''}`}
                icon={<Receipt className="w-3.5 h-3.5 text-brand-600" />}
                colorClass="bg-brand-100/80"
              />
              <InsightCard
                title="Avg. Expense"
                value={formatCurrency(insights.avg_expense)}
                subtext="Per expense"
                icon={<BarChart2 className="w-3.5 h-3.5 text-violet-600" />}
                colorClass="bg-violet-100/80"
              />
              <InsightCard
                title="Largest Expense"
                value={formatCurrency(insights.max_expense)}
                subtext={insights.max_expense_description?.slice(0, 20) || ''}
                icon={<Target className="w-3.5 h-3.5 text-orange-500" />}
                colorClass="bg-orange-100/80"
              />
              <InsightCard
                title="You Paid"
                value={formatCurrency(insights.user_paid)}
                subtext="Total payments"
                icon={<TrendingUp className="w-3.5 h-3.5 text-emerald-600" />}
                colorClass="bg-emerald-100/80"
              />
              <InsightCard
                title="Your Share"
                value={formatCurrency(insights.user_share)}
                subtext="Total owed"
                icon={<TrendingDown className="w-3.5 h-3.5 text-slate-500" />}
                colorClass="bg-slate-100/80"
              />
              <InsightCard
                title="Net Position"
                value={`${userNet >= 0 ? '+' : '-'}${formatCurrency(userNet)}`}
                subtext={userNet > 0.005 ? 'You\'re owed' : userNet < -0.005 ? 'You owe' : 'Settled!'}
                colorClass={userNet >= 0 ? 'bg-emerald-100/80' : 'bg-red-100/80'}
              />
            </div>
          </div>

          {/* ── Top spender ── */}
          {insights.top_spender_name && (
            <div className="glass-card p-4 flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center flex-shrink-0">
                <Award className="w-4.5 h-4.5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-slate-400">Top Contributor</p>
                <p className="font-bold text-slate-900">
                  {insights.top_spender_name}
                  <span className="ml-2 font-normal text-slate-500 text-sm">
                    paid {formatCurrency(insights.top_spender_amount)} total
                  </span>
                </p>
              </div>
            </div>
          )}

          {/* ── Settlement status ── */}
          <div className={`glass-card p-4 flex items-center gap-3 ${
            insights.is_settled
              ? 'border border-emerald-200/50 bg-emerald-50/30'
              : 'border border-orange-200/50 bg-orange-50/30'
          }`}>
            {insights.is_settled ? (
              <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0" />
            )}
            <p className="text-sm font-medium text-slate-700">
              {insights.is_settled
                ? 'All balances are settled — everyone is square!'
                : `Group has outstanding balances. ${insights.settlement_count > 0
                    ? `${insights.settlement_count} settlement${insights.settlement_count !== 1 ? 's' : ''} recorded.`
                    : 'No settlements recorded yet.'}`}
            </p>
          </div>

          {/* ── Monthly trend chart ── */}
          {insights.monthly_trend?.length > 0 && (
            <div className="glass-card p-6">
              <div className="flex items-center gap-2 mb-5">
                <BarChart2 className="w-4 h-4 text-brand-600" />
                <h3 className="font-bold text-slate-900">Monthly Spending Trend</h3>
              </div>
              {insights.monthly_trend.every(m => m.total === 0) ? (
                <ChartEmpty message="No spending data in the last 6 months" />
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={insights.monthly_trend} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.15} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                      tickFormatter={v => `₹${v >= 1000 ? (v/1000).toFixed(0)+'k' : v}`} />
                    <Tooltip content={<CurrencyTooltip />} />
                    <Area type="monotone" dataKey="total" stroke="#6366f1" strokeWidth={2.5}
                      fill="url(#trendGrad)" dot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }}
                      activeDot={{ r: 6, fill: '#4338ca', strokeWidth: 0 }} />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>
          )}

          {/* ── Member spending chart ── */}
          {memberChartData.length > 0 && (
            <div className="glass-card p-6">
              <div className="flex items-center gap-2 mb-5">
                <Users className="w-4 h-4 text-violet-600" />
                <h3 className="font-bold text-slate-900">Member Spending</h3>
              </div>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={memberChartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false}
                    tickFormatter={v => `₹${v >= 1000 ? (v/1000).toFixed(0)+'k' : v}`} />
                  <Tooltip content={<CurrencyTooltip />} />
                  <Bar dataKey="paid" name="Paid" radius={[6, 6, 0, 0]}>
                    {memberChartData.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} opacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              {/* Member breakdown table */}
              <div className="mt-4 pt-4 border-t border-slate-100/60">
                <div className="space-y-2">
                  {insights.member_spending.map(m => (
                    <div key={m.user_id} className="flex items-center justify-between text-sm py-1">
                      <span className="font-semibold text-slate-800">{m.name}</span>
                      <div className="flex gap-6 text-xs text-slate-500">
                        <span>Paid <span className="font-bold text-slate-700">{formatCurrency(m.paid)}</span></span>
                        <span>Share <span className="font-bold text-slate-700">{formatCurrency(m.share)}</span></span>
                        <span className={`font-bold ${m.net > 0.005 ? 'text-emerald-600' : m.net < -0.005 ? 'text-red-500' : 'text-slate-400'}`}>
                          {m.net > 0.005 ? `+${formatCurrency(m.net)}` : m.net < -0.005 ? `-${formatCurrency(m.net)}` : '✓ Settled'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── AI Insights ── */}
          <div>
            <p className="section-title">AI Analysis</p>
            <AIInsightsPanel groupId={groupId} stats={{
              total_spent: insights.total_spent,
              expense_count: insights.expense_count,
              avg_expense: insights.avg_expense,
              max_expense: insights.max_expense,
              max_expense_description: insights.max_expense_description,
              top_spender_name: insights.top_spender_name,
              top_spender_amount: insights.top_spender_amount,
              user_paid: insights.user_paid,
              user_share: insights.user_share,
              user_net_balance: insights.user_net_balance,
              is_settled: insights.is_settled,
              settlement_count: insights.settlement_count,
            }} />
          </div>
        </>
      )}
    </div>
  );
}
