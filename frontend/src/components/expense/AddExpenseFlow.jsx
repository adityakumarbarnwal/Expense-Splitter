import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, ArrowLeft, Sparkles, Plus, Users, ChevronRight } from 'lucide-react';

export default function AddExpenseFlow({ groups = [], onClose }) {
  const navigate = useNavigate();
  const [selectedGroup, setSelectedGroup] = useState(null);

  const handleSelectGroup = (group) => {
    setSelectedGroup(group);
  };

  const handleAddManually = () => {
    if (!selectedGroup) return;
    navigate(`/groups/${selectedGroup.id}/expenses`, {
      state: { openManual: true },
    });
    if (onClose) onClose();
  };

  const handleAddWithAI = () => {
    if (!selectedGroup) return;
    navigate(`/groups/${selectedGroup.id}/expenses`, {
      state: { openAI: true },
    });
    if (onClose) onClose();
  };

  return (
    <div className="glass-card-elevated p-5 max-w-md border border-brand-100/60 shadow-glass-elevated fade-up relative">
      <button
        onClick={onClose}
        className="absolute top-4 right-4 p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
        aria-label="Close"
      >
        <X className="w-4 h-4" />
      </button>

      {!selectedGroup ? (
        <div>
          <div className="mb-3 pr-6">
            <h3 className="font-bold text-slate-900 text-sm">Select a Group</h3>
            <p className="text-xs text-slate-500 mt-0.5">Which group is this expense for?</p>
          </div>

          {groups.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">
              No groups found. Create a group first!
            </p>
          ) : (
            <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1">
              {groups.map((group) => {
                const count = group.member_count ?? group.members_count ?? group.members?.length ?? 0;
                return (
                  <button
                    key={group.id}
                    onClick={() => handleSelectGroup(group)}
                    className="w-full flex items-center justify-between p-2.5 rounded-xl border border-slate-200/60 bg-white/50 hover:bg-white hover:border-brand-200 hover:shadow-sm transition-all text-left group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-brand-50 border border-brand-100 flex items-center justify-center flex-shrink-0 group-hover:bg-brand-100 transition-colors">
                        <Users className="w-4 h-4 text-brand-600" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-800 text-sm truncate group-hover:text-brand-600 transition-colors">
                          {group.name}
                        </p>
                        <p className="text-[11px] text-slate-400">
                          {count} {count === 1 ? 'member' : 'members'}
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-brand-500 transition-colors flex-shrink-0" />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        <div>
          <div className="flex items-center gap-2 mb-4 pr-6">
            <button
              onClick={() => setSelectedGroup(null)}
              className="p-1 -ml-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
              title="Back to groups"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <div className="min-w-0">
              <h3 className="font-bold text-slate-900 text-sm truncate">
                {selectedGroup.name}
              </h3>
              <p className="text-xs text-slate-500">Choose how to add expense</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <button
              onClick={handleAddManually}
              className="btn-secondary flex flex-col items-center justify-center gap-2 py-4 px-3 text-center hover:border-brand-300 transition-all"
            >
              <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                <Plus className="w-4 h-4 text-slate-700" />
              </div>
              <div>
                <p className="font-bold text-xs text-slate-800">Add Manually</p>
                <p className="text-[10px] text-slate-400 mt-0.5">Standard form</p>
              </div>
            </button>

            <button
              onClick={handleAddWithAI}
              className="btn-primary flex flex-col items-center justify-center gap-2 py-4 px-3 text-center transition-all"
              style={{ background: 'linear-gradient(135deg, #7c3aed, #6366f1)' }}
            >
              <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="font-bold text-xs text-white">Add with AI</p>
                <p className="text-[10px] text-white/80 mt-0.5">Natural language</p>
              </div>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
