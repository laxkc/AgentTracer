/**
 * Error Page
 *
 * Displays a friendly fallback when the app crashes.
 */

import React, { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/button";
import { showToast } from "../utils/toast";

type ErrorPageProps = {
  error: Error | null;
  errorInfo?: React.ErrorInfo | null;
  onReset: () => void;
};

const ErrorPage: React.FC<ErrorPageProps> = ({ error, errorInfo, onReset }) => {
  const [copied, setCopied] = useState(false);
  const isDev = import.meta.env.DEV;

  const errorDetails = useMemo(() => {
    const details = [
      error?.message || "Unknown error",
      error?.stack,
      errorInfo?.componentStack,
    ]
      .filter(Boolean)
      .join("\n");
    return details.trim();
  }, [error, errorInfo]);

  const handleCopy = async () => {
    if (!errorDetails) {
      showToast.error("No error details available to copy.");
      return;
    }

    try {
      await navigator.clipboard.writeText(errorDetails);
      setCopied(true);
      showToast.success("Error details copied.");
      window.setTimeout(() => setCopied(false), 2000);
    } catch (copyError) {
      console.error("Failed to copy error details:", copyError);
      showToast.error("Unable to copy error details.");
    }
  };

  const handleReset = () => {
    onReset();
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-6 py-16">
      <div className="max-w-2xl w-full bg-white border border-gray-200 rounded-xl shadow-sm p-8 space-y-6">
        <div className="space-y-2">
          <p className="text-sm font-semibold text-red-600">Unexpected Error</p>
          <h1 className="text-2xl font-semibold text-gray-900">
            Something went wrong while loading this page.
          </h1>
          <p className="text-gray-600">
            Try refreshing the page. If the problem persists, copy the error details and
            share them with support.
          </p>
        </div>

        <div className="flex flex-wrap gap-3">
          <Button onClick={handleReset}>Reload</Button>
          <Link to="/">
            <Button variant="outline">Back to home</Button>
          </Link>
          <Button variant="ghost" onClick={handleCopy}>
            {copied ? "Copied" : "Copy error details"}
          </Button>
        </div>

        {isDev && errorDetails && (
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
            <p className="text-xs font-semibold text-gray-600 mb-2">Stack trace</p>
            <pre className="text-xs text-gray-700 whitespace-pre-wrap break-words">
              {errorDetails}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default ErrorPage;
