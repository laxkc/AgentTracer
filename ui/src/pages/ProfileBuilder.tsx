/**
 * Profile Builder
 *
 * Build behavior profiles from observability data before creating baselines.
 * Allows preview of profile data before baseline creation.
 *
 * Design Constraints:
 * - Observational only
 * - Privacy-safe
 * - No behavior modification
 */

import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, TrendingUp, Clock, Percent } from 'lucide-react';
import toast from 'react-hot-toast';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { DatePicker } from '../components/ui/date-picker';
import { API_CONFIG, API_ENDPOINTS } from '../config/api';
import { apiGet, apiPost } from '../lib/apiClient';
import { Select } from '../components/ui/select';

interface BehaviorProfile {
  profile_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  window_start: string;
  window_end: string;
  sample_size: number;
  decision_distributions: Record<string, Record<string, number>>;
  signal_distributions: Record<string, Record<string, number>>;
  latency_stats: Record<string, number>;
  created_at: string;
}

const ProfileBuilder: React.FC = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    agent_id: '',
    agent_version: '',
    environment: 'production',
    window_start: '',
    window_end: '',
    min_sample_size: 100,
  });
  const [profile, setProfile] = useState<BehaviorProfile | null>(null);
  const [loading, setLoading] = useState(false);

  const handleBuildProfile = async () => {
    try {
      setLoading(true);

      if (!formData.agent_id || !formData.agent_version || !formData.window_start || !formData.window_end) {
        toast.error('Please fill in all required fields');
        setLoading(false);
        return;
      }

      const baseline = await apiPost<{ profile_id: string }>(
        API_ENDPOINTS.BASELINES,
        {
          agent_id: formData.agent_id,
          agent_version: formData.agent_version,
          environment: formData.environment,
          baseline_type: 'time_window',
          window_start: new Date(formData.window_start).toISOString(),
          window_end: new Date(formData.window_end).toISOString(),
          min_sample_size: formData.min_sample_size,
          auto_activate: false,
        },
        API_CONFIG.QUERY_API_BASE_URL
      );

      const profileData = await apiGet<BehaviorProfile>(
        API_ENDPOINTS.PROFILE_DETAIL(baseline.profile_id),
        API_CONFIG.QUERY_API_BASE_URL
      );
      setProfile(profileData);
      toast.success('Profile built successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to build profile');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateBaseline = () => {
    if (profile) {
      navigate('/baselines', { state: { profileId: profile.profile_id } });
    }
  };

  return (
    <div className="container mx-auto px-4 py-10 space-y-6">
      <div>
        <Link
          to="/baselines"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Baseline Manager
        </Link>
        <h1 className="text-3xl font-semibold text-gray-900 mt-3">Profiles</h1>
        <p className="text-gray-600 mt-2">
          Build behavioral profiles from agent runs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">Build profile</h2>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Agent ID <span className="text-red-500">*</span>
            </label>
            <Input
              type="text"
              value={formData.agent_id}
              onChange={(event) => setFormData({ ...formData, agent_id: event.target.value })}
              placeholder="e.g., support-agent"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Agent Version <span className="text-red-500">*</span>
            </label>
            <Input
              type="text"
              value={formData.agent_version}
              onChange={(event) => setFormData({ ...formData, agent_version: event.target.value })}
              placeholder="e.g., v1.0.0"
            />
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              Environment <span className="text-red-500">*</span>
            </label>
            <Select
              value={formData.environment}
              onChange={(event) => setFormData({ ...formData, environment: event.target.value })}
            >
              <option value="production">production</option>
              <option value="staging">staging</option>
              <option value="development">development</option>
            </Select>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Window Start <span className="text-red-500">*</span>
              </label>
              <DatePicker
                value={formData.window_start}
                onChange={(value) => setFormData({ ...formData, window_start: value })}
                placeholder="Select start date"
              />
            </div>

            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Window End <span className="text-red-500">*</span>
              </label>
              <DatePicker
                value={formData.window_end}
                onChange={(value) => setFormData({ ...formData, window_end: value })}
                placeholder="Select end date"
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">Min Sample Size</label>
            <Input
              type="number"
              value={formData.min_sample_size}
              onChange={(event) =>
                setFormData({ ...formData, min_sample_size: parseInt(event.target.value) || 100 })
              }
              min="1"
            />
            <p className="text-xs text-gray-500">
              Minimum number of runs required to build a valid profile.
            </p>
          </div>

          <Button onClick={handleBuildProfile} disabled className="w-full">
            Build Profile (coming soon)
          </Button>
          <p className="text-xs text-gray-500 text-center">
            Profile creation is temporarily disabled while the API endpoint is finalized.
          </p>
        </section>

        <section className="bg-white border border-gray-200 rounded-lg p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Profile preview</h2>
          {profile ? (
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="text-sm text-green-800 font-medium">Profile built successfully</p>
                    <p className="text-xs text-green-700 mt-1">Profile ID: {profile.profile_id}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <Clock className="h-4 w-4" />
                  Time window
                </div>
                <p className="text-sm text-gray-900 pl-6">
                  {new Date(profile.window_start).toLocaleString()} to{' '}
                  {new Date(profile.window_end).toLocaleString()}
                </p>
                <p className="text-xs text-gray-500 pl-6">Sample size: {profile.sample_size} runs</p>
              </div>

              {Object.keys(profile.decision_distributions).length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <TrendingUp className="h-4 w-4" />
                    Decision distributions
                  </div>
                  <div className="space-y-3 pl-6">
                    {Object.entries(profile.decision_distributions).map(([type, distribution]) => (
                      <div key={type} className="space-y-1.5">
                        <div className="text-xs font-medium text-gray-600">{type}</div>
                        <div className="flex flex-wrap gap-1.5">
                          {Object.entries(distribution).map(([option, prob]) => (
                            <Badge key={option} variant="secondary">
                              {option}: {(prob * 100).toFixed(1)}%
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(profile.signal_distributions).length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <Percent className="h-4 w-4" />
                    Signal distributions
                  </div>
                  <div className="space-y-3 pl-6">
                    {Object.entries(profile.signal_distributions).map(([type, distribution]) => (
                      <div key={type} className="space-y-1.5">
                        <div className="text-xs font-medium text-gray-600">{type}</div>
                        <div className="flex flex-wrap gap-1.5">
                          {Object.entries(distribution).map(([code, prob]) => (
                            <Badge key={code} variant="default">
                              {code}: {(prob * 100).toFixed(1)}%
                            </Badge>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {Object.keys(profile.latency_stats).length > 0 && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                    <Clock className="h-4 w-4" />
                    Latency statistics
                  </div>
                  <div className="grid grid-cols-2 gap-2 pl-6">
                    {Object.entries(profile.latency_stats).map(([stat, value]) => (
                      <div key={stat} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                        <div className="text-xs text-gray-600">{stat}</div>
                        <div className="text-sm font-medium text-gray-900">
                          {typeof value === 'number' ? value.toFixed(2) : value} ms
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <Button onClick={handleCreateBaseline} className="w-full" variant="default">
                Create baseline from profile
              </Button>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              <p className="text-sm">Build a profile to see a preview here.</p>
            </div>
          )}
        </section>
      </div>

      <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
        <p className="text-sm text-gray-700">
          <strong>About profiles:</strong> Behavior profiles are statistical snapshots of agent
          behavior over a time window. They aggregate observability data into distributions and
          statistics used to create baselines for drift detection.
        </p>
      </div>
    </div>
  );
};

export default ProfileBuilder;
