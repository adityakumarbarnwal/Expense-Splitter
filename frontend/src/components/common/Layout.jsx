import React from 'react';
import { Outlet, Link, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, LogOut, UserCircle, Zap } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import NotificationBell from '../layout/NotificationBell';
import toast from 'react-hot-toast';

const navLinkClass = ({ isActive }) =>
  `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
    isActive
      ? 'bg-brand-100/60 text-brand-700 shadow-sm'
      : 'text-slate-600 hover:text-slate-900 hover:bg-white/50'
  }`;

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

  const userInitial = user?.name?.charAt(0).toUpperCase() || '?';

  return (
    <div className="min-h-screen">
      {/* ── Glass Navbar ── */}
      <nav className="glass-nav sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* Brand */}
            <Link to="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-xl flex items-center justify-center
                              bg-brand-gradient shadow-brand flex-shrink-0
                              group-hover:shadow-brand-hover transition-all duration-200">
                <span className="text-white font-black text-base leading-none">S</span>
              </div>
              <div className="flex flex-col leading-none">
                <span className="font-black text-slate-900 text-base tracking-tight">SplitIt</span>
                <span className="text-[9px] font-semibold text-brand-500 tracking-widest uppercase -mt-0.5">
                  AI Powered
                </span>
              </div>
            </Link>

            {/* Desktop Nav */}
            {user && (
              <div className="hidden sm:flex items-center gap-1">
                <NavLink to="/dashboard" className={navLinkClass}>
                  <LayoutDashboard className="w-4 h-4" />
                  Dashboard
                </NavLink>
                <NavLink to="/groups" className={navLinkClass}>
                  <Users className="w-4 h-4" />
                  Groups
                </NavLink>
              </div>
            )}

            {/* Right side */}
            {user ? (
              <div className="flex items-center gap-2">
                {/* AI badge */}
                {/* <div className="hidden md:flex items-center gap-1 px-2 py-1 rounded-full
                                bg-violet-100/70 border border-violet-200/50">
                  <Zap className="w-3 h-3 text-violet-600" />
                  <span className="text-[10px] font-bold text-violet-700 tracking-wide">AI</span>
                </div> */}

                <NotificationBell />

                <Link
                  to="/profile"
                  className="flex items-center gap-2 px-2 py-1.5 rounded-xl
                             hover:bg-white/60 transition-all group"
                  title="Profile"
                >
                  <div className="w-7 h-7 rounded-full flex items-center justify-center
                                  bg-brand-gradient shadow-sm ring-2 ring-white/80">
                    <span className="text-white text-xs font-bold">{userInitial}</span>
                  </div>
                  <span className="hidden sm:block text-sm font-semibold text-slate-700
                                   max-w-[110px] truncate group-hover:text-brand-600 transition-colors">
                    {user.name}
                  </span>
                </Link>

                <button
                  onClick={handleLogout}
                  className="p-2 rounded-xl text-slate-400 hover:text-red-500
                             hover:bg-red-50/60 transition-all"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" className="btn-secondary text-sm py-1.5 px-3">Login</Link>
                <Link to="/register" className="btn-primary text-sm py-1.5 px-3">Register</Link>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Mobile nav */}
      {user && (
        <div className="sm:hidden border-b border-white/30 px-4 py-2 flex gap-1
                        bg-white/60 backdrop-blur-md">
          <NavLink to="/dashboard" className={navLinkClass}>
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </NavLink>
          <NavLink to="/groups" className={navLinkClass}>
            <Users className="w-4 h-4" />
            Groups
          </NavLink>
          <NavLink to="/profile" className={navLinkClass}>
            <UserCircle className="w-4 h-4" />
            Profile
          </NavLink>
        </div>
      )}

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="mt-16 py-6 text-center">
        <p className="text-xs text-slate-400 font-medium">
          SplitIt — Smart group expenses, simplified
        </p>
      </footer>
    </div>
  );
}
