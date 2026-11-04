import React, { useState, useRef, useEffect, useCallback, useId } from 'react';
import { Check, ChevronDown, Search, User } from 'lucide-react';

/**
 * MemberDropdown — polished custom dropdown for selecting a group member.
 *
 * Replaces the native <select> in NaturalLanguageInput with a component that
 * matches SplitIt's glass-card design system: purple gradient, rounded corners,
 * subtle borders, smooth animation, hover/focus/selected states.
 *
 * Features:
 * - Smooth open/close animation (CSS transition)
 * - Live search filter (shown when members > 5)
 * - Keyboard navigation (ArrowUp/Down, Enter, Escape, Tab)
 * - Closes on outside click or Escape
 * - Layered above surrounding content (z-50)
 * - Selected member highlighted with checkmark
 * - Current user marked with "(You)"
 * - Handles long names gracefully with truncation + tooltip
 * - Full ARIA: role=combobox, listbox, option, aria-selected, aria-expanded
 * - Zero external dependencies beyond React
 *
 * Props:
 *   members       — array of { id, name }
 *   currentUserId — id of the signed-in user (shows "(You)")
 *   value         — currently selected member name string (or '')
 *   onChange      — (name: string) => void  — '' means "none selected"
 *   placeholder   — string (default: "Select your name (optional)")
 *   disabled      — boolean
 */
