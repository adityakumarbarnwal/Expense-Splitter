import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useLocation } from 'react-router-dom';
import {
  Plus, Trash2, Sparkles, ChevronDown, ChevronUp, ChevronRight,
  Receipt, Pencil, Check, X
} from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi, expensesApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, EmptyState } from '../components/common/UI';
import AIConfirmationCard from '../components/ai/AIConfirmationCard';
import NaturalLanguageInput from '../components/ai/NaturalLanguageInput';
import { useAuth } from '../contexts/AuthContext';

function formatCurrency(amount) {
  return `₹${Number(amount).toFixed(2)}`;
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

// ── Inline Edit Form ──
function ExpenseEditForm({ expense, members, currentUserId, onSaved, onCancel, saving }) {
  const [description, setDescription] = useState(expense.description);
  const [amount, setAmount] = useState(String(expense.amount));
  const [payerId, setPayerId] = useState(expense.payer_id);
  const [participantIds, setParticipantIds] = useState(
    expense.participants?.map(p => p.user_id) || []
  );
  const [note, setNote] = useState(expense.note || '');

  const toggleParticipant = (id) => {
    setParticipantIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!description.trim() || !amount || !payerId || participantIds.length === 0) {
      toast.error('Fill in all required fields and select at least one participant');
      return;
    }
    onSaved({
      description: description.trim(),
      amount: parseFloat(amount),
      payer_id: payerId,
      participant_ids: participantIds,
      note: note.trim() || null,
    });
  };

  const perPerson = participantIds.length > 0 && amount
    ? (parseFloat(amount) / participantIds.length).toFixed(2)
    : null;

  return (
    <form onSubmit={handleSubmit} className="space-y-4 pt-4 border-t border-brand-100/60 mt-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="label text-xs">Description *</label>
          <input type="text" value={description}
            onChange={e => setDescription(e.target.value)}
            className="input text-sm" required maxLength={500} autoFocus />
        </div>
        <div>
          <label className="label text-xs">Amount (₹) *</label>
          <input type="number" value={amount}
            onChange={e => setAmount(e.target.value)}
            className="input text-sm" min="0.01" step="0.01" required />
        </div>
      </div>
      <div>
        <label className="label text-xs">Paid by *</label>
        <select value={payerId} onChange={e => setPayerId(e.target.value)}
          className="input text-sm" required>
          {members.map(m => (
            <option key={m.id} value={m.id}>{m.name}{m.id === currentUserId ? ' (You)' : ''}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="label text-xs">Split between *</label>
        <div className="flex flex-wrap gap-1.5 mt-1">
          {members.map(m => (
            <button key={m.id} type="button"
              onClick={() => toggleParticipant(m.id)}
              className={`px-2.5 py-1 rounded-full text-xs font-semibold border transition-all ${
                participantIds.includes(m.id)
                  ? 'bg-brand-gradient text-white border-transparent shadow-sm'
                  : 'bg-white/60 text-slate-700 border-slate-200 hover:border-brand-300'
              }`}>
              {m.name}{m.id === currentUserId ? ' (You)' : ''}
            </button>
          ))}
        </div>
        {perPerson && (
          <p className="text-xs text-slate-500 mt-1">
            Each pays: <span className="font-bold text-slate-700">₹{perPerson}</span>
          </p>
        )}
      </div>
      <div>
        <label className="label text-xs">Note (optional)</label>
        <input type="text" value={note} onChange={e => setNote(e.target.value)}
          className="input text-sm" maxLength={500} />
      </div>
      <div className="flex gap-2 pt-1">
        <button type="submit" disabled={saving}
          className="btn-primary flex items-center gap-1.5 text-sm py-1.5">
          {saving ? 'Saving...' : <><Check className="w-3.5 h-3.5" /> Save</>}
        </button>
        <button type="button" onClick={onCancel}
          className="btn-secondary flex items-center gap-1.5 text-sm py-1.5">
          <X className="w-3.5 h-3.5" /> Cancel
        </button>
      </div>
    </form>
  );
}

// ── Expense Card ──
function ExpenseCard({ expense, members, currentUserId, onDelete, onEdit }) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const isPayer = expense.payer_id === currentUserId;
  const isCreator = expense.created_by === currentUserId;

  const handleSaveEdit = async (data) => {
    setSaving(true);
    try {
      await onEdit(expense.id, data);
      setEditing(false);
      setExpanded(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="glass-card p-5 hover:shadow-glass-hover transition-all">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0
                           bg-gradient-to-br ${getAvatarColor(expense.payer_name || 'A')}`}>
            <Receipt className="w-4 h-4 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-bold text-slate-900 truncate">{expense.description}</p>
              {isPayer && (
                <span className="badge-indigo text-[10px] flex-shrink-0">You paid</span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Paid by <span className="font-semibold text-slate-600">{expense.payer_name}</span>
              {' · '}{formatDate(expense.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 flex-shrink-0">
          <span className="text-lg font-black text-slate-900">{formatCurrency(expense.amount)}</span>
          {!editing && (
            <button onClick={() => { setEditing(true); setExpanded(true); }}
              className="p-1.5 text-slate-300 hover:text-brand-600 hover:bg-brand-50 rounded-lg transition-colors"
              title="Edit expense">
              <Pencil className="w-3.5 h-3.5" />
            </button>
          )}
          <button onClick={() => setExpanded(e => !e)}
            className="p-1.5 text-slate-300 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button onClick={() => onDelete(expense)}
            className="p-1.5 text-slate-200 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            title="Delete expense">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {expanded && !editing && expense.participants?.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-100/60">
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
            Split Details
          </p>
          <div className="space-y-1.5">
            {expense.participants.map(p => (
              <div key={p.user_id || p.id}
                className="flex justify-between items-center text-sm py-0.5">
                <span className={`${p.user_id === currentUserId ? 'font-bold text-brand-700' : 'text-slate-600'}`}>
                  {p.name}{p.user_id === currentUserId ? ' (You)' : ''}
                </span>
                <span className="font-semibold text-slate-900">{formatCurrency(p.share)}</span>
              </div>
            ))}
          </div>
          {expense.note && (
            <p className="text-xs text-slate-400 mt-3 italic border-t border-slate-100/60 pt-2">
              {expense.note}
            </p>
          )}
        </div>
      )}

      {/* Inline edit form — only creator can see */}
      {editing && (
        <ExpenseEditForm
          expense={expense}
          members={members}
          currentUserId={currentUserId}
          onSaved={handleSaveEdit}
          onCancel={() => { setEditing(false); }}
          saving={saving}
        />
      )}
    </div>
  );
}

// ── Main Page ──
export default function ExpensesPage() {
  const { groupId } = useParams();
  const { user } = useAuth();
  const location = useLocation();
  const [group, setGroup] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showManualForm, setShowManualForm] = useState(false);
  const [showAIInput, setShowAIInput] = useState(false);
  const [aiResult, setAIResult] = useState(null);
  const [aiOriginalText, setAIOriginalText] = useState('');
  const [aiWarnings, setAIWarnings] = useState([]);

  const [formData, setFormData] = useState({
    description: '', amount: '', payer_id: '', participant_ids: [], note: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [groupData, expensesData] = await Promise.all([
        groupsApi.get(groupId),
        expensesApi.list(groupId),
      ]);
      setGroup(groupData);
      setExpenses(expensesData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [groupId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const openManualForm = useCallback(() => {
    const currentMember = group?.members?.find(m => m.id === user?.id);
    setFormData({
      description: '', amount: '',
      payer_id: currentMember?.id || '',
      participant_ids: group?.members?.map(m => m.id) || [],
      note: '',
    });
    setShowManualForm(true);
    setShowAIInput(false);
    setAIResult(null);
  }, [group, user?.id]);

  useEffect(() => {
    if (location.state?.openManual) {
      if (group) {
        openManualForm();
        window.history.replaceState({}, '');
      }
    } else if (location.state?.openAI) {
      setShowAIInput(true);
      window.history.replaceState({}, '');
    }
  }, [group, location.state, openManualForm]);

  const handleParticipantToggle = (memberId) => {
    setFormData(prev => {
      const ids = prev.participant_ids.includes(memberId)
        ? prev.participant_ids.filter(id => id !== memberId)
        : [...prev.participant_ids, memberId];
      return { ...prev, participant_ids: ids };
    });
  };

  const handleSubmitExpense = async (expenseData) => {
    setSubmitting(true);
    try {
      await expensesApi.create(groupId, expenseData);
      toast.success('Expense added!');
      setShowManualForm(false);
      setShowAIInput(false);
      setAIResult(null);
      setFormData({ description: '', amount: '', payer_id: '', participant_ids: [], note: '' });
      fetchData();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleManualSubmit = async (e) => {
    e.preventDefault();
    if (!formData.description || !formData.amount || !formData.payer_id || formData.participant_ids.length === 0) {
      toast.error('Please fill in all required fields and select at least one participant');
      return;
    }
    await handleSubmitExpense({
      description: formData.description,
      amount: parseFloat(formData.amount),
      payer_id: formData.payer_id,
      participant_ids: formData.participant_ids,
      note: formData.note || null,
    });
  };

  const handleAIParsed = (result, originalText, warnings = []) => {
    setAIResult(result);
    setAIOriginalText(originalText);
    setAIWarnings(warnings);
    setShowAIInput(false);
  };

  const handleAIConfirm = async (confirmedData) => {
    const memberByName = Object.fromEntries(
      (group?.members || []).map(m => [m.name.toLowerCase(), m.id])
    );
    const payerId = memberByName[confirmedData.payer_name?.toLowerCase()];
    const participantIds = (confirmedData.participant_names || [])
      .map(name => memberByName[name.toLowerCase()])
      .filter(Boolean);

    if (!payerId) {
      toast.error(`Payer "${confirmedData.payer_name}" not found in group. Please use manual entry.`);
      return;
    }
    if (participantIds.length === 0) {
      toast.error('No valid participants found. Please use manual entry.');
      return;
    }
    await handleSubmitExpense({
      description: confirmedData.description,
      amount: parseFloat(confirmedData.amount),
      payer_id: payerId,
      participant_ids: participantIds,
      note: null,
    });
  };

  const handleEditExpense = async (expenseId, data) => {
    try {
      await expensesApi.update(expenseId, data);
      toast.success('Expense updated!');
      fetchData(); // Re-fetch to get fresh balances (recalculated server-side)
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const handleDeleteExpense = async (expense) => {
    if (!window.confirm(`Delete "${expense.description}"? This will recalculate all balances.`)) return;
    try {
      await expensesApi.delete(expense.id);
      toast.success('Expense deleted');
      fetchData();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (loading) return <LoadingSpinner message="Loading expenses..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchData} />;

  const members = group?.members || [];

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
        <span className="text-slate-700 font-semibold">Expenses</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-black text-slate-900">Expenses</h1>
          <p className="text-slate-500 text-sm mt-0.5 font-medium">
            {expenses.length} expense{expenses.length !== 1 ? 's' : ''} in {group?.name}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowAIInput(!showAIInput); setShowManualForm(false); setAIResult(null); }}
            className="btn-primary flex items-center gap-2"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)' }}
          >
            <Sparkles className="w-4 h-4" />
            AI Entry
          </button>
          <button onClick={openManualForm} className="btn-secondary flex items-center gap-2">
            <Plus className="w-4 h-4" />
            Manual
          </button>
        </div>
      </div>

      {/* AI Input */}
      {showAIInput && (
        <NaturalLanguageInput
          groupId={groupId}
          members={members}
          currentUser={user}
          onParsed={handleAIParsed}
          onCancel={() => setShowAIInput(false)}
        />
      )}

      {/* AI Confirmation */}
      {aiResult && (
        <AIConfirmationCard
          result={aiResult}
          originalText={aiOriginalText}
          warnings={aiWarnings}
          members={members}
          onConfirm={handleAIConfirm}
          onEdit={() => { setAIResult(null); openManualForm(); }}
          onCancel={() => setAIResult(null)}
          submitting={submitting}
        />
      )}

      {/* Manual Form */}
      {showManualForm && (
        <div className="glass-card-elevated p-6 border border-brand-100/60 fade-up">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-xl bg-brand-gradient flex items-center justify-center shadow-brand">
              <Plus className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Add Expense</h2>
          </div>
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Description *</label>
                <input type="text" value={formData.description}
                  onChange={e => setFormData(p => ({ ...p, description: e.target.value }))}
                  placeholder="e.g. Dinner at restaurant"
                  className="input" required autoFocus maxLength={500} />
              </div>
              <div>
                <label className="label">Amount (₹) *</label>
                <input type="number" value={formData.amount}
                  onChange={e => setFormData(p => ({ ...p, amount: e.target.value }))}
                  placeholder="0.00" className="input" min="0.01" step="0.01" required />
              </div>
            </div>

            <div>
              <label className="label">Paid by *</label>
              <select value={formData.payer_id}
                onChange={e => setFormData(p => ({ ...p, payer_id: e.target.value }))}
                className="input" required>
                <option value="">Select who paid</option>
                {members.map(m => (
                  <option key={m.id} value={m.id}>{m.name}{m.id === user?.id ? ' (You)' : ''}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Split between *</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {members.map(m => (
                  <button key={m.id} type="button"
                    onClick={() => handleParticipantToggle(m.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-semibold border transition-all ${
                      formData.participant_ids.includes(m.id)
                        ? 'bg-brand-gradient text-white border-transparent shadow-brand'
                        : 'bg-white/60 text-slate-700 border-slate-200 hover:border-brand-300'
                    }`}>
                    {m.name}{m.id === user?.id ? ' (You)' : ''}
                  </button>
                ))}
              </div>
              {formData.participant_ids.length > 0 && formData.amount && (
                <p className="text-xs text-slate-500 mt-1.5 font-medium">
                  Each pays: <span className="font-bold text-slate-700">
                    ₹{(parseFloat(formData.amount) / formData.participant_ids.length).toFixed(2)}
                  </span>
                </p>
              )}
            </div>

            <div>
              <label className="label">Note (optional)</label>
              <input type="text" value={formData.note}
                onChange={e => setFormData(p => ({ ...p, note: e.target.value }))}
                placeholder="Any additional note" className="input" maxLength={500} />
            </div>

            <div className="flex gap-3 pt-2">
              <button type="submit" disabled={submitting} className="btn-primary">
                {submitting ? 'Adding...' : 'Add Expense'}
              </button>
              <button type="button" onClick={() => setShowManualForm(false)} className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Expense List */}
      {expenses.length === 0 ? (
        <EmptyState
          icon="🧾"
          title="No expenses yet"
          description="Add your first expense using AI or the manual form above"
        />
      ) : (
        <div className="space-y-3 stagger-2">
          {expenses.map((expense, i) => (
            <div key={expense.id} className={`stagger-${Math.min(i + 1, 6)}`}>
              <ExpenseCard
                expense={expense}
                members={members}
                currentUserId={user?.id}
                onDelete={handleDeleteExpense}
                onEdit={handleEditExpense}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
