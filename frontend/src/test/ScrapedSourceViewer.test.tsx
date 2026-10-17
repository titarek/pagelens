import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ScrapedSourceViewer } from '../components/ScrapedSourceViewer';

describe('ScrapedSourceViewer Component', () => {
  const mockHtml = `<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello World</h1></body>
</html>`;

  const mockCss = `body { margin: 0; font-family: sans-serif; }
.hero { color: #6366f1; }`;

  it('renders HTML content by default with line numbers', () => {
    render(
      <ScrapedSourceViewer
        jobId="test-job-999"
        htmlContent={mockHtml}
        cssContent={mockCss}
        htmlBytes={mockHtml.length}
        cssBytes={mockCss.length}
      />
    );

    expect(screen.getByText('Scraped HTML')).toBeInTheDocument();
    expect(screen.getByText('Aggregated CSS')).toBeInTheDocument();
    expect(screen.getByText(/Hello World/i)).toBeInTheDocument();
    expect(screen.getByText('Download .html')).toBeInTheDocument();
  });

  it('switches to CSS tab upon click', () => {
    render(
      <ScrapedSourceViewer
        jobId="test-job-999"
        htmlContent={mockHtml}
        cssContent={mockCss}
        htmlBytes={mockHtml.length}
        cssBytes={mockCss.length}
      />
    );

    fireEvent.click(screen.getByText('Aggregated CSS'));

    expect(screen.getByText(/font-family: sans-serif/i)).toBeInTheDocument();
    expect(screen.getByText('Download .css')).toBeInTheDocument();
  });

  it('filters lines when search term is entered', () => {
    render(
      <ScrapedSourceViewer
        jobId="test-job-999"
        htmlContent={mockHtml}
        cssContent={mockCss}
        htmlBytes={mockHtml.length}
        cssBytes={mockCss.length}
      />
    );

    const searchInput = screen.getByPlaceholderText('Search code...');
    fireEvent.change(searchInput, { target: { value: 'Hello' } });

    expect(screen.getByText(/Hello World/i)).toBeInTheDocument();
    expect(screen.queryByText(/<title>Test<\/title>/i)).not.toBeInTheDocument();
  });
});
