import React, { useState } from 'react';
import { Save, User, Mail, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { profileApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function ProfilePage() {
  const { user, checkSession } = useAuth();
  const [name, setName] = useState(user?.name || '');
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error('Name cannot be empty');
      return;
    }
    if (name.trim() === user?.name) {
      setEditing(false);
      return;
    }

    setSaving(true);
    try {
      await profileApi.update({ name: name.trim() });
      await checkSession(); // Refresh user in context
      toast.success('Profile updated!');
      setEditing(false);
    } catch (err) {
      toast.error(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setName(user?.name || '');
    setEditing(false);
  };

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Your Profile</h1>
        <p className="text-gray-500 mt-1">Manage your account details</p>
      </div>

      {/* Avatar card */}
      <div className="card flex items-center gap-5 mb-6">
        <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
          <span className="text-white text-2xl font-bold">
            {user?.name?.charAt(0).toUpperCase()}
          </span>
        </div>
        <div>
          <p className="text-lg font-semibold text-gray-900">{user?.name}</p>
          <p className="text-sm text-gray-500">{user?.email}</p>
          <span className="inline-flex items-center gap-1 mt-1 text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded-full font-medium">
            <Shield className="w-3 h-3" />
            Verified Account
          </span>
        </div>
      </div>

      {/* Edit form */}
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-5">Account Details</h2>

        <form onSubmit={handleSave} className="space-y-5">
          {/* Name */}
          <div>
            <label className="label" htmlFor="profile-name">
              <span className="flex items-center gap-1.5">
                <User className="w-3.5 h-3.5" />
                Display Name
              </span>
            </label>
            {editing ? (
              <input
                id="profile-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input"
                autoFocus
                required
                maxLength={100}
              />
            ) : (
              <div className="flex items-center justify-between">
                <p className="text-gray-900 font-medium py-2">{user?.name}</p>
                <button
                  type="button"
                  onClick={() => setEditing(true)}
                  className="btn-secondary text-sm py-1.5 px-3"
                >
                  Edit
                </button>
              </div>
            )}
          </div>

          {/* Email — read-only */}
          <div>
            <label className="label">
              <span className="flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5" />
                Email Address
                <span className="text-gray-400 font-normal">(cannot be changed)</span>
              </span>
            </label>
            <div className="input bg-gray-50 text-gray-500 cursor-not-allowed select-none">
              {user?.email}
            </div>
          </div>

          {/* Action buttons — only show when editing */}
          {editing && (
            <div className="flex gap-3 pt-2">
              <button
                type="submit"
                disabled={saving || !name.trim()}
                className="btn-primary flex items-center gap-2"
              >
                {saving ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Changes
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Account info */}
      <div className="card mt-6 bg-gray-50 border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Account Information</h3>
        <div className="space-y-2 text-sm text-gray-600">
          <div className="flex justify-between">
            <span>User ID</span>
            <span className="font-mono text-xs text-gray-400">{user?.id}</span>
          </div>
          <div className="flex justify-between">
            <span>Authentication</span>
            <span className="text-green-600 font-medium">JWT (Secure Cookie)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
