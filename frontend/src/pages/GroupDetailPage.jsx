import React, { useState, useEffect } from 'react';
import { useParams, Link, NavLink, Outlet } from 'react-router-dom';
import {
  Plus, Trash2, Receipt, BarChart3, UserPlus, Pencil, Check, X,
  Users, BarChart2, Sparkles, ChevronRight
} from 'lucide-react';
import toast from 'react-hot-toast';
import { groupsApi } from '../services/api';
import { LoadingSpinner, ErrorMessage } from '../components/common/UI';
import { useAuth } from '../contexts/AuthContext';

const avatarColors = [
  'from-indigo-500 to-violet-600',
  'from-emerald-500 to-teal-600',
  'from-orange-500 to-rose-500',
  'from-sky-500 to-blue-600',
  'from-pink-500 to-fuchsia-600',
  'from-amber-500 to-orange-600',
];

function getAvatarColor(name) {
  const c = (name || 'A').charCodeAt(0) % avatarColors.length;
  return avatarColors[c];
}

export default function GroupDetailPage() {
  const { groupId } = useParams();
  const { user } = useAuth();
  const [group, setGroup] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [newMemberEmail, setNewMemberEmail] = useState('');
  const [addingMember, setAddingMember] = useState(false);
  const [showAddForm, setShowAddForm] = useState(false);

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

  const handleAddMember = async (e) => {
    e.preventDefault();
    if (!newMemberEmail.trim()) return;
    setAddingMember(true);
    try {
      await groupsApi.addMember(groupId, { email: newMemberEmail.trim() });
      toast.success('Member added to group');
      setNewMemberEmail('');
      setShowAddForm(false);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setAddingMember(false);
    }
  };

  const handleRemoveMember = async (member) => {
    const msg = member.id === user?.id
      ? 'Remove yourself from this group?'
      : `Remove ${member.name} from the group?`;
    if (!window.confirm(msg)) return;
    try {
      await groupsApi.removeMember(groupId, member.id);
      toast.success(`${member.name} removed`);
      fetchGroup();
    } catch (err) {
      toast.error(err.message);
    }
  };

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
  const initial = group.name.charAt(0).toUpperCase();
  const avatarColor = getAvatarColor(group.name);

  const navItems = [
    { to: `/groups/${groupId}/expenses`, label: 'Expenses', icon: <Receipt className="w-4 h-4" /> },
    { to: `/groups/${groupId}/balances`, label: 'Balances', icon: <BarChart3 className="w-4 h-4" /> },
    { to: `/groups/${groupId}/insights`, label: 'Insights', icon: <BarChart2 className="w-4 h-4" /> },
  ];

  return (
    <div className="space-y-6 fade-up">
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
        <Link to="/groups" className="hover:text-brand-600 transition-colors">Groups</Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-slate-700">{group.name}</span>
      </div>

      {/* Group Header Card */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1 min-w-0">
            {/* Avatar */}
            <div className={`w-14 h-14 bg-gradient-to-br ${avatarColor} rounded-2xl
                              flex items-center justify-center flex-shrink-0 shadow-glass`}>
              <span className="text-white font-black text-xl">{initial}</span>
            </div>

            {/* Name + rename */}
            <div className="flex-1 min-w-0">
              {editingName ? (
                <form onSubmit={handleRenameGroup} className="flex items-center gap-2 mb-1">
                  <input
                    type="text"
                    value={newGroupName}
                    onChange={(e) => setNewGroupName(e.target.value)}
                    className="input text-lg font-bold py-1 max-w-xs"
                    autoFocus
                    required
                    maxLength={255}
                  />
                  <button type="submit" disabled={renamingGroup || !newGroupName.trim()}
                    className="p-1.5 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors">
                    <Check className="w-4 h-4" />
                  </button>
                  <button type="button" onClick={() => setEditingName(false)}
                    className="p-1.5 text-slate-400 hover:bg-slate-100 rounded-lg transition-colors">
                    <X className="w-4 h-4" />
                  </button>
                </form>
              ) : (
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-2xl font-black text-slate-900 truncate">{group.name}</h1>
                  <button onClick={handleStartRename}
                    className="p-1.5 text-slate-300 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors">
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
              {group.description && (
                <p className="text-slate-500 text-sm">{group.description}</p>
              )}
              <div className="flex items-center gap-2 mt-2">
                <div className="flex -space-x-1.5">
                  {members.slice(0, 5).map(m => (
                    <div key={m.id}
                      className={`w-6 h-6 rounded-full border-2 border-white flex items-center justify-center
                                  bg-gradient-to-br ${getAvatarColor(m.name)} text-white text-[9px] font-bold`}>
                      {m.name.charAt(0).toUpperCase()}
                    </div>
                  ))}
                  {members.length > 5 && (
                    <div className="w-6 h-6 rounded-full border-2 border-white bg-slate-100 flex items-center justify-center
                                    text-slate-600 text-[9px] font-bold">
                      +{members.length - 5}
                    </div>
                  )}
                </div>
                <span className="text-xs text-slate-500 font-medium">
                  {members.length} member{members.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Quick nav tabs */}
        <div className="flex gap-2 mt-5 pt-5 border-t border-slate-100/60 flex-wrap">
          {navItems.map(item => (
            <Link
              key={item.to}
              to={item.to}
              className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold
                         bg-white/60 hover:bg-brand-50 border border-slate-100 hover:border-brand-200
                         text-slate-600 hover:text-brand-700 transition-all"
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Members Section */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-4 h-4 text-slate-400" />
            Members <span className="text-slate-400 font-normal">({members.length})</span>
          </h2>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="btn-secondary flex items-center gap-1.5 text-sm py-1.5"
          >
            <UserPlus className="w-3.5 h-3.5" />
            Add Member
          </button>
        </div>

        {/* Add Member Form */}
        {showAddForm && (
          <form onSubmit={handleAddMember} className="mb-4 p-4 bg-brand-50/40 rounded-xl border border-brand-100/60">
            <p className="text-xs font-semibold text-slate-500 mb-2">
              Add by email — must already be registered with SplitIt.
            </p>
            <div className="flex gap-2">
              <input
                type="email"
                value={newMemberEmail}
                onChange={(e) => setNewMemberEmail(e.target.value)}
                placeholder="member@example.com"
                className="input flex-1"
                required
                autoFocus
              />
              <button type="submit" disabled={addingMember || !newMemberEmail.trim()} className="btn-primary">
                {addingMember ? 'Adding...' : 'Add'}
              </button>
              <button type="button" onClick={() => { setShowAddForm(false); setNewMemberEmail(''); }}
                className="btn-secondary">
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Member List */}
        {members.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <div className="text-3xl mb-2">👤</div>
            <p className="text-sm">No members yet. Add members by their email address.</p>
          </div>
        ) : (
          <ul className="space-y-1">
            {members.map(member => {
              const isYou = member.id === user?.id;
              return (
                <li key={member.id}
                  className={`flex items-center justify-between py-3 px-2 rounded-xl transition-colors ${
                    isYou ? 'bg-brand-50/40' : 'hover:bg-slate-50/40'
                  }`}>
                  <div className="flex items-center gap-3">
                    <div className={`w-9 h-9 rounded-full flex items-center justify-center
                                    bg-gradient-to-br ${getAvatarColor(member.name)} shadow-sm`}>
                      <span className="text-white font-bold text-sm">
                        {member.name.charAt(0).toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="font-semibold text-slate-900 text-sm">{member.name}</span>
                        {isYou && (
                          <span className="badge-indigo text-[10px]">You</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{member.email}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveMember(member)}
                    className="p-1.5 text-slate-200 hover:text-red-500 hover:bg-red-50
                               rounded-lg transition-colors"
                    title={`Remove ${member.name}`}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
