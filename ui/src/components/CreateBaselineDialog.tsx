/**
 * Create Baseline Dialog Component
 *
 * Form for creating new behavioral baselines
 * - Agent identification
 * - Environment and type selection
 * - Time window configuration
 * - Sample size and approval settings
 */

import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';

interface CreateBaselineForm {
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_type: string;
  window_start: string;
  window_end: string;
  min_sample_size: number;
  approved_by: string;
  description: string;
  auto_activate: boolean;
}

interface CreateBaselineDialogProps {
  open: boolean;
  onClose: () => void;
  formData: CreateBaselineForm;
  onFormChange: (field: keyof CreateBaselineForm, value: any) => void;
  onSubmit: () => void;
  isLoading?: boolean;
}

const CreateBaselineDialog: React.FC<CreateBaselineDialogProps> = ({
  open,
  onClose,
  formData,
  onFormChange,
  onSubmit,
  isLoading = false,
}) => {
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Baseline</DialogTitle>
          <DialogDescription>
            Build a behavioral baseline from historical agent data
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 px-6 py-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block text-gray-700">
                Agent ID <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.agent_id}
                onChange={(e) => onFormChange('agent_id', e.target.value)}
                placeholder="e.g., customer_support_agent"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block text-gray-700">
                Agent Version <span className="text-red-500">*</span>
              </label>
              <Input
                value={formData.agent_version}
                onChange={(e) => onFormChange('agent_version', e.target.value)}
                placeholder="e.g., 1.0.0"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block text-gray-700">
                Environment
              </label>
              <select
                value={formData.environment}
                onChange={(e) => onFormChange('environment', e.target.value)}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="production">Production</option>
                <option value="staging">Staging</option>
                <option value="development">Development</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block text-gray-700">
                Baseline Type
              </label>
              <select
                value={formData.baseline_type}
                onChange={(e) => onFormChange('baseline_type', e.target.value)}
                className="flex h-10 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="version">Version</option>
                <option value="time_window">Time Window</option>
                <option value="manual">Manual</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block text-gray-700">
                Window Start <span className="text-red-500">*</span>
              </label>
              <Input
                type="datetime-local"
                value={formData.window_start}
                onChange={(e) => onFormChange('window_start', e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block text-gray-700">
                Window End <span className="text-red-500">*</span>
              </label>
              <Input
                type="datetime-local"
                value={formData.window_end}
                onChange={(e) => onFormChange('window_end', e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block text-gray-700">
              Min Sample Size
            </label>
            <Input
              type="number"
              value={formData.min_sample_size}
              onChange={(e) => onFormChange('min_sample_size', parseInt(e.target.value))}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block text-gray-700">
              Approved By
            </label>
            <Input
              value={formData.approved_by}
              onChange={(e) => onFormChange('approved_by', e.target.value)}
              placeholder="e.g., john.doe@example.com"
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block text-gray-700">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => onFormChange('description', e.target.value)}
              placeholder="Optional description of this baseline"
              rows={3}
              className="flex w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto_activate"
              checked={formData.auto_activate}
              onChange={(e) => onFormChange('auto_activate', e.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="auto_activate" className="text-sm font-medium text-gray-700">
              Auto-activate baseline after creation
            </label>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={onSubmit} disabled={isLoading}>
            {isLoading ? 'Creating...' : 'Create Baseline'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default CreateBaselineDialog;
