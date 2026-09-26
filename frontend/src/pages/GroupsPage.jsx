import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Plus, Users, Trash2, ArrowRight, Calendar,
  TrendingUp, TrendingDown, Minus, Sparkles
} from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, EmptyState, SkeletonGroupCard } from '../components/common/UI';

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  });
}

function formatCurrency(amount) {
  return `₹${Math.abs(Number(amount)).toFixed(2)}`;
}

/** Premium group card with net position indicator */
function GroupCard({ group, onDelete }) {
  const net = Number(group.user_net_balance ?? null);
  const hasNet = group.user_net_balance !== null && group.user_net_balance !== undefined;
  const initial = group.name.charAt(0).toUpperCase();

  // Color palette for group avatars based on first letter
  const avatarColors = [
    'from-indigo-500 to-violet-600',
    'from-emerald-500 to-teal-600',
    'from-orange-500 to-rose-500',
    'from-sky-500 to-blue-600',
    'from-pink-500 to-fuchsia-600',
    'from-amber-500 to-orange-600',
  ];
  const colorIndex = initial.charCodeAt(0) % avatarColors.length;
  const avatarColor = avatarColors[colorIndex];

  const NetBadge = () => {
    if (!hasNet) return null;
    if (net > 0.005) return (
      <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl
                      bg-emerald-50 border border-emerald-100">
        <TrendingUp className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0" />
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-emerald-600">You're owed</p>
          <p className="text-sm font-black text-emerald-700">{formatCurrency(net)}</p>
        </div>
      </div>
    );
    if (net < -0.005) return (
      <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl
                      bg-red-50 border border-red-100">
        <TrendingDown className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-red-500">You owe</p>
          <p className="text-sm font-black text-red-600">{formatCurrency(net)}</p>
        </div>
      </div>
    );
    return (
      <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl
                      bg-slate-50 border border-slate-100">
        <Minus className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
        <div>
          <p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Settled</p>
          <p className="text-sm font-black text-slate-500">₹0.00</p>
        </div>
      </div>
    );
  };

  return (
    <Link
      to={`/groups/${group.id}`}
      className="glass-card-hover p-6 flex flex-col gap-4 cursor-pointer group relative"
    >
      {/* Delete button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onDelete(group);
        }}
        className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-200
                   hover:text-red-500 hover:bg-red-50 transition-all opacity-0
                   group-hover:opacity-100"
        title="Delete group"
      >
        <Trash2 className="w-4 h-4" />
      </button>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div className={`w-11 h-11 bg-gradient-to-br ${avatarColor} rounded-2xl
                          flex items-center justify-center flex-shrink-0 shadow-sm`}>
          <span className="text-white font-black text-base">{initial}</span>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-bold text-slate-900 text-base truncate
                         group-hover:text-brand-700 transition-colors">
            {group.name}
          </h3>
          {group.description && (
            <p className="text-slate-500 text-xs mt-0.5 truncate">{group.description}</p>
          )}
          <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-400 font-medium">
            <span className="flex items-center gap-1">
              <Users className="w-3 h-3" />
              {group.member_count} member{group.member_count !== 1 ? 's' : ''}
            </span>
            {group.created_at && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {formatDate(group.created_at)}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="glass-divider" />

      {/* Net position + arrow */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1">
            Your Position
          </p>
          <NetBadge />
          {!hasNet && (
            <p className="text-xs text-slate-400 italic">Loading balance...</p>
          )}
        </div>
        <ArrowRight className="w-4 h-4 text-slate-300 group-hover:text-brand-500
                                group-hover:translate-x-0.5 transition-all flex-shrink-0" />
      </div>
    </Link>
  );
}

export default function GroupsPage() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [creating, setCreating] = useState(false);

  const fetchGroups = useCallback(async () => {
    try {
      setError(null);
      const data = await groupsApi.list();
      setGroups(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchGroups(); }, [fetchGroups]);

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) return;
    setCreating(true);
    try {
      await groupsApi.create({
        name: formData.name.trim(),
        description: formData.description.trim() || null,
      });
      toast.success(`Group "${formData.name}" created!`);
      setFormData({ name: '', description: '' });
      setShowForm(false);
      fetchGroups();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteGroup = async (group) => {
    if (!window.confirm(`Delete group "${group.name}" and all its data? This cannot be undone.`)) return;
    try {
      await groupsApi.delete(group.id);
      toast.success(`Group "${group.name}" deleted`);
      fetchGroups();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (loading) return (
    <div className="space-y-6 fade-up">
      <div className="flex items-center justify-between">
        <div className="skeleton h-8 w-40 rounded-xl" />
        <div className="skeleton h-10 w-32 rounded-xl" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {[1, 2, 3, 4].map(i => <SkeletonGroupCard key={i} />)}
      </div>
    </div>
  );
  if (error) return <ErrorMessage message={error} onRetry={fetchGroups} />;

  return (
    <div className="space-y-8 fade-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-slate-900">Your Groups</h1>
          <p className="text-slate-500 mt-1 font-medium">
            {groups.length === 0
              ? 'Create your first group to start splitting expenses'
              : `${groups.length} group${groups.length !== 1 ? 's' : ''} · Net positions shown`}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Group
        </button>
      </div>

      {/* Create Group Form */}
      {showForm && (
        <div className="glass-card-elevated p-6 border border-brand-200/40 fade-up">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-8 h-8 rounded-xl bg-brand-gradient flex items-center justify-center shadow-brand">
              <Plus className="w-4 h-4 text-white" />
            </div>
            <h2 className="text-lg font-bold text-slate-900">Create New Group</h2>
          </div>
          <form onSubmit={handleCreateGroup} className="space-y-4">
            <div>
              <label className="label">Group Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData(p => ({ ...p, name: e.target.value }))}
                placeholder="e.g. Trip to Goa, Flat 4B, Office Lunch"
                className="input"
                required
                autoFocus
                maxLength={255}
              />
            </div>
            <div>
              <label className="label">Description (optional)</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData(p => ({ ...p, description: e.target.value }))}
                placeholder="e.g. Monthly flat expenses"
                className="input"
                maxLength={500}
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={creating || !formData.name.trim()} className="btn-primary">
                {creating ? 'Creating...' : 'Create Group'}
              </button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setFormData({ name: '', description: '' }); }}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Groups Grid */}
      {groups.length === 0 ? (
        <EmptyState
          icon="👥"
          title="No groups yet"
          description="Create your first group to start tracking shared expenses with friends"
          action={
            <button onClick={() => setShowForm(true)} className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-4 h-4" /> Create First Group
            </button>
          }
        />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 stagger-2">
            {groups.map((group, i) => (
              <div key={group.id} className={`stagger-${Math.min(i + 1, 6)}`}>
                <GroupCard group={group} onDelete={handleDeleteGroup} />
              </div>
            ))}
          </div>

          {/* AI entry callout */}
          <div className="ai-insight-card flex items-center gap-4">
            <Sparkles className="w-8 h-8 text-violet-600 flex-shrink-0" />
            <div>
              <p className="font-bold text-slate-900 text-sm">Add expenses with AI</p>
              <p className="text-xs text-slate-500 mt-0.5">
                Open any group, click "AI Entry", and type naturally — SplitIt understands.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
