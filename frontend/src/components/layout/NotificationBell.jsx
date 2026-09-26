import React, { useState, useRef, useEffect } from 'react';
import { Bell, Check, CheckCheck } from 'lucide-react';
import { notificationsApi } from '../../services/api';
import { useNavigate } from 'react-router-dom';

/**
 * NotificationBell — Glassmorphic navbar bell with dropdown.
 * Polls every 60 seconds. Clicking navigates to related group.
 */
export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState({ notifications: [], unread_count: 0 });
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  const fetchNotifications = async () => {
    try {
      const res = await notificationsApi.list();
      setData(res);
    } catch {
      // Silently fail — notifications are non-critical
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60_000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleMarkRead = async (notification) => {
    if (!notification.read) {
      try {
        await notificationsApi.markRead(notification.id);
        setData(prev => ({
          ...prev,
          unread_count: Math.max(0, prev.unread_count - 1),
          notifications: prev.notifications.map(n =>
            n.id === notification.id ? { ...n, read: true } : n
          ),
        }));
      } catch {/* ignore */}
    }
    if (notification.related_entity_id) {
      setOpen(false);
      navigate(`/groups/${notification.related_entity_id}`);
    }
  };

  const handleMarkAllRead = async () => {
    setLoading(true);
    try {
      await notificationsApi.markAllRead();
      setData(prev => ({
        ...prev,
        unread_count: 0,
        notifications: prev.notifications.map(n => ({ ...n, read: true })),
      }));
    } catch {/* ignore */}
    finally { setLoading(false); }
  };

  const { notifications, unread_count } = data;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => { setOpen(o => !o); if (!open) fetchNotifications(); }}
        className="relative p-2 rounded-xl text-slate-500 hover:text-slate-700
                   hover:bg-white/50 transition-all"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unread_count > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4
                           bg-red-500 text-white text-[10px] font-bold
                           rounded-full flex items-center justify-center
                           ring-2 ring-white animate-pulse-soft">
            {unread_count > 9 ? '9+' : unread_count}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-80 glass-card-elevated
                        z-50 overflow-hidden p-0 border border-white/40
                        shadow-glass-elevated animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3
                          border-b border-slate-100/60">
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-900 text-sm">Notifications</span>
              {unread_count > 0 && (
                <span className="badge-indigo text-[10px]">{unread_count} new</span>
              )}
            </div>
            {unread_count > 0 && (
              <button onClick={handleMarkAllRead} disabled={loading}
                className="flex items-center gap-1 text-xs font-semibold
                           text-brand-600 hover:text-brand-700 disabled:opacity-50 transition-colors">
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="py-10 text-center">
                <Bell className="w-8 h-8 mx-auto mb-2 text-slate-200" />
                <p className="text-slate-400 text-sm font-medium">No notifications yet</p>
              </div>
            ) : (
              notifications.slice(0, 20).map(n => (
                <button
                  key={n.id}
                  onClick={() => handleMarkRead(n)}
                  className={`w-full text-left px-4 py-3 hover:bg-brand-50/30
                              transition-colors flex items-start gap-3 border-b
                              border-slate-50/60 last:border-0 ${
                    !n.read ? 'bg-brand-50/20' : ''
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                    !n.read ? 'bg-brand-500' : 'bg-transparent'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm leading-snug ${
                      !n.read ? 'text-slate-900 font-semibold' : 'text-slate-600'
                    }`}>
                      {n.message}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5 font-medium">
                      {new Date(n.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric', month: 'short',
                        hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </div>
                  {!n.read && <Check className="w-3.5 h-3.5 text-brand-400 flex-shrink-0 mt-1" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
