import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, DollarSign, Users,
  Receipt, ArrowRight, AlertCircle
} from 'lucide-react';
import { dashboardApi } from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/UI';
import { useAuth } from '../contexts/AuthContext';

function formatCurrency(amount) {
  return `₹${Math.abs(Number(amount)).toFixed(2)}`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function StatCard({ icon, label, value, color, sublabel }) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${color}`}>
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
        {sublabel && <p className="text-xs text-gray-400 mt-0.5">{sublabel}</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboard = async () => {
    try {
      setError(null);
      const res = await dashboardApi.get();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchDashboard(); }, []);

  if (loading) return <LoadingSpinner message="Loading dashboard..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchDashboard} />;

  const net = Number(data?.net_balance ?? 0);
  const youOwe = Number(data?.you_owe ?? 0);
  const youAreOwed = Number(data?.you_are_owed ?? 0);

  return (
    <div className="space-y-8">
      {/* Welcome */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome back, {user?.name?.split(' ')[0]} 👋
        </h1>
        <p className="text-gray-500 mt-1">Here's your financial summary</p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Users className="w-5 h-5 text-blue-600" />}
          label="Total Groups"
          value={data?.total_groups ?? 0}
          color="bg-blue-50"
          sublabel="Groups you're in"
        />
        <StatCard
          icon={<TrendingDown className="w-5 h-5 text-red-600" />}
          label="You Owe"
          value={formatCurrency(youOwe)}
          color="bg-red-50"
          sublabel="Across all groups"
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5 text-green-600" />}
          label="You're Owed"
          value={formatCurrency(youAreOwed)}
          color="bg-green-50"
          sublabel="Across all groups"
        />
        <StatCard
          icon={<DollarSign className={`w-5 h-5 ${net >= 0 ? 'text-green-600' : 'text-red-600'}`} />}
          label="Net Balance"
          value={`${net >= 0 ? '+' : '-'}${formatCurrency(net)}`}
          color={net >= 0 ? 'bg-green-50' : 'bg-red-50'}
          sublabel={net > 0 ? 'You get back' : net < 0 ? 'You owe overall' : 'All settled!'}
        />
      </div>

      {/* Net balance alert */}
      {net < 0 && (
        <div className="flex items-start gap-3 p-4 bg-orange-50 border border-orange-200 rounded-xl">
          <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-orange-800">
            You owe a net of <strong>{formatCurrency(net)}</strong> across your groups.{' '}
            <Link to="/groups" className="underline font-medium hover:text-orange-900">View groups →</Link>
          </p>
        </div>
      )}
      {net > 0 && (
        <div className="flex items-start gap-3 p-4 bg-green-50 border border-green-200 rounded-xl">
          <TrendingUp className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-green-800">
            Others owe you a net of <strong>{formatCurrency(net)}</strong>. You're doing great!
          </p>
        </div>
      )}

      {/* Two column: recent expenses + groups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Expenses */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Receipt className="w-5 h-5 text-gray-400" />
              Recent Expenses
            </h2>
          </div>
          {!data?.recent_expenses?.length ? (
            <p className="text-sm text-gray-400 text-center py-6">No recent expenses</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {data.recent_expenses.slice(0, 6).map((exp) => (
                <li key={exp.id} className="py-3 flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{exp.description}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {exp.payer_name} · {formatDate(exp.created_at)}
                    </p>
                  </div>
                  <span className="text-sm font-semibold text-gray-700 flex-shrink-0">
                    {formatCurrency(exp.amount)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Groups */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Users className="w-5 h-5 text-gray-400" />
              Your Groups
            </h2>
            <Link to="/groups" className="text-sm text-blue-600 hover:underline font-medium flex items-center gap-1">
              View all <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
          {!data?.groups?.length ? (
            <div className="text-center py-6">
              <p className="text-sm text-gray-400 mb-3">No groups yet</p>
              <Link to="/groups" className="btn-primary text-sm">
                Create a Group
              </Link>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {data.groups.slice(0, 5).map((g) => (
                <li key={g.id}>
                  <Link
                    to={`/groups/${g.id}`}
                    className="flex items-center justify-between py-3 hover:text-blue-600 transition-colors group"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 group-hover:text-blue-600 truncate">
                        {g.name}
                      </p>
                      <p className="text-xs text-gray-400">
                        {g.member_count} member{g.member_count !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-blue-400 flex-shrink-0" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
