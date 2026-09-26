import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { CheckCircle, AlertCircle, ArrowRight, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi, balancesApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, EmptyState } from '../components/common/UI';
import { useAuth } from '../contexts/AuthContext';

function formatCurrency(amount) {
  return `₹${Math.abs(Number(amount)).toFixed(2)}`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

export default function BalancesPage() {
  const { groupId } = useParams();
  const { user } = useAuth();
  const [group, setGroup] = useState(null);
  const [balanceData, setBalanceData] = useState(null);
  const [settlements, setSettlements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showSettleForm, setShowSettleForm] = useState(false);
  // payer_id / receiver_id are MongoDB ObjectId strings
  const [settleForm, setSettleForm] = useState({ payer_id: '', receiver_id: '', amount: '', note: '' });
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [groupData, balances, settlementsData] = await Promise.all([
        groupsApi.get(groupId),
        balancesApi.getBalances(groupId),
        balancesApi.listSettlements(groupId),
      ]);
      setGroup(groupData);
      setBalanceData(balances);
      setSettlements(settlementsData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleRecordSettlement = async (e) => {
    e.preventDefault();
    if (!settleForm.payer_id || !settleForm.receiver_id || !settleForm.amount) {
      toast.error('Please fill all required fields');
      return;
    }
    if (settleForm.payer_id === settleForm.receiver_id) {
      toast.error('Payer and receiver must be different');
      return;
    }
    setSubmitting(true);
    try {
      await balancesApi.recordSettlement(groupId, {
        payer_id: settleForm.payer_id,       // MongoDB ObjectId string
        receiver_id: settleForm.receiver_id,  // MongoDB ObjectId string
        amount: parseFloat(settleForm.amount),
        note: settleForm.note || null,
      });
      toast.success('Settlement recorded!');
      setShowSettleForm(false);
      setSettleForm({ payer_id: '', receiver_id: '', amount: '', note: '' });
      fetchData();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  // Pre-fill settlement form from a suggestion
  // Suggestion: { from_user_id, from_member_name, to_user_id, to_member_name, amount }
  const handleUseSuggestion = (suggestion) => {
    setSettleForm({
      payer_id: suggestion.from_user_id,
      receiver_id: suggestion.to_user_id,
      amount: suggestion.amount.toFixed(2),
      note: '',
    });
    setShowSettleForm(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (loading) return <LoadingSpinner message="Calculating balances..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchData} />;

  const members = group?.members || [];

  return (
    <div>
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-6">
        <Link to="/groups" className="hover:text-blue-600">Groups</Link>
        <span className="mx-2">/</span>
        <Link to={`/groups/${groupId}`} className="hover:text-blue-600">{group?.name}</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">Balances</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Balances</h1>
        <button
          onClick={() => setShowSettleForm(!showSettleForm)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Record Settlement
        </button>
      </div>

      {/* Settlement Form */}
      {showSettleForm && (
        <div className="card mb-6 border-green-200 bg-green-50">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Record Settlement</h2>
          <form onSubmit={handleRecordSettlement} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="label">Who paid *</label>
                <select
                  value={settleForm.payer_id}
                  onChange={(e) => setSettleForm((p) => ({ ...p, payer_id: e.target.value }))}
                  className="input"
                  required
                >
                  <option value="">Select payer</option>
                  {members.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}{m.id === user?.id ? ' (You)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Paid to *</label>
                <select
                  value={settleForm.receiver_id}
                  onChange={(e) => setSettleForm((p) => ({ ...p, receiver_id: e.target.value }))}
                  className="input"
                  required
                >
                  <option value="">Select receiver</option>
                  {members.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.name}{m.id === user?.id ? ' (You)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Amount (₹) *</label>
                <input
                  type="number"
                  value={settleForm.amount}
                  onChange={(e) => setSettleForm((p) => ({ ...p, amount: e.target.value }))}
                  placeholder="0.00"
                  className="input"
                  min="0.01"
                  step="0.01"
                  required
                />
              </div>
            </div>
            <div>
              <label className="label">Note (optional)</label>
              <input
                type="text"
                value={settleForm.note}
                onChange={(e) => setSettleForm((p) => ({ ...p, note: e.target.value }))}
                placeholder="e.g. UPI transfer"
                className="input"
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={submitting} className="btn-success">
                {submitting ? 'Recording...' : 'Record Settlement'}
              </button>
              <button type="button" onClick={() => setShowSettleForm(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Overall Status */}
      {balanceData && (
        <div className={`card mb-6 ${balanceData.is_settled ? 'border-green-300 bg-green-50' : 'border-orange-200 bg-orange-50'}`}>
          <div className="flex items-center gap-3">
            {balanceData.is_settled ? (
              <>
                <CheckCircle className="w-6 h-6 text-green-600" />
                <p className="font-semibold text-green-800">All settled! No outstanding debts.</p>
              </>
            ) : (
              <>
                <AlertCircle className="w-6 h-6 text-orange-500" />
                <p className="font-semibold text-orange-800">
                  {balanceData.settlement_suggestions?.length ?? 0} settlement
                  {(balanceData.settlement_suggestions?.length ?? 0) !== 1 ? 's' : ''} needed
                </p>
              </>
            )}
          </div>
        </div>
      )}

      {/* Net Balances — uses user_id and member_name from new API */}
      {balanceData && balanceData.balances?.length > 0 && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Net Balances</h2>
          <div className="space-y-3">
            {balanceData.balances
              .sort((a, b) => b.net_balance - a.net_balance)
              .map((b) => {
                const net = Number(b.net_balance);
                const isCurrentUser = b.user_id === user?.id;
                return (
                  <div
                    key={b.user_id}
                    className={`flex items-center justify-between py-2 border-b border-gray-100 last:border-0 ${
                      isCurrentUser ? 'bg-blue-50/40 -mx-2 px-2 rounded-lg' : ''
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center ${
                        isCurrentUser ? 'bg-blue-100' : 'bg-gray-100'
                      }`}>
                        <span className={`font-semibold text-sm ${
                          isCurrentUser ? 'text-blue-700' : 'text-gray-700'
                        }`}>
                          {b.member_name?.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {b.member_name}
                          {isCurrentUser && (
                            <span className="ml-1.5 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">You</span>
                          )}
                        </p>
                        <p className="text-xs text-gray-400">
                          Paid {formatCurrency(b.total_paid)} · Owes {formatCurrency(b.total_owed)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`font-bold text-lg ${net > 0 ? 'text-green-600' : net < 0 ? 'text-red-600' : 'text-gray-400'}`}>
                        {net > 0 ? '+' : ''}{formatCurrency(net)}
                      </span>
                      <p className="text-xs">
                        {net > 0
                          ? <span className="text-green-600">gets back</span>
                          : net < 0
                          ? <span className="text-red-600">owes</span>
                          : <span className="text-gray-400">settled</span>}
                      </p>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Settlement Suggestions — uses from_user_id / to_user_id */}
      {balanceData && balanceData.settlement_suggestions?.length > 0 && (
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Suggested Settlements</h2>
          <div className="space-y-3">
            {balanceData.settlement_suggestions.map((s, i) => {
              const involvesCurrent =
                s.from_user_id === user?.id || s.to_user_id === user?.id;
              return (
                <div
                  key={i}
                  className={`flex items-center justify-between p-3 rounded-lg ${
                    involvesCurrent ? 'bg-blue-50 border border-blue-100' : 'bg-gray-50'
                  }`}
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`font-medium ${s.from_user_id === user?.id ? 'text-blue-700' : 'text-gray-900'}`}>
                      {s.from_member_name}
                      {s.from_user_id === user?.id && ' (You)'}
                    </span>
                    <ArrowRight className="w-4 h-4 text-gray-400" />
                    <span className={`font-medium ${s.to_user_id === user?.id ? 'text-green-700' : 'text-gray-900'}`}>
                      {s.to_member_name}
                      {s.to_user_id === user?.id && ' (You)'}
                    </span>
                    <span className="font-bold text-green-700 ml-1">{formatCurrency(s.amount)}</span>
                  </div>
                  <button
                    onClick={() => handleUseSuggestion(s)}
                    className="btn-secondary text-xs py-1 px-3 flex-shrink-0"
                  >
                    Record
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Settlement History */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Settlement History</h2>
        {settlements.length === 0 ? (
          <p className="text-gray-400 text-sm text-center py-4">No settlements recorded yet</p>
        ) : (
          <div className="space-y-2">
            {settlements.map((s) => (
              <div key={s.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                <div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-medium text-gray-900">{s.payer_name}</span>
                    <span className="text-gray-400">→</span>
                    <span className="font-medium text-gray-900">{s.receiver_name}</span>
                  </div>
                  <p className="text-xs text-gray-400">
                    {formatDate(s.created_at)}{s.note ? ` · ${s.note}` : ''}
                  </p>
                </div>
                <span className="font-semibold text-gray-700">{formatCurrency(s.amount)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
