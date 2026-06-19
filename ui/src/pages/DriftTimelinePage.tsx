/**
 * Drift Timeline Page
 *
 * Standalone page for viewing drift timeline visualization.
 * Accepts query parameters for filtering.
 *
 * Design Constraints:
 * - Observational language only
 * - No quality judgments
 * - Drift is descriptive, not evaluative
 */

import React, { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { ArrowLeft, AlertCircle } from "lucide-react";
import DriftTimeline from "../components/DriftTimeline";
import { Button } from "../components/ui/button";

const DriftTimelinePage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const agentId = searchParams.get("agent_id") || "";
  const agentVersion = searchParams.get("agent_version") || undefined;
  const environment = searchParams.get("environment") || undefined;

  const [hasParams, setHasParams] = useState(false);

  useEffect(() => {
    setHasParams(!!agentId);
  }, [agentId]);

  if (!hasParams) {
    return (
      <div className="container mx-auto px-4 py-10">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 max-w-2xl mx-auto">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 mt-0.5" />
            <div>
              <h2 className="text-lg font-semibold text-yellow-800 mb-2">
                Missing parameters
              </h2>
              <p className="text-sm text-yellow-700 mb-4">
                Provide agent_id as a query parameter to view the drift
                timeline.
              </p>
              <Link to="/behaviors">
                <Button>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Behavior Dashboard
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-10 space-y-6">
      <div>
        <Link
          to="/behaviors"
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Behavior Dashboard
        </Link>
        <h1 className="text-3xl font-semibold text-gray-900 mt-4">Drift timeline</h1>
        <p className="text-gray-600 mt-2">
          Chronological view of drift events for {agentId}
          {agentVersion && ` v${agentVersion}`}
          {environment && ` • ${environment}`}
        </p>
      </div>

      <DriftTimeline
        agentId={agentId}
        agentVersion={agentVersion}
        environment={environment}
      />
    </div>
  );
};

export default DriftTimelinePage;
