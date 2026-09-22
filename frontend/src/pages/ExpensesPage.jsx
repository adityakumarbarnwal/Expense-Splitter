import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Plus, Trash2, Sparkles, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi, expensesApi, aiApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, EmptyState } from '../components/common/UI';
import AIConfirmationCard from '../components/ai/AIConfirmationCard';
import NaturalLanguageInput from '../components/ai/NaturalLanguageInput';

function formatCurrency(amount) {
  return `₹${Number(amount).toFixed(2)}`;
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

export default function ExpensesPage() {
  const { groupId } = useParams();
  const [group, setGroup] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Manual form state
  const [showManualForm, setShowManualForm] = useState(false);
  const [showAIInput, setShowAIInput] = useState(false);

  // AI confirmation state
  const [aiResult, setAIResult] = useState(null);
  const [aiOriginalText, setAIOriginalText] = useState('');

  // Manual form fields
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

  const handleParticipantToggle = (memberId) => {
    setFormData((prev) => {
      const ids = prev.participant_ids.includes(memberId)
        ? prev.participant_ids.filter((id) => id !== memberId)
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
      payer_id: parseInt(formData.payer_id),
      participant_ids: formData.participant_ids,
      note: formData.note || null,
    });
  };

  const handleAIParsed = (result, originalText) => {
    setAIResult(result);
    setAIOriginalText(originalText);
    setShowAIInput(false);
  };

  const handleAIConfirm = async (confirmedData) => {
    // Convert member names to IDs
    const memberMap = Object.fromEntries(group.members.map((m) => [m.name, m.id]));
    const payerId = memberMap[confirmedData.payer_name];
    const participantIds = confirmedData.participant_names
      .map((name) => memberMap[name])
      .filter(Boolean);

    if (!payerId) {
      toast.error('Could not resolve payer. Please use manual entry.');
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

  const handleDeleteExpense = async (expense) => {
    if (!window.confirm(`Delete "${expense.description}"?`)) return;
    try {
      await expensesApi.delete(groupId, expense.id);
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
    <div>
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-6">
        <Link to="/" className="hover:text-blue-600">Groups</Link>
        <span className="mx-2">/</span>
        <Link to={`/groups/${groupId}`} className="hover:text-blue-600">{group?.name}</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">Expenses</span>
      </div>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Expenses</h1>
        <div className="flex gap-2">
          <button
            onClick={() => { setShowAIInput(!showAIInput); setShowManualForm(false); setAIResult(null); }}
            className="btn-primary flex items-center gap-2 bg-purple-600 hover:bg-purple-700 focus:ring-purple-500"
          >
            <Sparkles className="w-4 h-4" />
            AI Entry
          </button>
          <button
            onClick={() => { setShowManualForm(!showManualForm); setShowAIInput(false); setAIResult(null); }}
            className="btn-secondary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Manual
          </button>
        </div>
      </div>

      {/* AI Natural Language Input */}
      {showAIInput && (
        <NaturalLanguageInput
          groupId={parseInt(groupId)}
          members={members}
          onParsed={handleAIParsed}
          onCancel={() => setShowAIInput(false)}
        />
      )}

      {/* AI Confirmation Card */}
      {aiResult && (
        <AIConfirmationCard
          result={aiResult}
          originalText={aiOriginalText}
          members={members}
          onConfirm={handleAIConfirm}
          onEdit={() => { setAIResult(null); setShowManualForm(true); }}
          onCancel={() => setAIResult(null)}
          submitting={submitting}
        />
      )}

      {/* Manual Expense Form */}
      {showManualForm && (
        <div className="card mb-6 border-gray-300">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Add Expense</h2>
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">Description *</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
                  placeholder="e.g. Dinner at restaurant"
                  className="input"
                  required
                  maxLength={500}
                />
              </div>
              <div>
                <label className="label">Amount (₹) *</label>
                <input
                  type="number"
                  value={formData.amount}
                  onChange={(e) => setFormData((p) => ({ ...p, amount: e.target.value }))}
                  placeholder="0.00"
                  className="input"
                  min="0.01"
                  step="0.01"
                  required
                />
              </div>
            </div>

            <div>
              <label className="label">Paid by *</label>
              <select
                value={formData.payer_id}
                onChange={(e) => setFormData((p) => ({ ...p, payer_id: parseInt(e.target.value) }))}
                className="input"
                required
              >
                <option value="">Select who paid</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Split between (select participants) *</label>
              <div className="flex flex-wrap gap-2 mt-1">
                {members.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => handleParticipantToggle(m.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                      formData.participant_ids.includes(m.id)
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
              {formData.participant_ids.length > 0 && (
                <p className="text-xs text-gray-500 mt-1">
                  Each pays: {formData.amount
                    ? `₹${(parseFloat(formData.amount) / formData.participant_ids.length).toFixed(2)}`
                    : '—'}
                </p>
              )}
            </div>

            <div>
              <label className="label">Note (optional)</label>
              <input
                type="text"
                value={formData.note}
                onChange={(e) => setFormData((p) => ({ ...p, note: e.target.value }))}
                placeholder="Any additional note"
                className="input"
                maxLength={500}
              />
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
          description="Add your first expense using AI or the manual form"
        />
      ) : (
        <div className="space-y-3">
          {expenses.map((expense) => (
            <ExpenseCard key={expense.id} expense={expense} onDelete={handleDeleteExpense} />
          ))}
        </div>
      )}
    </div>
  );
}

function ExpenseCard({ expense, onDelete }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-semibold text-gray-900 truncate">{expense.description}</p>
          </div>
          <p className="text-sm text-gray-500 mt-0.5">
            Paid by <span className="font-medium text-gray-700">{expense.payer_name}</span>
            {' · '}
            {formatDate(expense.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-3 ml-3">
          <span className="text-lg font-bold text-gray-900">{formatCurrency(expense.amount)}</span>
          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 text-gray-400 hover:text-gray-600"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button
            onClick={() => onDelete(expense)}
            className="p-1 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {expanded && expense.participants.length > 0 && (
        <div className="mt-4 pt-3 border-t border-gray-100">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Split Details</p>
          <div className="space-y-1">
            {expense.participants.map((p) => (
              <div key={p.id} className="flex justify-between text-sm">
                <span className="text-gray-700">{p.member_name}</span>
                <span className="font-medium text-gray-900">{formatCurrency(p.share)}</span>
              </div>
            ))}
          </div>
          {expense.note && (
            <p className="text-xs text-gray-400 mt-2 italic">{expense.note}</p>
          )}
        </div>
      )}
    </div>
  );
}
