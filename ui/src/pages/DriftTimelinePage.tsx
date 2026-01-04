/**
 * Phase 3 - Drift Timeline Page
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
import { ArrowLeft, Clock, AlertCircle } from "lucide-react";
import DriftTimeline from "../components/DriftTimeline";
import { Card, CardContent } from "../components/ui/card";
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
      <div className="container mx-auto px-4 py-8">
        <Card className="bg-yellow-50 border-yellow-200 max-w-2xl mx-auto">
          <CardContent className="pt-6 flex items-start gap-4">
            <AlertCircle className="h-6 w-6 text-yellow-600 mt-0.5" />
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-yellow-800 mb-2">
                Missing Parameters
              </h2>
              <p className="text-yellow-700 mb-4">
                Please provide agent_id as a query parameter to view the drift timeline.
              </p>
              <Link to="/behaviors">
                <Button>
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Go to Behavior Dashboard
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 space-y-6">
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
          <div className="p-2 bg-green-100 rounded-lg">
            <Clock className="h-6 w-6 text-green-600" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight">Drift Timeline</h1>
        </div>
        <p className="text-gray-500">
          Behavioral change timeline for {agentId}
          {agentVersion && ` v${agentVersion}`}
          {environment && ` (${environment})`}
        </p>
      </div>

      {/* Timeline Component */}
      <DriftTimeline agentId={agentId} agentVersion={agentVersion} environment={environment} />
    </div>
  );
};

export default DriftTimelinePage;
