import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Plus, Trash2, Receipt, BarChart3, UserPlus } from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi } from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/UI';

export default function GroupDetailPage() {
  const { groupId } = useParams();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newMemberName, setNewMemberName] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

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

  useEffect(() => {
    fetchGroup();
  }, [groupId]);

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!newMemberName.trim()) return;

    setAddingMember(true);
    try {
      await groupsApi.addMember(groupId, { name: newMemberName.trim() });
      toast.success(`${newMemberName} added to group`);
      setNewMemberName('');
      setShowAddForm(false);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (member) => {
    if (!window.confirm(`Remove ${member.name} from the group?`)) return;
    try {
      await groupsApi.removeMember(groupId, member.id);
      toast.success(`${member.name} removed`);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (loading) return <LoadingSpinner message="Loading group..." />;
  if (error) return <ErrorMessage message={error} onRetry={fetchGroup} />;
  if (!group) return null;

  return (
    <div>
      {/* Breadcrumb */}
      <div className="text-sm text-gray-500 mb-6">
        <Link to="/" className="hover:text-blue-600">Groups</Link>
        <span className="mx-2">/</span>
        <span className="text-gray-900 font-medium">{group.name}</span>
      </div>

      {/* Group Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{group.name}</h1>
          {group.description && <p className="text-gray-500 mt-1">{group.description}</p>}
          <p className="text-sm text-gray-400 mt-1">
            {group.member_count} member{group.member_count !== 1 ? 's' : ''}
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
            Members ({group.member_count})
          </h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="btn-secondary flex items-center gap-2 text-sm py-1.5"
          >
            <UserPlus className="w-4 h-4" />
            Add Member
          </button>
        </div>

        {/* Add Member Form */}
        {showAddForm && (
          <form onSubmit={handleAddMember} className="mb-4 flex gap-3">
            <input
              type="text"
              value={newMemberName}
              onChange={(e) => setNewMemberName(e.target.value)}
              placeholder="Member's name (e.g. Rahul)"
              className="input flex-1"
              required
              autoFocus
              maxLength={100}
            />
            <button type="submit" disabled={addingMember || !newMemberName.trim()} className="btn-primary">
              {addingMember ? 'Adding...' : 'Add'}
            </button>
            <button
              type="button"
              onClick={() => { setShowAddForm(false); setNewMemberName(''); }}
              className="btn-secondary"
            >
              Cancel
            </button>
          </form>
        )}

        {/* Members List */}
        {group.members.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <p className="text-4xl mb-2">👤</p>
            <p>No members yet. Add some members to get started.</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {group.members.map((member) => (
              <li key={member.id} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-blue-700 font-semibold text-sm">
                      {member.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="font-medium text-gray-900">{member.name}</span>
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
