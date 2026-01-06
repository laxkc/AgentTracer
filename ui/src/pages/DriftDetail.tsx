/**
 * Drift Detail Page
 *
 * Detailed view of a single drift event showing baseline vs observed comparison
 */

import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ArrowLeft,
  AlertTriangle,
  Activity,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Clock,
  CheckCircle2,
  Info,
} from "lucide-react";
import toast from "react-hot-toast";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";

interface BehaviorDrift {
  drift_id: string;
  baseline_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  drift_type: string;
  metric: string;
  baseline_value: number;
  observed_value: number;
  delta: number;
  delta_percent: number;
  significance: number;
  test_method: string;
  severity: string;
  detected_at: string;
  observation_window_start: string;
  observation_window_end: string;
  observation_sample_size: number;
  resolved_at: string | null;
  created_at: string;
}

interface BehaviorBaseline {
  baseline_id: string;
  profile_id: string;
  agent_id: string;
  agent_version: string;
  environment: string;
  baseline_type: string;
  approved_by: string | null;
  approved_at: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

const DriftDetail: React.FC = () => {
  const { driftId } = useParams<{ driftId: string }>();
  const [drift, setDrift] = useState<BehaviorDrift | null>(null);
  const [baseline, setBaseline] = useState<BehaviorBaseline | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resolving, setResolving] = useState(false);

  useEffect(() => {
    if (driftId) {
      fetchDriftDetails();
    }
  }, [driftId]);

  const fetchDriftDetails = async () => {
    try {
      setLoading(true);
      setError(null);

      const driftResponse = await fetch(`http://localhost:8001/v1/phase3/drift/${driftId}`);
      if (!driftResponse.ok) {
        throw new Error("Drift event not found");
      }
      const driftEvent = await driftResponse.json();
      setDrift(driftEvent);

      const baselineResponse = await fetch(
        `http://localhost:8001/v1/phase3/baselines/${driftEvent.baseline_id}`
      );
      if (baselineResponse.ok) {
        const baselineData = await baselineResponse.json();
        setBaseline(baselineData);
      }

      setLoading(false);
    } catch (error) {
      setError(error instanceof Error ? error.message : "Failed to fetch drift details");
      setLoading(false);
    }
  };

