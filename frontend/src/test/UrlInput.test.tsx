import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { UrlInput } from '../components/UrlInput';

describe('UrlInput Component', () => {
  it('renders input with placeholder and button', () => {
    const handleAnalyze = vi.fn();
    render(<UrlInput onAnalyze={handleAnalyze} isLoading={false} />);

    expect(screen.getByPlaceholderText('https://example.com')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyze/i })).toBeInTheDocument();
  });

  it('displays error message if submitted with empty URL', () => {
    const handleAnalyze = vi.fn();
    render(<UrlInput onAnalyze={handleAnalyze} isLoading={false} />);

    fireEvent.click(screen.getByRole('button', { name: /analyze/i }));
    expect(screen.getByText(/please enter a target url/i)).toBeInTheDocument();
    expect(handleAnalyze).not.toHaveBeenCalled();
  });

  it('auto-prefixes https protocol if missing', () => {
    const handleAnalyze = vi.fn();
    render(<UrlInput onAnalyze={handleAnalyze} isLoading={false} />);

    const input = screen.getByPlaceholderText('https://example.com');
    fireEvent.change(input, { target: { value: 'example.com' } });
    fireEvent.click(screen.getByRole('button', { name: /analyze/i }));

    expect(handleAnalyze).toHaveBeenCalledWith('https://example.com', 'static');
  });

  it('allows switching to deep mode and passes correct parameter', () => {
    const handleAnalyze = vi.fn();
    render(<UrlInput onAnalyze={handleAnalyze} isLoading={false} />);

    fireEvent.click(screen.getByText(/deep mode/i));
    const input = screen.getByPlaceholderText('https://example.com');
    fireEvent.change(input, { target: { value: 'https://mysite.com' } });
    fireEvent.click(screen.getByRole('button', { name: /analyze/i }));

    expect(handleAnalyze).toHaveBeenCalledWith('https://mysite.com', 'full');
  });
});
