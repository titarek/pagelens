import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ScoreGauge, getScoreColor } from '../components/ScoreGauge';

describe('ScoreGauge Component', () => {
  it('correctly maps score numbers to color classes', () => {
    expect(getScoreColor(95).hex).toBe('#22c55e');
    expect(getScoreColor(80).hex).toBe('#22c55e');
    expect(getScoreColor(79).hex).toBe('#f59e0b');
    expect(getScoreColor(50).hex).toBe('#f59e0b');
    expect(getScoreColor(49).hex).toBe('#ef4444');
    expect(getScoreColor(10).hex).toBe('#ef4444');
  });

  it('renders with accessibility meter role and aria-valuenow', () => {
    render(<ScoreGauge score={88} label="Page Performance" />);

    const meter = screen.getByRole('meter');
    expect(meter).toBeInTheDocument();
    expect(meter).toHaveAttribute('aria-valuenow', '88');
    expect(meter).toHaveAttribute('aria-valuemin', '0');
    expect(meter).toHaveAttribute('aria-valuemax', '100');
    expect(meter).toHaveAttribute('aria-label', 'Page Performance');
    expect(screen.getByText('88')).toBeInTheDocument();
  });

  it('clamps scores outside 0-100 range', () => {
    render(<ScoreGauge score={150} />);
    const meter = screen.getByRole('meter');
    expect(meter).toHaveAttribute('aria-valuenow', '100');
  });
});
