import React, { useState } from 'react';
import { CheckCircle, Edit2, X, AlertTriangle, Sparkles } from 'lucide-react';

/**
 * AIConfirmationCard — Shows AI-parsed expense details for user review.
 *
 * This is the critical UI step in the AI pipeline:
 * USER sees what the AI interpreted → confirms or edits → THEN it gets saved.
 *
 * The AI result is NEVER directly saved — only after user confirmation.
 */
export default function AIConfirmationCard({
  result,
  originalText,
  warnings = [],
  members,
  onConfirm,
  onEdit,
  onCancel,
  submitting,
}) {
  const [editedResult, setEditedResult] = useState({
    description: result.description || '',
    amount: result.amount ? String(result.amount) : '',
    payer_name: result.payer_name || '',
    participant_names: [...(result.participant_names || [])],
  });

  const [isEditing, setIsEditing] = useState(false);

  const handleToggleParticipant = (memberName) => {
    setEditedResult((prev) => {
      const inList = prev.participant_names.includes(memberName);
      return {
        ...prev,
        participant_names: inList
          ? prev.participant_names.filter((n) => n !== memberName)
          : [...prev.participant_names, memberName],
      };
    });
  };

  const handleConfirm = () => {
    if (!editedResult.description || !editedResult.amount || !editedResult.payer_name || editedResult.participant_names.length === 0) {
      return; // Validation handled by parent
    }
    onConfirm({
      description: editedResult.description,
      amount: parseFloat(editedResult.amount),
      payer_name: editedResult.payer_name,
      participant_names: editedResult.participant_names,
    });
  };

  const confidenceColor = {
    high: 'text-green-600 bg-green-100',
    medium: 'text-yellow-600 bg-yellow-100',
    low: 'text-red-600 bg-red-100',
  }[result.confidence] || 'text-gray-600 bg-gray-100';

  const isValid =
    editedResult.description.trim() &&
    editedResult.amount &&
    parseFloat(editedResult.amount) > 0 &&
    editedResult.payer_name &&
    editedResult.participant_names.length > 0;

  const perPersonShare = isValid
    ? (parseFloat(editedResult.amount) / editedResult.participant_names.length).toFixed(2)
    : null;

  return (
    <div className="card mb-6 border-purple-200">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-purple-600" />
          </div>
          <div>
            <h2 className="font-semibold text-gray-900">AI Interpretation</h2>
            <p className="text-xs text-gray-500">Review before saving</p>
          </div>
        </div>
        <span className={`text-xs px-2 py-1 rounded-full font-medium ${confidenceColor}`}>
          {result.confidence} confidence
        </span>
      </div>

      {/* Original text */}
      <div className="bg-gray-50 rounded-lg p-3 mb-4">
        <p className="text-xs text-gray-500 mb-1">You entered:</p>
        <p className="text-sm text-gray-700 italic">"{originalText}"</p>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-yellow-700 mb-1">Attention needed:</p>
              <ul className="text-xs text-yellow-700 space-y-0.5">
                {warnings.map((w, i) => <li key={i}>• {w}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Parsed Fields */}
      <div className="space-y-4">
        {/* Description */}
        <div>
          <label className="label text-xs">Description</label>
          {isEditing ? (
            <input
              type="text"
              value={editedResult.description}
              onChange={(e) => setEditedResult((p) => ({ ...p, description: e.target.value }))}
              className="input"
              required
            />
          ) : (
            <p className={`text-base font-medium ${editedResult.description ? 'text-gray-900' : 'text-red-500 italic'}`}>
              {editedResult.description || 'Not detected — please edit'}
            </p>
          )}
        </div>

        {/* Amount */}
        <div>
          <label className="label text-xs">Amount</label>
          {isEditing ? (
            <input
              type="number"
              value={editedResult.amount}
              onChange={(e) => setEditedResult((p) => ({ ...p, amount: e.target.value }))}
              className="input"
              min="0.01"
              step="0.01"
              required
            />
          ) : (
            <p className={`text-2xl font-bold ${editedResult.amount ? 'text-gray-900' : 'text-red-500 italic'}`}>
              {editedResult.amount ? `₹${parseFloat(editedResult.amount).toFixed(2)}` : 'Not detected — please edit'}
            </p>
          )}
        </div>

        {/* Payer */}
        <div>
          <label className="label text-xs">Paid by</label>
          {isEditing ? (
            <select
              value={editedResult.payer_name}
              onChange={(e) => setEditedResult((p) => ({ ...p, payer_name: e.target.value }))}
              className="input"
              required
            >
              <option value="">Select payer</option>
              {members.map((m) => (
                <option key={m.id} value={m.name}>{m.name}</option>
              ))}
            </select>
          ) : (
            <p className={`font-medium ${editedResult.payer_name ? 'text-gray-900' : 'text-red-500 italic'}`}>
              {editedResult.payer_name || 'Not detected — please edit'}
            </p>
          )}
        </div>

        {/* Participants */}
        <div>
          <label className="label text-xs">
            Participants ({editedResult.participant_names.length})
            {perPersonShare && <span className="text-gray-400 ml-2">— ₹{perPersonShare} each</span>}
          </label>
          {isEditing ? (
            <div className="flex flex-wrap gap-2 mt-1">
              {members.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => handleToggleParticipant(m.name)}
                  className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-colors ${
                    editedResult.participant_names.includes(m.name)
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                  }`}
                >
                  {m.name}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-2 mt-1">
              {editedResult.participant_names.length > 0 ? (
                editedResult.participant_names.map((name) => (
                  <span key={name} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                    {name}
                  </span>
                ))
              ) : (
                <p className="text-red-500 italic text-sm">No participants detected — please edit</p>
              )}
            </div>
          )}
        </div>

        {/* AI notes */}
        {result.notes && (
          <p className="text-xs text-gray-400 italic">AI note: {result.notes}</p>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-3 mt-6 pt-4 border-t border-gray-100">
        {isEditing ? (
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="btn-secondary"
          >
            Done Editing
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="btn-secondary flex items-center gap-2"
          >
            <Edit2 className="w-4 h-4" />
            Edit
          </button>
        )}

        <button
          type="button"
          onClick={handleConfirm}
          disabled={!isValid || submitting || isEditing}
          className="btn-primary flex items-center gap-2 bg-green-600 hover:bg-green-700 focus:ring-green-500"
        >
          <CheckCircle className="w-4 h-4" />
          {submitting ? 'Saving...' : 'Confirm & Save'}
        </button>

        <button type="button" onClick={onCancel} className="btn-secondary flex items-center gap-2">
          <X className="w-4 h-4" />
          Cancel
        </button>
      </div>

      <p className="text-xs text-gray-400 mt-3">
        ⚠️ AI interpretations may not be 100% accurate. Please review all fields before confirming.
      </p>
    </div>
  );
}
