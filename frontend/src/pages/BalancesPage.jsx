import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  CheckCircle, AlertCircle, ArrowRight, Plus, ChevronRight,
  TrendingUp, TrendingDown, Minus, Users, History, Pencil
} from 'lucide-react';
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

const avatarColors = [
  'from-indigo-500 to-violet-600', 'from-emerald-500 to-teal-600',
  'from-orange-500 to-rose-500', 'from-sky-500 to-blue-600',
  'from-pink-500 to-fuchsia-600', 'from-amber-500 to-orange-600',
];
function getAvatarColor(name) {
  return avatarColors[(name || 'A').charCodeAt(0) % avatarColors.length];
}

function SettlementEditForm({ settlement, members, onSave, onCancel, saving }) {
  const [payerId, setPayerId] = useState(
    settlement.payer_id || members.find(m => m.name === settlement.payer_name)?.id || ''
  );
  const [receiverId, setReceiverId] = useState(
    settlement.receiver_id || members.find(m => m.name === settlement.receiver_name)?.id || ''
  );
  const [amount, setAmount] = useState(String(settlement.amount ?? ''));
  const [note, setNote] = useState(settlement.note || '');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!payerId || !receiverId || !amount) {
      toast.error('Please fill in all required fields');
      return;
    }
    if (payerId === receiverId) {
      toast.error('Payer and receiver must be different');
      return;
    }
    if (parseFloat(amount) <= 0) {
      toast.error('Amount must be greater than 0');
      return;
    }
    onSave(settlement.id, {
      payer_id: payerId,
      receiver_id: receiverId,
      amount: parseFloat(amount),
      note: note.trim() || null,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 rounded-xl bg-white/70 border border-brand-200/60 shadow-sm space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="label text-xs">Who paid *</label>
          <select value={payerId} onChange={e => setPayerId(e.target.value)} className="input text-sm" required>
            <option value="">Select payer</option>
            {members.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label text-xs">Paid to *</label>
          <select value={receiverId} onChange={e => setReceiverId(e.target.value)} className="input text-sm" required>
            <option value="">Select receiver</option>
            {members.map(m => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label text-xs">Amount (₹) *</label>
          <input type="number" value={amount} onChange={e => setAmount(e.target.value)}
            className="input text-sm" min="0.01" step="0.01" required />
        </div>
      </div>
      <div>
        <label className="label text-xs">Note (optional)</label>
        <input type="text" value={note} onChange={e => setNote(e.target.value)}
          placeholder="e.g. UPI transfer" className="input text-sm" />
      </div>
      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={saving} className="btn-primary text-xs py-1.5 px-3">
          {saving ? 'Saving...' : 'Save'}
        </button>
        <button type="button" onClick={onCancel} className="btn-secondary text-xs py-1.5 px-3">
          Cancel
        </button>
      </div>
    </form>
  );
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
  const [settleForm, setSettleForm] = useState({ payer_id: '', receiver_id: '', amount: '', note: '' });
  const [submitting, setSubmitting] = useState(false);
  const [editingSettlementId, setEditingSettlementId] = useState(null);
  const [savingSettlement, setSavingSettlement] = useState(false);

  const handleUpdateSettlement = async (settlementId, data) => {
    setSavingSettlement(true);
    try {
      await balancesApi.updateSettlement(settlementId, data);
      toast.success('Settlement updated');
      setEditingSettlementId(null);
      fetchData();
    } catch (err) {
      toast.error(err.message || 'Failed to update settlement');
    } finally {
      setSavingSettlement(false);
    }
  };

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
      toast.error('Please fill all required fields'); return;
    }
    if (settleForm.payer_id === settleForm.receiver_id) {
      toast.error('Payer and receiver must be different'); return;
    }
    setSubmitting(true);
    try {
      await balancesApi.recordSettlement(groupId, {
        payer_id: settleForm.payer_id,
        receiver_id: settleForm.receiver_id,
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

  // Find current user's balance
  const myBalance = balanceData?.balances?.find(b => b.user_id === user?.id);
  const myNet = Number(myBalance?.net_balance ?? 0);

  return (
    <div className="space-y-6 fade-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
        <Link to="/groups" className="hover:text-brand-600 transition-colors">Groups</Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <Link to={`/groups/${groupId}`} className="hover:text-brand-600 transition-colors">
          {group?.name}
        </Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-slate-700 font-semibold">Balances</span>
      </div>

      {/* My Position Hero Card */}
      <div className={`glass-card p-6 border ${
        myNet > 0.005 ? 'border-emerald-200/50 bg-emerald-50/20'
        : myNet < -0.005 ? 'border-red-200/50 bg-red-50/20'
        : 'border-slate-200/50'
      }`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">
              Your Position in {group?.name}
            </p>
            <div className="flex items-center gap-3">
              {myNet > 0.005 ? (
                <>
                  <TrendingUp className="w-6 h-6 text-emerald-600" />
                  <div>
                    <p className="text-3xl font-black text-emerald-700">{formatCurrency(myNet)}</p>
                    <p className="text-sm text-emerald-600 font-semibold">You are owed</p>
                  </div>
                </>
              ) : myNet < -0.005 ? (
                <>
                  <TrendingDown className="w-6 h-6 text-red-500" />
                  <div>
                    <p className="text-3xl font-black text-red-600">{formatCurrency(myNet)}</p>
                    <p className="text-sm text-red-500 font-semibold">You owe</p>
                  </div>
                </>
              ) : (
                <>
                  <CheckCircle className="w-6 h-6 text-emerald-500" />
                  <div>
                    <p className="text-3xl font-black text-slate-600">₹0.00</p>
                    <p className="text-sm text-emerald-600 font-semibold">Settled ✓</p>
                  </div>
                </>
              )}
            </div>
            {myBalance && (
              <p className="text-xs text-slate-400 mt-2 font-medium">
                Paid {formatCurrency(myBalance.total_paid)} · Owed {formatCurrency(myBalance.total_owed)}
              </p>
            )}
          </div>
          <button
            onClick={() => setShowSettleForm(!showSettleForm)}
            className="btn-primary flex items-center gap-2 flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
            Record Settlement
          </button>
        </div>
      </div>

      {/* Group Status */}
      {balanceData && (
        <div className={`glass-card p-4 flex items-center gap-3 border ${
          balanceData.is_settled
            ? 'border-emerald-200/50 bg-emerald-50/30'
            : 'border-orange-200/50 bg-orange-50/30'
        }`}>
          {balanceData.is_settled ? (
            <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0" />
          )}
          <p className="text-sm font-semibold text-slate-800">
            {balanceData.is_settled
              ? 'All settled! No outstanding debts in this group.'
              : `${balanceData.settlement_suggestions?.length ?? 0} settlement${
                  (balanceData.settlement_suggestions?.length ?? 0) !== 1 ? 's' : ''
                } needed to clear all balances.`}
          </p>
        </div>
      )}

      {/* Settlement Form */}
      {showSettleForm && (
        <div className="glass-card-elevated p-6 border border-emerald-200/40 fade-up">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-xl bg-success-gradient flex items-center justify-center shadow-success">
              <CheckCircle className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Record Settlement</h2>
          </div>
          <form onSubmit={handleRecordSettlement} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="label">Who paid *</label>
                <select value={settleForm.payer_id}
                  onChange={(e) => setSettleForm(p => ({ ...p, payer_id: e.target.value }))}
                  className="input" required>
                  <option value="">Select payer</option>
                  {members.map(m => (
                    <option key={m.id} value={m.id}>{m.name}{m.id === user?.id ? ' (You)' : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Paid to *</label>
                <select value={settleForm.receiver_id}
                  onChange={(e) => setSettleForm(p => ({ ...p, receiver_id: e.target.value }))}
                  className="input" required>
                  <option value="">Select receiver</option>
                  {members.map(m => (
                    <option key={m.id} value={m.id}>{m.name}{m.id === user?.id ? ' (You)' : ''}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Amount (₹) *</label>
                <input type="number" value={settleForm.amount}
                  onChange={(e) => setSettleForm(p => ({ ...p, amount: e.target.value }))}
                  placeholder="0.00" className="input" min="0.01" step="0.01" required />
              </div>
            </div>
            <div>
              <label className="label">Note (optional)</label>
              <input type="text" value={settleForm.note}
                onChange={(e) => setSettleForm(p => ({ ...p, note: e.target.value }))}
                placeholder="e.g. UPI transfer" className="input" />
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

      {/* Net Balances Grid */}
      {balanceData?.balances?.length > 0 && (
        <div className="glass-card p-6">
          <h2 className="font-bold text-slate-900 flex items-center gap-2 mb-5">
            <Users className="w-4 h-4 text-slate-400" />
            Member Balances
          </h2>
          <div className="space-y-3">
            {balanceData.balances
              .sort((a, b) => b.net_balance - a.net_balance)
              .map(b => {
                const net = Number(b.net_balance);
                const isCurrentUser = b.user_id === user?.id;
                return (
                  <div key={b.user_id}
                    className={`flex items-center justify-between p-3 rounded-xl transition-colors ${
                      isCurrentUser
                        ? 'bg-brand-50/60 border border-brand-100/60'
                        : 'bg-slate-50/40 hover:bg-slate-50/70'
                    }`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-9 h-9 rounded-full flex items-center justify-center
                                       bg-gradient-to-br ${getAvatarColor(b.member_name)} shadow-sm`}>
                        <span className="text-white font-bold text-sm">
                          {b.member_name?.charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div>
                        <p className="font-semibold text-slate-900 text-sm flex items-center gap-1.5">
                          {b.member_name}
                          {isCurrentUser && <span className="badge-indigo text-[10px]">You</span>}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          Paid {formatCurrency(b.total_paid)} · Owes {formatCurrency(b.total_owed)}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      {net > 0.005 ? (
                        <div className="flex items-center gap-1">
                          <TrendingUp className="w-3.5 h-3.5 text-emerald-600" />
                          <div>
                            <p className="font-black text-emerald-700 text-base">{formatCurrency(net)}</p>
                            <p className="text-[10px] text-emerald-600 font-semibold">gets back</p>
                          </div>
                        </div>
                      ) : net < -0.005 ? (
                        <div className="flex items-center gap-1">
                          <TrendingDown className="w-3.5 h-3.5 text-red-500" />
                          <div>
                            <p className="font-black text-red-600 text-base">{formatCurrency(net)}</p>
                            <p className="text-[10px] text-red-500 font-semibold">owes</p>
                          </div>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <Minus className="w-3.5 h-3.5 text-slate-400" />
                          <div>
                            <p className="font-black text-slate-400 text-base">₹0.00</p>
                            <p className="text-[10px] text-slate-400 font-semibold">settled</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Suggested Settlements */}
      {balanceData?.settlement_suggestions?.length > 0 && (
        <div className="glass-card p-6">
          <h2 className="font-bold text-slate-900 flex items-center gap-2 mb-4">
            <ArrowRight className="w-4 h-4 text-slate-400" />
            Suggested Settlements
          </h2>
          <div className="space-y-2">
            {balanceData.settlement_suggestions.map((s, i) => {
              const involvesCurrent = s.from_user_id === user?.id || s.to_user_id === user?.id;
              return (
                <div key={i}
                  className={`flex items-center justify-between p-4 rounded-xl ${
                    involvesCurrent
                      ? 'bg-brand-50/60 border border-brand-100/60'
                      : 'bg-slate-50/50'
                  }`}>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`font-semibold text-sm ${
                      s.from_user_id === user?.id ? 'text-brand-700' : 'text-slate-800'
                    }`}>
                      {s.from_member_name}
                      {s.from_user_id === user?.id && ' (You)'}
                    </span>
                    <ArrowRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
                    <span className={`font-semibold text-sm ${
                      s.to_user_id === user?.id ? 'text-emerald-700' : 'text-slate-800'
                    }`}>
                      {s.to_member_name}
                      {s.to_user_id === user?.id && ' (You)'}
                    </span>
                    <span className="font-black text-emerald-700 text-sm ml-1">
                      {formatCurrency(s.amount)}
                    </span>
                  </div>
                  <button onClick={() => handleUseSuggestion(s)}
                    className="btn-secondary text-xs py-1.5 px-3 flex-shrink-0">
                    Record
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Settlement History */}
      <div className="glass-card p-6">
        <h2 className="font-bold text-slate-900 flex items-center gap-2 mb-4">
          <History className="w-4 h-4 text-slate-400" />
          Settlement History
        </h2>
        {settlements.length === 0 ? (
          <p className="text-slate-400 text-sm text-center py-6">No settlements recorded yet</p>
        ) : (
          <div className="space-y-2">
            {settlements.map(s => (
              editingSettlementId === s.id ? (
                <SettlementEditForm
                  key={s.id}
                  settlement={s}
                  members={members}
                  onSave={handleUpdateSettlement}
                  onCancel={() => setEditingSettlementId(null)}
                  saving={savingSettlement}
                />
              ) : (
                <div key={s.id}
                  className="flex items-center justify-between py-3 px-3 rounded-xl
                             hover:bg-slate-50/50 transition-colors">
                  <div>
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-semibold text-slate-900">{s.payer_name}</span>
                      <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
                      <span className="font-semibold text-slate-900">{s.receiver_name}</span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {formatDate(s.created_at)}{s.note ? ` · ${s.note}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-black text-slate-700">{formatCurrency(s.amount)}</span>
                    <button
                      onClick={() => setEditingSettlementId(s.id)}
                      className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
                      title="Edit settlement"
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
