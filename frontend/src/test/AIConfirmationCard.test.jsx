/**
 * Frontend component tests.
 * Tests the AI Confirmation Card and UI components.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AIConfirmationCard from '../components/ai/AIConfirmationCard';

const mockMembers = [
  { id: 1, name: 'Aditya' },
  { id: 2, name: 'Rahul' },
  { id: 3, name: 'Aman' },
];

const mockResult = {
  description: 'Dinner',
  amount: 900,
  payer_name: 'Aditya',
  participant_names: ['Aditya', 'Rahul', 'Aman'],
  confidence: 'high',
  notes: null,
};

describe('AIConfirmationCard', () => {
  it('renders parsed expense details', () => {
    render(
      <AIConfirmationCard
        result={mockResult}
        originalText="I paid 900 for dinner"
        warnings={[]}
        members={mockMembers}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onCancel={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByText('Dinner')).toBeInTheDocument();
    expect(screen.getByText('₹900.00')).toBeInTheDocument();
    // Aditya appears as payer AND as participant — use getAllByText
    const adityaElements = screen.getAllByText('Aditya');
    expect(adityaElements.length).toBeGreaterThanOrEqual(1);
  });

  it('shows original text in a quote', () => {
    render(
      <AIConfirmationCard
        result={mockResult}
        originalText="I paid 900 for dinner"
        warnings={[]}
        members={mockMembers}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onCancel={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByText(/"I paid 900 for dinner"/)).toBeInTheDocument();
  });

  it('shows warnings when provided', () => {
    render(
      <AIConfirmationCard
        result={{ ...mockResult, payer_name: null }}
        originalText="Dinner"
        warnings={["AI suggested payer 'Ghost' who is not in this group."]}
        members={mockMembers}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onCancel={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByText(/Attention needed/i)).toBeInTheDocument();
  });

  it('calls onCancel when Cancel is clicked', () => {
    const onCancel = vi.fn();
    render(
      <AIConfirmationCard
        result={mockResult}
        originalText="Dinner"
        warnings={[]}
        members={mockMembers}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onCancel={onCancel}
        submitting={false}
      />
    );

    fireEvent.click(screen.getByText('Cancel'));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it('calls onConfirm with correct data when confirmed', () => {
    const onConfirm = vi.fn();
    render(
      <AIConfirmationCard
        result={mockResult}
        originalText="Dinner"
        warnings={[]}
        members={mockMembers}
        onConfirm={onConfirm}
        onEdit={vi.fn()}
        onCancel={vi.fn()}
        submitting={false}
      />
    );

    fireEvent.click(screen.getByText('Confirm & Save'));
    expect(onConfirm).toHaveBeenCalledOnce();
    expect(onConfirm).toHaveBeenCalledWith({
      description: 'Dinner',
      amount: 900,
      payer_name: 'Aditya',
      participant_names: ['Aditya', 'Rahul', 'Aman'],
    });
  });

  it('disables Confirm button when required fields are missing', () => {
    render(
      <AIConfirmationCard
        result={{ ...mockResult, description: null, amount: null }}
        originalText="Incomplete"
        warnings={[]}
        members={mockMembers}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onCancel={vi.fn()}
        submitting={false}
      />
    );

    const confirmBtn = screen.getByText('Confirm & Save');
    expect(confirmBtn).toBeDisabled();
  });

  it('shows high confidence badge', () => {
    render(
      <AIConfirmationCard
        result={{ ...mockResult, confidence: 'high' }}
        originalText="Dinner"
        warnings={[]}
        members={mockMembers}
        onConfirm={vi.fn()}
        onEdit={vi.fn()}
        onCancel={vi.fn()}
        submitting={false}
      />
    );

    expect(screen.getByText('high confidence')).toBeInTheDocument();
  });
});
