import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, LogOut, UserCircle } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import NotificationBell from '../layout/NotificationBell';
import toast from 'react-hot-toast';

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      toast.success('Logged out');
      navigate('/login');
    } catch {
      toast.error('Logout failed');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <Link to="/dashboard" className="flex items-center gap-2">
              <span className="text-2xl">💰</span>
              <span className="font-bold text-gray-900 text-lg">SplitSmart</span>
              <span className="hidden sm:inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium ml-1">
                AI Powered
              </span>
            </Link>

            {/* Nav links */}
            {user && (
              <div className="hidden sm:flex items-center gap-1">
                <Link
                  to="/dashboard"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
                >
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </Link>
                <Link
                  to="/groups"
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 transition-colors"
                >
                  <Users className="w-4 h-4" />
                  Groups
                </Link>
              </div>
            )}

            {/* Right side: bell + user + logout */}
            {user ? (
              <div className="flex items-center gap-2">
                <NotificationBell />
                <Link
                  to="/profile"
                  className="flex items-center gap-2 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
                  title="Profile"
                >
                  <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center">
                    <span className="text-white text-xs font-bold">
                      {user.name?.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="hidden sm:block text-sm font-medium text-gray-700 max-w-[120px] truncate">
                    {user.name}
                  </span>
                </Link>
                <button
                  onClick={handleLogout}
                  className="p-2 rounded-lg text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" className="btn-secondary text-sm py-1.5 px-3">
                  Login
                </Link>
                <Link to="/register" className="btn-primary text-sm py-1.5 px-3">
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile nav links */}
      {user && (
        <div className="sm:hidden bg-white border-b border-gray-100 px-4 py-2 flex gap-4">
          <Link
            to="/dashboard"
            className="flex items-center gap-1.5 py-1.5 text-sm text-gray-600 hover:text-blue-600 transition-colors"
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </Link>
          <Link
            to="/groups"
            className="flex items-center gap-1.5 py-1.5 text-sm text-gray-600 hover:text-blue-600 transition-colors"
          >
            <Users className="w-4 h-4" />
            Groups
          </Link>
          <Link
            to="/profile"
            className="flex items-center gap-1.5 py-1.5 text-sm text-gray-600 hover:text-blue-600 transition-colors"
          >
            <UserCircle className="w-4 h-4" />
            Profile
          </Link>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-16 py-6 text-center text-sm text-gray-400">
        <p>SplitSmart — DSC4141 Academic Project</p>
      </footer>
    </div>
  );
}
