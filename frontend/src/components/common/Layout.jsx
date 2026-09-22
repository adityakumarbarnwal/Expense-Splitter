import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Home, Users, Receipt, BarChart3 } from 'lucide-react';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Navigation */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-2">
              <span className="text-2xl">💰</span>
              <span className="font-bold text-gray-900 text-lg">SplitSmart</span>
              <span className="hidden sm:inline-block text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium ml-1">
                AI Powered
              </span>
            </Link>
            <div className="flex items-center gap-1 text-sm text-gray-500">
              <span>Group Expense Splitter</span>
            </div>
          </div>
        </div>
      </nav>

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
