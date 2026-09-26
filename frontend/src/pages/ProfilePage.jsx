import React, { useState } from 'react';
import { Save, User, Mail, Shield, Pencil, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { profileApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const avatarColors = [
  'from-indigo-500 to-violet-600', 'from-emerald-500 to-teal-600',
  'from-orange-500 to-rose-500', 'from-sky-500 to-blue-600',
  'from-pink-500 to-fuchsia-600', 'from-amber-500 to-orange-600',
];
function getAvatarColor(name) {
  return avatarColors[(name || 'A').charCodeAt(0) % avatarColors.length];
}

export default function ProfilePage() {
  const { user, checkSession } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!name.trim()) { toast.error('Name cannot be empty'); return; }
    if (name.trim() === user?.name) { setEditing(false); return; }
    setSaving(true);
    try {
      await profileApi.update({ name: name.trim() });
      await checkSession();
      toast.success('Profile updated!');
      setEditing(false);
    } catch (err) {
      toast.error(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => { setName(user?.name || ''); setEditing(false); };

  const initial = user?.name?.charAt(0).toUpperCase() || '?';
  const avatarColor = getAvatarColor(user?.name || 'A');

  return (
    <div className="max-w-lg space-y-6 fade-up">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-black text-slate-900">Profile</h1>
        <p className="text-slate-500 mt-1 font-medium">Manage your account details</p>
      </div>

      {/* Avatar Hero */}
      <div className="glass-card p-6 flex items-center gap-5">
        <div className={`w-20 h-20 rounded-3xl flex items-center justify-center flex-shrink-0
                          bg-gradient-to-br ${avatarColor} shadow-glass`}>
          <span className="text-white text-3xl font-black">{initial}</span>
        </div>
        <div>
          <p className="text-xl font-black text-slate-900">{user?.name}</p>
          <p className="text-sm text-slate-500 font-medium mt-0.5">{user?.email}</p>
          <div className="flex items-center gap-1.5 mt-2">
            <div className="flex items-center gap-1 badge-positive text-[10px]">
              <Shield className="w-3 h-3" />
              Verified Account
            </div>
            <div className="badge-indigo text-[10px]">JWT Auth</div>
          </div>
        </div>
      </div>

      {/* Edit form */}
      <div className="glass-card p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-bold text-slate-900">Account Details</h2>
          {!editing && (
            <button onClick={() => setEditing(true)}
              className="btn-secondary flex items-center gap-1.5 text-sm py-1.5">
              <Pencil className="w-3.5 h-3.5" /> Edit Name
            </button>
          )}
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          {/* Name */}
          <div>
            <label className="label">
              <span className="flex items-center gap-1.5">
                <User className="w-3 h-3" /> Display Name
              </span>
            </label>
            {editing ? (
              <input
                id="profile-name" type="text" value={name}
                onChange={e => setName(e.target.value)}
                className="input" autoFocus required maxLength={100}
              />
            ) : (
              <div className="input bg-slate-50/60 text-slate-800 select-none cursor-default">
                {user?.name}
              </div>
            )}
          </div>

          {/* Email */}
          <div>
            <label className="label">
              <span className="flex items-center gap-1.5">
                <Mail className="w-3 h-3" /> Email Address
                <span className="text-slate-400 font-normal normal-case">· cannot be changed</span>
              </span>
            </label>
            <div className="input bg-slate-50/40 text-slate-400 cursor-not-allowed select-none">
              {user?.email}
            </div>
          </div>

          {editing && (
            <div className="flex gap-3 pt-1">
              <button type="submit" disabled={saving || !name.trim()} className="btn-primary flex items-center gap-2">
                {saving ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    Saving...
                  </>
                ) : (
                  <><Save className="w-4 h-4" /> Save Changes</>
                )}
              </button>
              <button type="button" onClick={handleCancel} className="btn-secondary flex items-center gap-1.5">
                <X className="w-3.5 h-3.5" /> Cancel
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Account metadata */}
      <div className="glass-card p-5">
        <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
          Account Information
        </h3>
        <div className="space-y-2.5 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-slate-600 font-medium">User ID</span>
            <span className="font-mono text-xs text-slate-400 bg-slate-50 px-2 py-1 rounded-lg">
              {user?.id?.slice(-8)}…
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-600 font-medium">Session</span>
            <span className="text-emerald-600 font-semibold text-xs">Active · Secure Cookie</span>
          </div>
        </div>
      </div>
    </div>
  );
}
