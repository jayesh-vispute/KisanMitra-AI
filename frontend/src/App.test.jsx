import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import App from './App';

describe('App', () => {
  it('renders without crashing', () => {
    // A simple test to verify React mounts
    const { container } = render(<App />);
    expect(container).toBeInTheDocument();
  });
});
