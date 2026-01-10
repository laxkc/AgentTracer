/**
 * Baseline form schema.
 */

import { z } from 'zod';

export const baselineFormSchema = z
  .object({
    agent_id: z
      .string()
      .trim()
      .min(1, 'Agent ID is required')
      .max(100, 'Agent ID too long')
      .regex(/^[a-zA-Z0-9_-]+$/, 'Agent ID can only contain letters, numbers, dashes, and underscores'),
    agent_version: z
      .string()
      .trim()
      .min(1, 'Agent version is required')
      .regex(/^v?\d+\.\d+\.\d+$/, 'Version must be semantic (e.g., v1.0.0 or 1.0.0)'),
    environment: z.enum(['production', 'staging', 'development']),
    baseline_type: z.enum(['time_window', 'version', 'manual']),
    window_start: z.string().min(1, 'Start date is required'),
    window_end: z.string().min(1, 'End date is required'),
    min_sample_size: z
      .number({ message: 'Sample size must be a number' })
      .int('Sample size must be an integer')
      .min(10, 'Sample size must be at least 10')
      .max(10000, 'Sample size cannot exceed 10,000'),
    approved_by: z.string().email('Invalid email format').optional().or(z.literal('')),
    description: z.string().max(500, 'Description too long').optional().or(z.literal('')),
    auto_activate: z.boolean(),
  })
  .refine(
    (data) => {
      if (!data.window_start || !data.window_end) return true;
      return new Date(data.window_end) > new Date(data.window_start);
    },
    {
      message: 'End date must be after start date',
      path: ['window_end'],
    }
  );

export type BaselineFormData = z.infer<typeof baselineFormSchema>;
