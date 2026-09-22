import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Users, Trash2, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi } from '../services/api';
import { LoadingSpinner, ErrorMessage, EmptyState } from '../components/common/UI';

export default function HomePage() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupDesc, setNewGroupDesc] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchGroups = async () => {
    try {
      setError(null);
      const data = await groupsApi.list();
      setGroups(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim()) return;

    setCreating(true);
    try {
      await groupsApi.create({ name: newGroupName.trim(), description: newGroupDesc.trim() || null });
      toast.success(`Group "${newGroupName}" created!`);
      setNewGroupName('');
      setNewGroupDesc('');
      setShowForm(false);
      fetchGroups();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteGroup = async (group, e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm(`Delete group "${group.name}" and all its data? This cannot be undone.`)) return;

    try {
      await groupsApi.delete(group.id);
      toast.success(`Group "${group.name}" deleted`);
      fetchGroups();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (loading) return <LoadingSpinner message="Loading groups..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchGroups} />;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Your Groups</h1>
          <p className="text-gray-500 mt-1">Manage shared expenses with your groups</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          New Group
        </button>
      </div>

      {/* Create Group Form */}
      {showForm && (
        <div className="card mb-6 border-blue-200 bg-blue-50">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Group</h2>
          <form onSubmit={handleCreateGroup} className="space-y-4">
            <div>
              <label className="label">Group Name *</label>
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
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
                value={newGroupDesc}
                onChange={(e) => setNewGroupDesc(e.target.value)}
                placeholder="e.g. Monthly flat expenses"
                className="input"
                maxLength={500}
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={creating || !newGroupName.trim()} className="btn-primary">
                {creating ? 'Creating...' : 'Create Group'}
              </button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setNewGroupName(''); setNewGroupDesc(''); }}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Groups List */}
      {groups.length === 0 ? (
        <EmptyState
          icon="👥"
          title="No groups yet"
          description="Create your first group to start tracking shared expenses"
          action={
            <button onClick={() => setShowForm(true)} className="btn-primary inline-flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Create First Group
            </button>
          }
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {groups.map((group) => (
            <Link
              key={group.id}
              to={`/groups/${group.id}`}
              className="card hover:border-blue-300 hover:shadow-md transition-all group cursor-pointer"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-900 text-lg group-hover:text-blue-600 transition-colors truncate">
                    {group.name}
                  </h3>
                  {group.description && (
                    <p className="text-gray-500 text-sm mt-0.5 truncate">{group.description}</p>
                  )}
                  <div className="flex items-center gap-1 mt-3 text-sm text-gray-500">
                    <Users className="w-4 h-4" />
                    <span>{group.member_count} member{group.member_count !== 1 ? 's' : ''}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-3">
                  <button
                    onClick={(e) => handleDeleteGroup(group, e)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    title="Delete group"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-blue-400 transition-colors" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
