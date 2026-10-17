import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { MetricCard } from '../components/MetricCard';
import { ShortcomingList } from '../components/ShortcomingList';
import { SecurityPanel } from '../components/SecurityPanel';
import { Shortcoming, SecurityAudit } from '../lib/types';

describe('MetricCard Component', () => {
  it('renders title, value, unit, and benchmark goal', () => {
    render(
      <MetricCard
        title="Largest Contentful Paint"
        value="1.45"
        unit="s"
        status="good"
        benchmark="<= 2.5s"
        description="Core Web Vital benchmark"
      />
    );

    expect(screen.getByText('Largest Contentful Paint')).toBeInTheDocument();
    expect(screen.getByText('1.45')).toBeInTheDocument();
    expect(screen.getByText('s')).toBeInTheDocument();
    expect(screen.getByText('Goal: <= 2.5s')).toBeInTheDocument();
    expect(screen.getByText('GOOD')).toBeInTheDocument();
  });
});

describe('ShortcomingList Component', () => {
  const mockShortcomings: Shortcoming[] = [
    {
      id: 'large-html',
      severity: 'high',
      title: 'Excessive HTML Document Size',
      cause: 'HTML payload exceeds 100 KB uncompressed.',
      fix: 'Paginate large lists and remove inline state.',
      example: '<div class="virtualized-list">...</div>',
      reference: 'https://web.dev/reduce-dom-size',
    },
    {
      id: 'no-lazy-loading',
      severity: 'medium',
      title: 'Missing Image Lazy Loading',
      cause: 'Images below the fold are missing loading="lazy".',
      fix: 'Add loading="lazy" attribute.',
      example: '<img src="photo.jpg" loading="lazy">',
      reference: 'https://web.dev/lazy-loading',
    },
  ];

  it('renders all shortcomings and allows expanding details', () => {
    render(<ShortcomingList shortcomings={mockShortcomings} />);

    expect(screen.getByText('Excessive HTML Document Size')).toBeInTheDocument();
    expect(screen.getByText('Missing Image Lazy Loading')).toBeInTheDocument();

    // Click to expand second item
    fireEvent.click(screen.getByText('Missing Image Lazy Loading'));
    expect(screen.getByText(/Images below the fold are missing/i)).toBeInTheDocument();
    expect(screen.getByText(/Add loading="lazy" attribute/i)).toBeInTheDocument();
  });

  it('filters shortcomings by severity', () => {
    render(<ShortcomingList shortcomings={mockShortcomings} />);

    // Click 'High' filter tab
    fireEvent.click(screen.getByText(/High \(1\)/i));
    expect(screen.getByText('Excessive HTML Document Size')).toBeInTheDocument();
    expect(screen.queryByText('Missing Image Lazy Loading')).not.toBeInTheDocument();
  });
});

describe('SecurityPanel Component', () => {
  const mockSecurity: SecurityAudit = {
    score: 85,
    passed: 6,
    warnings: 1,
    failures: 1,
    checks: [
      {
        id: 'https-enforced',
        title: 'HTTPS Transport Encryption',
        status: 'pass',
        detail: 'Traffic is served securely over TLS.',
        fix: 'Maintain valid certificates.',
      },
      {
        id: 'hsts',
        title: 'Strict-Transport-Security (HSTS)',
        status: 'fail',
        detail: 'Missing HSTS response header.',
        fix: 'Add Strict-Transport-Security header.',
      },
    ],
  };

  it('renders security check status badges and findings', () => {
    render(<SecurityPanel security={mockSecurity} />);

    expect(screen.getByText('HTTPS Transport Encryption')).toBeInTheDocument();
    expect(screen.getByText('Strict-Transport-Security (HSTS)')).toBeInTheDocument();
    expect(screen.getByText('Traffic is served securely over TLS.')).toBeInTheDocument();
    expect(screen.getByText('Missing HSTS response header.')).toBeInTheDocument();
  });
});
