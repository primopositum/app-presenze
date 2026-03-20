/**
 * Component Test Example - ErrorCard
 * 
 * This demonstrates how to test Svelte components
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ErrorCard from '$lib/components/ErrorCard.svelte';

describe('ErrorCard Component', () => {
	it('should render error message when provided', () => {
		const errorMessage = 'Test error message';
		
		render(ErrorCard, {
			props: {
				error: errorMessage
			}
		});
		
		expect(screen.getByText(errorMessage)).toBeInTheDocument();
	});

	it('should not render when error is null', () => {
		render(ErrorCard, {
			props: {
				error: null
			}
		});
		
		// Component should not render error content
		expect(screen.queryByText('Error')).not.toBeInTheDocument();
	});

	it('should not render when error is empty string', () => {
		render(ErrorCard, {
			props: {
				error: ''
			}
		});
		
		expect(screen.queryByRole('alert')).not.toBeInTheDocument();
	});

	it('should have alert role for accessibility', () => {
		render(ErrorCard, {
			props: {
				error: 'Test error'
			}
		});
		
		const alert = screen.getByRole('alert');
		expect(alert).toBeInTheDocument();
	});

	it('should apply error styling classes', () => {
		const { container } = render(ErrorCard, {
			props: {
				error: 'Test error'
			}
		});
		
		// Check for Tailwind error classes (adjust based on actual implementation)
		const errorElement = container.querySelector('.text-red-600, .text-danger, [class*="error"]');
		expect(errorElement).toBeInTheDocument();
	});
});
