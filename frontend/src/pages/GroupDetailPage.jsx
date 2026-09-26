import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Plus, Trash2, Receipt, BarChart3, UserPlus, Pencil, Check, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi } from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/UI';
import { useAuth } from '../contexts/AuthContext';

export default function GroupDetailPage() {
  const { groupId } = useParams();
  const { user } = useAuth();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Add member by email
  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

  // Rename group
  const [editingName, setEditingName] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [renamingGroup, setRenamingGroup] = useState(false);

  const fetchGroup = async () => {
    try {
      setError(null);
      const data = await groupsApi.get(groupId);
      setGroup(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchGroup(); }, [groupId]);

  // --- Add member by email ---
  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!newMemberEmail.trim()) return;

    setAddingMember(true);
    try {
      await groupsApi.addMember(groupId, { email: newMemberEmail.trim() });
      toast.success(`Member added to group`);
      setNewMemberEmail('');
      setShowAddForm(false);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setAddingMember(false);
    }
  };

  // --- Remove member (uses MongoDB user _id) ---
  const handleRemoveMember = async (member) => {
    if (member.id === user?.id) {
      if (!window.confirm('Remove yourself from this group?')) return;
    } else {
      if (!window.confirm(`Remove ${member.name} from the group?`)) return;
    }
    try {
      await groupsApi.removeMember(groupId, member.id);
      toast.success(`${member.name} removed`);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // --- Rename group ---
  const handleStartRename = () => {
    setNewGroupName(group.name);
    setEditingName(true);
  };

  const handleRenameGroup = async (e) => {
    e.preventDefault();
    if (!newGroupName.trim() || newGroupName.trim() === group.name) {
      setEditingName(false);
      return;
    }
    setRenamingGroup(true);
    try {
      await groupsApi.update(groupId, { name: newGroupName.trim() });
      toast.success('Group renamed');
      setEditingName(false);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setRenamingGroup(false);
    }
  };

  if (loading) return <LoadingSpinner message="Loading group..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchGroup} />;
  if (!group) return null;

  const members = group.members || [];

  return (
    <div>
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-6">
        <Link to="/groups" className="hover:text-blue-600">Groups</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">{group.name}</span>
      </div>

      {/* Group Header */}
      <div className="flex items-start justify-between mb-8">
        <div className="flex-1 min-w-0">
          {/* Inline rename */}
          {editingName ? (
            <form onSubmit={handleRenameGroup} className="flex items-center gap-2">
              <input
                type="text"
                value={newGroupName}
                onChange={(e) => setNewGroupName(e.target.value)}
                className="input text-2xl font-bold py-1 max-w-xs"
                autoFocus
                required
                maxLength={255}
              />
              <button
                type="submit"
                disabled={renamingGroup || !newGroupName.trim()}
                className="p-1.5 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                title="Save name"
              >
                <Check className="w-5 h-5" />
              </button>
              <button
                type="button"
                onClick={() => setEditingName(false)}
                className="p-1.5 text-gray-400 hover:bg-gray-100 rounded-lg transition-colors"
                title="Cancel"
              >
                <X className="w-5 h-5" />
              </button>
            </form>
          ) : (
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-gray-900">{group.name}</h1>
              <button
                onClick={handleStartRename}
                className="p-1.5 text-gray-300 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                title="Rename group"
              >
                <Pencil className="w-4 h-4" />
              </button>
            </div>
          )}
          {group.description && <p className="text-gray-500 mt-1">{group.description}</p>}
          <p className="text-sm text-gray-400 mt-1">
            {members.length} member{members.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        <Link
          to={`/groups/${groupId}/expenses`}
          className="card hover:border-blue-300 hover:shadow-md transition-all flex items-center gap-3 cursor-pointer"
        >
          <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
            <Receipt className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Expenses</p>
            <p className="text-sm text-gray-500">View & add expenses</p>
          </div>
        </Link>
        <Link
          to={`/groups/${groupId}/balances`}
          className="card hover:border-green-300 hover:shadow-md transition-all flex items-center gap-3 cursor-pointer"
        >
          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
            <BarChart3 className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <p className="font-semibold text-gray-900">Balances</p>
            <p className="text-sm text-gray-500">Who owes whom</p>
          </div>
        </Link>
      </div>

      {/* Members Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">
            Members ({members.length})
          </h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="btn-secondary flex items-center gap-2 text-sm py-1.5"
          >
            <UserPlus className="w-4 h-4" />
            Add Member
          </button>
        </div>

        {/* Add Member Form — by email (registered users only) */}
        {showAddForm && (
          <form onSubmit={handleAddMember} className="mb-4">
            <div className="flex gap-3">
              <input
                type="email"
                value={newMemberEmail}
                onChange={(e) => setNewMemberEmail(e.target.value)}
                placeholder="member@example.com (must be registered)"
                className="input flex-1"
                required
                autoFocus
              />
              <button type="submit" disabled={addingMember || !newMemberEmail.trim()} className="btn-primary">
                {addingMember ? 'Adding...' : 'Add'}
              </button>
              <button
                type="button"
                onClick={() => { setShowAddForm(false); setNewMemberEmail(''); }}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
            <p className="text-xs text-gray-400 mt-1.5">
              The user must already be registered with SplitSmart.
            </p>
          </form>
        )}

        {/* Members List */}
        {members.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-4xl mb-2">👤</p>
            <p>No members yet. Add members by their email address.</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {members.map((member) => (
              <li key={member.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-700 font-semibold text-sm">
                      {member.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-900">{member.name}</span>
                    {member.id === user?.id && (
                      <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">You</span>
                    )}
                    <p className="text-xs text-gray-400">{member.email}</p>
                  </div>
                </div>
                <button
                  onClick={() => handleRemoveMember(member)}
                  className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  title={`Remove ${member.name}`}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