  const handleResolveDrift = async () => {
    if (!drift || drift.resolved_at) {
      return;
    }

    try {
      setResolving(true);
      const response = await fetch(`http://localhost:8001/v1/phase3/drift/${driftId}/resolve`, {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to resolve drift");
      }

      const resolvedDrift = await response.json();
      setDrift(resolvedDrift);
      toast.success("Drift event marked as resolved");
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to resolve drift");
    } finally {
      setResolving(false);
    }
  };

  const getSeverityVariant = (severity: string) => {
    switch (severity) {
      case "low":
        return "secondary";
      case "medium":
        return "default";
      case "high":
        return "destructive";
      default:
        return "secondary";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading drift details...</p>
        </div>
      </div>
    );
  }

  if (error || !drift) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <p className="text-red-600">Error: {error || "Drift event not found"}</p>
          <Link to="/behaviors" className="mt-4 inline-block text-blue-600 hover:text-blue-700">
            <Button variant="outline" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const changeVerb = drift.delta > 0 ? "increased" : "decreased";
  const TrendIcon = drift.delta > 0 ? TrendingUp : TrendingDown;

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl space-y-6">
      {/* Page Header - SINGLE INSTANCE */}
      <div className="space-y-1">
        <Link
          to="/behaviors"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium mb-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Behavior Dashboard
        </Link>
        <div className="flex items-center gap-3">
          <div className="p-2 bg-orange-100 rounded-lg">
            <AlertTriangle className="h-6 w-6 text-orange-600" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">Drift Event Details</h1>
        </div>
        <p className="text-gray-500">Detailed view of detected behavioral change</p>
      </div>

      {/* Summary Card */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-start justify-between mb-4">
            <div className="space-y-3">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge variant={getSeverityVariant(drift.severity)}>
                  {drift.severity} severity
                </Badge>
                <Badge variant="secondary">{drift.drift_type} drift</Badge>
                {drift.resolved_at && (
                  <Badge variant="default" className="bg-green-100 text-green-800 border-green-200">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Resolved
                  </Badge>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Activity className="h-5 w-5 text-gray-400" />
                <div className="text-lg font-semibold text-gray-900">{drift.metric}</div>
              </div>
              <div className="text-sm text-gray-600">
                {drift.agent_id} v{drift.agent_version} ({drift.environment})
              </div>
            </div>
            <div className="text-right space-y-1">
              <div className="text-sm text-gray-600">Detected</div>
              <div className="text-base font-medium text-gray-900">
                {new Date(drift.detected_at).toLocaleDateString()}
              </div>
              <div className="text-xs text-gray-500">
                {new Date(drift.detected_at).toLocaleTimeString()}
              </div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200 flex items-start gap-3">
            <TrendIcon className="h-5 w-5 text-gray-600 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-gray-700 mb-1">Observed Change</div>
              <p className="text-base text-gray-900">
                The metric <span className="font-semibold">{drift.metric}</span> {changeVerb} from{" "}
                <span className="font-bold text-gray-900">
                  {(drift.baseline_value * 100).toFixed(2)}%
                </span>{" "}
                to{" "}
                <span className="font-bold text-gray-900">
                  {(drift.observed_value * 100).toFixed(2)}%
                </span>
                , representing a{" "}
                <span className="font-bold text-gray-900">
                  {drift.delta_percent > 0 ? "+" : ""}
                  {drift.delta_percent.toFixed(1)}%
                </span>{" "}
                change.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Comparison Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Baseline Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Baseline Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center mb-4">
              <div className="text-5xl font-bold text-gray-900 mb-2">
                {(drift.baseline_value * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">Expected behavior</div>
            </div>
            {baseline && (
              <div className="pt-4 border-t border-gray-200 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Baseline Type</span>
                  <span className="text-gray-900 font-medium">{baseline.baseline_type}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Created</span>
                  <span className="text-gray-900 font-medium">
                    {new Date(baseline.created_at).toLocaleDateString()}
                  </span>
                </div>
                {baseline.approved_by && (
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-gray-600">Approved By</span>
                    <span className="text-gray-900 font-medium">{baseline.approved_by}</span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Observed Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendIcon className="h-5 w-5" />
              Observed Value
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center mb-4">
              <div className="text-5xl font-bold text-gray-900 mb-2">
                {(drift.observed_value * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-gray-600">Current behavior</div>
            </div>
            <div className="pt-4 border-t border-gray-200 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Window Start</span>
                <span className="text-gray-900 font-medium">
                  {new Date(drift.observation_window_start).toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Window End</span>
                <span className="text-gray-900 font-medium">
                  {new Date(drift.observation_window_end).toLocaleDateString()}
                </span>
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-600">Sample Size</span>
                <span className="text-gray-900 font-medium">
                  {drift.observation_sample_size} runs
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Statistical Analysis */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Statistical Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Test Method</dt>
              <dd className="text-sm text-gray-900">{drift.test_method}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Statistical Significance</dt>
              <dd className="text-sm text-gray-900">
                p = {drift.significance.toFixed(4)}
                {drift.significance < 0.05 && (
                  <span className="ml-2 text-xs text-green-600 font-medium">(p &lt; 0.05)</span>
                )}
              </dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Absolute Change</dt>
              <dd className="text-sm text-gray-900">
                {drift.delta > 0 ? "+" : ""}
                {(drift.delta * 100).toFixed(2)}%
              </dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Relative Change</dt>
              <dd className="text-sm text-gray-900">
                {drift.delta_percent > 0 ? "+" : ""}
                {drift.delta_percent.toFixed(1)}%
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      {/* Context Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            Context Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Drift ID</dt>
              <dd className="text-sm text-gray-900 font-mono">{drift.drift_id}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Baseline ID</dt>
              <dd className="text-sm text-gray-900 font-mono">{drift.baseline_id}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Drift Type</dt>
              <dd className="text-sm text-gray-900">{drift.drift_type}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Severity</dt>
              <dd className="text-sm text-gray-900">{drift.severity}</dd>
            </div>
            <div className="space-y-1">
              <dt className="text-sm font-medium text-gray-600">Created At</dt>
              <dd className="text-sm text-gray-900">
                {new Date(drift.created_at).toLocaleString()}
              </dd>
            </div>
            {drift.resolved_at && (
              <div className="space-y-1">
                <dt className="text-sm font-medium text-gray-600">Resolved At</dt>
                <dd className="text-sm text-gray-900">
                  {new Date(drift.resolved_at).toLocaleString()}
                </dd>
              </div>
            )}
          </dl>
        </CardContent>
      </Card>

      {/* Interpretation Guide */}
      <Card className="bg-blue-50 border-blue-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-900">
            <Info className="h-5 w-5" />
            Interpreting This Drift Event
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-blue-800">
          <p>
            <strong>What this means:</strong> The agent's behavior has changed relative to the
            established baseline. Specifically, the distribution or value of{" "}
            <span className="font-medium">{drift.metric}</span> has shifted.
          </p>
          <p>
            <strong>What this does NOT mean:</strong> This drift detection does not indicate
            whether the change is good, bad, correct, or incorrect. Drift is purely observational.
          </p>
          <div>
            <p className="mb-2">
              <strong>Next steps:</strong> Review the context of this change. Consider:
            </p>
            <ul className="list-disc list-inside ml-4 space-y-1">
              <li>Was there a recent deployment or configuration change?</li>
              <li>Is this change expected based on known system updates?</li>
              <li>Does the magnitude of change warrant investigation?</li>
              <li>Are there related drift events in other metrics?</li>
            </ul>
          </div>
          <p>
            <strong>Remember:</strong> Human interpretation is required to determine if action is
            needed. The platform provides visibility, not decisions.
          </p>
        </CardContent>
      </Card>

      {/* Related Links */}
      <Card>
        <CardHeader>
          <CardTitle>Related</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Link
              to={`/drift/timeline?agent_id=${drift.agent_id}&agent_version=${drift.agent_version}&environment=${drift.environment}`}
            >
              <Button variant="outline" size="sm">
                <Clock className="h-4 w-4 mr-2" />
                View Timeline for {drift.agent_id}
              </Button>
            </Link>
            <Link to="/drift/compare">
              <Button variant="outline" size="sm">
                <BarChart3 className="h-4 w-4 mr-2" />
                Compare Drift Events
              </Button>
            </Link>
            <Link to="/behaviors">
              <Button variant="outline" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>

      {/* Actions */}
      {!drift.resolved_at && (
        <div className="flex gap-4">
          <Button onClick={handleResolveDrift} disabled={resolving}>
            <CheckCircle2 className="h-4 w-4 mr-2" />
            {resolving ? "Resolving..." : "Mark as Resolved"}
          </Button>
        </div>
      )}
    </div>
  );
};

export default DriftDetail;
