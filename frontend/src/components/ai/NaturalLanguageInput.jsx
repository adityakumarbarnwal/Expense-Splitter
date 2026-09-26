import React, { useState } from 'react';
import { Sparkles, AlertCircle, Lightbulb } from 'lucide-react';
import { expensesApi } from '../../services/api';

/**
 * NaturalLanguageInput — AI-powered expense entry.
 *
 * 1. Accepts free-text
 * 2. POSTs to /api/v1/groups/:groupId/expenses/parse-ai
 * 3. Returns parsed result for parent to confirm
 *
 * Does NOT save anything — confirmation/saving is handled by parent.
 */
export default function NaturalLanguageInput({ groupId, members, currentUser, onParsed, onCancel }) {
  const [text, setText] = useState('');
  const [selectedMemberName, setSelectedMemberName] = useState(
    currentUser ? (members.find((m) => m.id === currentUser.id)?.name || '') : ''
  );
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState(null);

  const examples = [
    "I paid ₹1200 for dinner for me, Rahul and Aman",
    "Aditya paid 500 for groceries shared by everyone",
    "Paid 900 for taxi, split between Priya and me",
  ];

  const handleParse = async (e) => {
    e.preventDefault();
    if (!text.trim()) return;

    setParsing(true);
    setError(null);

    try {
      const response = await expensesApi.parseAI(groupId, {
        text: text.trim(),
        group_id: groupId,
        current_user_name: selectedMemberName || null,
      });

      if (response.success && response.result) {
        onParsed(response.result, text.trim(), response.warnings || []);
      } else {
        setError(response.error || 'Could not parse the expense. Try being more specific or use manual entry.');
      }
    } catch (err) {
      setError(err.message || 'AI service is currently unavailable. Please use manual entry.');
    } finally {
      setParsing(false);
    }
  };

  return (
    <div className="glass-card-elevated p-6 border border-violet-200/60 fade-up">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-indigo-600 flex items-center justify-center shadow-brand">
          <Sparkles className="w-4 h-4 text-white" />
        </div>
        <div>
          <h2 className="font-bold text-slate-900">AI Expense Entry</h2>
          <p className="text-xs text-slate-500 font-medium">Describe the expense in plain language</p>
        </div>
        <div className="ml-auto">
          <span className="badge-indigo text-[10px]">Gemini AI</span>
        </div>
      </div>

      <form onSubmit={handleParse} className="space-y-4">
        {/* Who are you? */}
        <div>
          <label className="label text-xs">
            Who are you? <span className="text-slate-400 font-normal">(helps resolve "I", "me")</span>
          </label>
          <select
            value={selectedMemberName}
            onChange={e => setSelectedMemberName(e.target.value)}
            className="input text-sm"
          >
            <option value="">Select your name (optional)</option>
            {members.map(m => (
              <option key={m.id} value={m.name}>
                {m.name}{m.id === currentUser?.id ? ' (You)' : ''}
              </option>
            ))}
          </select>
        </div>

        {/* Natural language input */}
        <div>
          <label className="label">Describe the expense *</label>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder='e.g. "I paid ₹1200 for dinner for me, Rahul and Aman"'
            className="input min-h-[80px] resize-none"
            required
            maxLength={2000}
          />
        </div>

        {/* Example prompts */}
        <div>
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wide mb-1.5 flex items-center gap-1">
            <Lightbulb className="w-3 h-3" /> Examples
          </p>
          <div className="flex flex-wrap gap-1.5">
            {examples.map((ex, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setText(ex)}
                className="text-xs px-2.5 py-1 bg-violet-50 border border-violet-200
                           text-violet-700 rounded-full hover:bg-violet-100 transition-colors font-medium"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 rounded-xl border border-red-200">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-red-700 font-semibold">AI parsing failed</p>
              <p className="text-xs text-red-600 mt-0.5">{error}</p>
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={parsing || !text.trim()}
            className="btn-primary flex items-center gap-2"
            style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)' }}
          >
            {parsing ? (
              <>
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Parsing with AI...
              </>
            ) : (
              <><Sparkles className="w-4 h-4" /> Parse with AI</>
            )}
          </button>
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
        </div>
      </form>

      <p className="text-xs text-slate-400 mt-4 flex items-center gap-1.5">
        <span>🔒</span>
        AI interprets your text — you'll review before anything is saved.
      </p>
    </div>
  );
}
