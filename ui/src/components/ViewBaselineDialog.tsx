/**
 * View Baseline Dialog Component
 *
 * Displays detailed information about a baseline including:
 * - Baseline metadata
 * - Profile statistics
 * - Decision and signal distributions
 * - Latency statistics
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
import { Badge } from './ui/badge';
import { formatDateTime, formatNumber, capitalize, formatPercent } from '../utils/helpers';

interface Baseline {
  baseline_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_type: string;
  is_active: boolean;
  created_at: string;
  approved_by?: string | null;
  description?: string | null;
  profile_id: string;
}

interface Profile {
  profile_id: string;
  sample_size: number;
  window_start: string;
  window_end: string;
  latency_stats?: Record<string, number> | null;
  decision_distributions?: Record<string, Record<string, number>> | null;
  signal_distributions?: Record<string, Record<string, number>> | null;
}

interface ViewBaselineDialogProps {
  baseline: Baseline | null;
  profile: Profile | null;
  onClose: () => void;
}

const ViewBaselineDialog: React.FC<ViewBaselineDialogProps> = ({
  baseline,
  profile,
  onClose,
}) => {
  if (!baseline) return null;

  const getTypeVariant = (type: string): 'default' | 'secondary' | 'outline' => {
    switch (type) {
      case 'version':
        return 'default';
      case 'time_window':
        return 'secondary';
      default:
        return 'outline';
    }
  };

  return (
    <Dialog open={!!baseline} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Baseline Details</DialogTitle>
          <DialogDescription>
            {baseline.agent_id} v{baseline.agent_version} ({baseline.environment})
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 px-6 py-4">
          {/* Baseline Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-sm font-medium text-gray-500">Baseline ID</div>
              <div className="text-sm font-mono break-all">{baseline.baseline_id}</div>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Type</div>
              <Badge variant={getTypeVariant(baseline.baseline_type)}>
                {capitalize(baseline.baseline_type)}
              </Badge>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Status</div>
              <Badge variant={baseline.is_active ? 'success' : 'secondary'}>
                {baseline.is_active ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <div>
              <div className="text-sm font-medium text-gray-500">Created</div>
              <div className="text-sm">{formatDateTime(baseline.created_at)}</div>
            </div>
            {baseline.approved_by && (
              <div>
                <div className="text-sm font-medium text-gray-500">Approved By</div>
                <div className="text-sm">{baseline.approved_by}</div>
              </div>
            )}
            {baseline.description && (
              <div className="col-span-1 md:col-span-2">
                <div className="text-sm font-medium text-gray-500">Description</div>
                <div className="text-sm">{baseline.description}</div>
              </div>
            )}
          </div>

          {/* Profile Data */}
          {profile && (
            <div className="border-t pt-4 space-y-4">
              <h3 className="font-semibold text-gray-900">Profile Statistics</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <div className="text-sm font-medium text-gray-500">Sample Size</div>
                  <div className="text-lg font-bold">{formatNumber(profile.sample_size)} runs</div>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-500">Time Window</div>
                  <div className="text-sm break-words">
                    {formatDateTime(profile.window_start)} - {formatDateTime(profile.window_end)}
                  </div>
                </div>
              </div>

              {/* Latency Stats */}
              {profile.latency_stats && (
                <div>
                  <div className="text-sm font-medium text-gray-500 mb-2">Latency Statistics</div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {Object.entries(profile.latency_stats).map(([key, value]) => (
                      <div key={key}>
                        <div className="text-xs text-gray-500">{key.replace('_', ' ')}</div>
                        <div className="text-sm font-medium">{value.toFixed(2)}ms</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Decision Distributions */}
              {profile.decision_distributions &&
                Object.keys(profile.decision_distributions).length > 0 && (
                  <div>
                    <div className="text-sm font-medium text-gray-500 mb-2">
                      Decision Distributions
                    </div>
                    <div className="space-y-2">
                      {Object.entries(profile.decision_distributions).map(
                        ([decisionType, dist]) => (
                          <div key={decisionType} className="border rounded p-2">
                            <div className="text-xs font-medium mb-1">{decisionType}</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(dist as Record<string, number>).map(
                                ([choice, count]) => (
                                  <Badge key={choice} variant="outline">
                                    {choice}:{' '}
                                    {formatPercent((count / profile.sample_size) * 100, 0)}
                                  </Badge>
                                )
                              )}
                            </div>
                          </div>
                        )
                      )}
                    </div>
                  </div>
                )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ViewBaselineDialog;