export default function MemberDropdown({
  members = [],
  currentUserId,
  value = '',
  onChange,
  placeholder = 'Select your name (optional)',
  disabled = false,
}) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [focusedIdx, setFocusedIdx] = useState(-1);

  const triggerRef = useRef(null);
  const listRef = useRef(null);
  const searchRef = useRef(null);
  const uid = useId(); // stable id for ARIA
  const showSearch = members.length > 5;

  // Filter members by search query
  const filtered = search.trim()
    ? members.filter((m) =>
        m.name.toLowerCase().includes(search.trim().toLowerCase())
      )
    : members;

  // Build display label for trigger button
  const selectedMember = members.find((m) => m.name === value);
  const triggerLabel = selectedMember
    ? `${selectedMember.name}${selectedMember.id === currentUserId ? ' (You)' : ''}`
    : placeholder;

  // Open / close helpers
  const openDropdown = useCallback(() => {
    if (disabled) return;
    setOpen(true);
    setSearch('');
    setFocusedIdx(-1);
    // Focus search field if shown, otherwise the list
    setTimeout(() => {
      if (showSearch && searchRef.current) searchRef.current.focus();
      else listRef.current?.focus();
    }, 50);
  }, [disabled, showSearch]);

  const closeDropdown = useCallback(() => {
    setOpen(false);
    setSearch('');
    setFocusedIdx(-1);
  }, []);

  const handleSelect = useCallback(
    (name) => {
      onChange(name);
      closeDropdown();
      triggerRef.current?.focus();
    },
    [onChange, closeDropdown]
  );

  const handleClear = useCallback(
    (e) => {
      e.stopPropagation();
      onChange('');
      closeDropdown();
    },
    [onChange, closeDropdown]
  );

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (
        !triggerRef.current?.contains(e.target) &&
        !listRef.current?.contains(e.target)
      ) {
        closeDropdown();
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open, closeDropdown]);

  // Keyboard navigation on the trigger
  const handleTriggerKey = (e) => {
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'ArrowDown') {
      e.preventDefault();
      if (!open) openDropdown();
      else setFocusedIdx((i) => Math.min(i + 1, filtered.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIdx((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Escape') closeDropdown();
  };

  // Keyboard navigation inside the list
  const handleListKey = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIdx((i) => Math.min(i + 1, filtered.length - 1));
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIdx((i) => Math.max(i - 1, 0));
    }
    if (e.key === 'Enter' && focusedIdx >= 0) {
      e.preventDefault();
      handleSelect(filtered[focusedIdx].name);
    }
    if (e.key === 'Escape') {
      closeDropdown();
      triggerRef.current?.focus();
    }
    if (e.key === 'Tab') {
      closeDropdown();
    }
  };

  // Scroll focused option into view
  useEffect(() => {
    if (!open || focusedIdx < 0 || !listRef.current) return;
    const items = listRef.current.querySelectorAll('[role="option"]');
    items[focusedIdx]?.scrollIntoView({ block: 'nearest' });
  }, [focusedIdx, open]);

  return (
    <div className="relative" style={{ isolation: 'isolate' }}>
      {/* ── Trigger button ─────────────────────────────────────────────── */}
      <button
        ref={triggerRef}
        type="button"
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${uid}-listbox`}
        aria-label="Select your name"
        disabled={disabled}
        onClick={() => (open ? closeDropdown() : openDropdown())}
        onKeyDown={handleTriggerKey}
        className={[
          'w-full flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm',
          'bg-white/70 backdrop-blur-sm transition-all duration-150 text-left',
          'focus:outline-none focus:ring-2 focus:ring-violet-400/50',
          open
            ? 'border-violet-400 shadow-[0_0_0_3px_rgba(139,92,246,0.12)]'
            : 'border-slate-200/80 hover:border-violet-300 hover:bg-white/90',
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
          !value ? 'text-slate-400' : 'text-slate-800 font-medium',
        ].join(' ')}
      >
        {/* Avatar / icon */}
        <span
          className={[
            'w-6 h-6 rounded-lg flex-shrink-0 flex items-center justify-center text-[10px] font-black',
            value
              ? 'bg-gradient-to-br from-violet-500 to-indigo-600 text-white'
              : 'bg-slate-100 text-slate-400',
          ].join(' ')}
        >
          {value ? value.charAt(0).toUpperCase() : <User className="w-3 h-3" />}
        </span>

        {/* Label */}
        <span className="flex-1 truncate">{triggerLabel}</span>

        {/* Clear × — only when something is selected */}
        {value && !disabled && (
          <span
            role="button"
            tabIndex={-1}
            onClick={handleClear}
            onKeyDown={(e) => e.key === 'Enter' && handleClear(e)}
            className="w-4 h-4 rounded-full bg-slate-200/80 hover:bg-red-100 text-slate-500
                       hover:text-red-500 flex items-center justify-center flex-shrink-0
                       transition-colors text-xs leading-none"
            aria-label="Clear selection"
          >
            ×
          </span>
        )}

        {/* Chevron */}
        <ChevronDown
          className={`w-4 h-4 flex-shrink-0 text-slate-400 transition-transform duration-200 ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* ── Dropdown panel ─────────────────────────────────────────────── */}
      {open && (
        <div
          className={[
            'absolute left-0 right-0 mt-1.5 rounded-2xl border border-white/60',
            'bg-white/90 backdrop-blur-xl shadow-[0_12px_40px_rgba(0,0,0,0.14),0_4px_12px_rgba(99,102,241,0.08)]',
            'overflow-hidden origin-top',
            'animate-dropdown',
          ].join(' ')}
          style={{ zIndex: 50 }}
        >
          {/* Search field */}
          {showSearch && (
            <div className="p-2 border-b border-slate-100/80">
              <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50/80 border border-slate-100">
                <Search className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                <input
                  ref={searchRef}
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setFocusedIdx(0);
                  }}
                  onKeyDown={handleListKey}
                  placeholder="Search members…"
                  className="flex-1 text-sm bg-transparent outline-none text-slate-700 placeholder:text-slate-400"
                />
              </div>
            </div>
          )}

          {/* Options list */}
          <ul
            ref={listRef}
            id={`${uid}-listbox`}
            role="listbox"
            aria-label="Group members"
            tabIndex={showSearch ? -1 : 0}
            onKeyDown={handleListKey}
            className="py-1.5 max-h-56 overflow-y-auto focus:outline-none"
          >
            {/* None / clear option */}
            <li
              role="option"
              aria-selected={value === ''}
              onClick={() => handleSelect('')}
              className={[
                'flex items-center gap-2.5 px-3 py-2 mx-1.5 rounded-xl cursor-pointer text-sm',
                'transition-colors duration-100',
                value === ''
                  ? 'bg-violet-50 text-violet-700'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700',
                focusedIdx === -1 ? 'ring-1 ring-violet-200/60' : '',
              ].join(' ')}
            >
              <span className="w-6 h-6 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
                <User className="w-3 h-3 text-slate-400" />
              </span>
              <span className="flex-1 italic">{placeholder}</span>
              {value === '' && <Check className="w-3.5 h-3.5 text-violet-500 flex-shrink-0" />}
            </li>

            {/* Member options */}
            {filtered.length === 0 ? (
              <li className="px-4 py-3 text-xs text-slate-400 text-center">
                No members match "{search}"
              </li>
            ) : (
              filtered.map((member, idx) => {
                const isSelected = member.name === value;
                const isYou = member.id === currentUserId;
                const isFocused = focusedIdx === idx;

                return (
                  <li
                    key={member.id}
                    role="option"
                    aria-selected={isSelected}
                    onClick={() => handleSelect(member.name)}
                    className={[
                      'flex items-center gap-2.5 px-3 py-2 mx-1.5 rounded-xl cursor-pointer',
                      'transition-colors duration-100 select-none',
                      isSelected
                        ? 'bg-gradient-to-r from-violet-50 to-indigo-50 text-violet-900'
                        : isFocused
                        ? 'bg-slate-50 text-slate-800'
                        : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900',
                    ].join(' ')}
                  >
                    {/* Member avatar */}
                    <span
                      className={[
                        'w-6 h-6 rounded-lg flex-shrink-0 flex items-center justify-center',
                        'text-[10px] font-black',
                        isSelected
                          ? 'bg-gradient-to-br from-violet-500 to-indigo-600 text-white'
                          : 'bg-slate-100 text-slate-500',
                      ].join(' ')}
                    >
                      {member.name.charAt(0).toUpperCase()}
                    </span>

                    {/* Name */}
                    <span className="flex-1 text-sm font-medium truncate" title={member.name}>
                      {member.name}
                    </span>

                    {/* You badge */}
                    {isYou && (
                      <span className="text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-full bg-violet-100 text-violet-600 flex-shrink-0">
                        You
                      </span>
                    )}

                    {/* Checkmark */}
                    {isSelected && (
                      <Check className="w-3.5 h-3.5 text-violet-600 flex-shrink-0" />
                    )}
                  </li>
                );
              })
            )}
          </ul>
        </div>
      )}

      {/* Inline keyframe — avoids adding a dependency or touching global CSS */}
      <style>{`
        @keyframes dropdownIn {
          from { opacity: 0; transform: scaleY(0.92) translateY(-4px); }
          to   { opacity: 1; transform: scaleY(1)   translateY(0); }
        }
        .animate-dropdown {
          animation: dropdownIn 150ms cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }
      `}</style>
    </div>
  );
}
