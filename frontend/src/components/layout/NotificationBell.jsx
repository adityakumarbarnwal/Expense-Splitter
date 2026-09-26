import React, { useState, useRef, useEffect } from 'react';
import { Bell, Check, CheckCheck } from 'lucide-react';
import { notificationsApi } from '../../services/api';
import { useNavigate } from 'react-router-dom';

/**
 * NotificationBell — Navbar bell icon with unread badge and dropdown.
 *
 * Polls every 60 seconds for new notifications.
 * Clicking a notification with a related_entity_id navigates to that group.
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

  // Initial fetch + polling every 60s
  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 60_000);
    return () => clearInterval(interval);
  }, []);

  // Close dropdown when clicking outside
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
        setData((prev) => ({
          ...prev,
          unread_count: Math.max(0, prev.unread_count - 1),
          notifications: prev.notifications.map((n) =>
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
      setData((prev) => ({
        ...prev,
        unread_count: 0,
        notifications: prev.notifications.map((n) => ({ ...n, read: true })),
      }));
    } catch {/* ignore */} finally {
      setLoading(false);
    }
  };

  const { notifications, unread_count } = data;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => { setOpen((o) => !o); if (!open) fetchNotifications(); }}
        className="relative p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition-colors"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unread_count > 0 && (
          <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            {unread_count > 9 ? '9+' : unread_count}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
            <span className="font-semibold text-gray-900 text-sm">Notifications</span>
            {unread_count > 0 && (
              <button
                onClick={handleMarkAllRead}
                disabled={loading}
                className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div className="max-h-80 overflow-y-auto divide-y divide-gray-50">
            {notifications.length === 0 ? (
              <div className="py-8 text-center text-gray-400 text-sm">
                <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
                No notifications yet
              </div>
            ) : (
              notifications.slice(0, 20).map((n) => (
                <button
                  key={n.id}
                  onClick={() => handleMarkRead(n)}
                  className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors flex items-start gap-3 ${
                    !n.read ? 'bg-blue-50/60' : ''
                  }`}
                >
                  <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${!n.read ? 'bg-blue-500' : 'bg-transparent'}`} />
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm leading-snug ${!n.read ? 'text-gray-900 font-medium' : 'text-gray-600'}`}>
                      {n.message}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {new Date(n.created_at).toLocaleDateString('en-IN', {
                        day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                      })}
                    </p>
                  </div>
                  {!n.read && <Check className="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-1" />}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
