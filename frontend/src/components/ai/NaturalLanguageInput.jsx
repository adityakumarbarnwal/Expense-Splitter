import React, { useState } from 'react';
import { Sparkles, AlertCircle } from 'lucide-react';
import { expensesApi } from '../../services/api';

/**
 * NaturalLanguageInput — The AI-powered expense entry component.
 *
 * This component:
 * 1. Accepts free-text input from the user
 * 2. Sends it to POST /api/v1/groups/:groupId/expenses/parse-ai
 * 3. Returns the parsed result for confirmation
 *
 * It does NOT save anything to the database.
 * The parent component handles confirmation and actual saving.
 */
export default function NaturalLanguageInput({ groupId, members, currentUser, onParsed, onCancel }) {
  const [text, setText] = useState('');
  const [selectedMemberName, setSelectedMemberName] = useState(
    // Default to current logged-in user's name if they're in the group
    currentUser ? (members.find((m) => m.id === currentUser.id)?.name || '') : ''
  );
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState(null);

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
        setError(response.error || 'Could not parse the expense. Please try again or use manual entry.');
      }
    } catch (err) {
      setError(err.message || 'AI service is currently unavailable. Please use manual entry.');
    } finally {
      setParsing(false);
    }
  };

  const examples = [
    "I paid ₹1200 for dinner for me, Rahul and Aman",
    "Aditya paid 500 for groceries shared by everyone",
    "Paid 900 for taxi, split between Priya and me",
  ];

  return (
    <div className="card mb-6 border-purple-200 bg-purple-50">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
          <Sparkles className="w-4 h-4 text-purple-600" />
        </div>
        <div>
          <h2 className="font-semibold text-gray-900">AI Expense Entry</h2>
          <p className="text-xs text-gray-500">Describe the expense in plain language</p>
        </div>
      </div>

      <form onSubmit={handleParse} className="space-y-4">
        {/* "Who are you?" for pronoun resolution — pre-filled with logged-in user */}
        <div>
          <label className="label text-xs">
            Who are you? <span className="text-gray-400">(helps resolve "I", "me")</span>
          </label>
          <select
            value={selectedMemberName}
            onChange={(e) => setSelectedMemberName(e.target.value)}
            className="input text-sm"
          >
            <option value="">Select your name (optional)</option>
            {members.map((m) => (
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
            onChange={(e) => setText(e.target.value)}
            placeholder='e.g. "I paid ₹1200 for dinner for me, Rahul and Aman"'
            className="input min-h-[80px] resize-none"
            required
            maxLength={2000}
          />
        </div>

        {/* Example prompts */}
        <div>
          <p className="text-xs text-gray-500 mb-1">Examples:</p>
          <div className="flex flex-wrap gap-1">
            {examples.map((ex, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setText(ex)}
                className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full hover:bg-purple-200 transition-colors"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-start gap-2 p-3 bg-red-50 rounded-lg border border-red-200">
            <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={parsing || !text.trim()}
            className="btn-primary flex items-center gap-2 bg-purple-600 hover:bg-purple-700 focus:ring-purple-500"
          >
            {parsing ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Parsing...
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                Parse with AI
              </>
            )}
          </button>
          <button type="button" onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
        </div>
      </form>

      <p className="text-xs text-gray-400 mt-3">
        🔒 AI interprets your text — you'll review before anything is saved.
      </p>
    </div>
  );
}
