"""
Phase 3 - Alert Emitter

This module emits human-readable alerts for detected drift.
Alerts are informational, non-blocking, and non-judgmental.

Constraints:
- Alerts are informational only (describe what changed)
- Never prescribe actions or solutions
- Use observational language only
- No quality judgments ("better/worse", "correct/incorrect")
- Reference the baseline used
- Include statistical significance
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

import requests

from backend.drift_engine import BehaviorDriftDB


# Configure logging
logger = logging.getLogger(__name__)


class AlertEmitter:
    """
    Emits human-readable alerts for detected drift.

    Purpose:
    - Format drift as observational alert messages
    - Send to multiple channels (logs, webhooks, database)
    - Enforce neutral language

    Alerts are informational only - never prescriptive.
    """

    def __init__(self):
        """
        Initialize alert emitter.

        Loads webhook configuration from environment variables.
        """
        self.webhook_config = self._load_webhook_config()

    def emit(self, drift: BehaviorDriftDB) -> None:
        """
        Emit alert for detected drift.

        Sends to all configured channels:
        - Application logs (always)
        - Webhooks (if configured)

        Args:
            drift: BehaviorDriftDB object representing detected drift
        """
        # Format alert message
        message = self._format_alert_message(drift)

        # Log alert (always)
        self._log_alert(message, drift)

        # Send to webhooks (if configured)
        if self.webhook_config.get("slack", {}).get("enabled"):
            self._send_slack_webhook(message, drift)

        if self.webhook_config.get("pagerduty", {}).get("enabled"):
            self._send_pagerduty_alert(message, drift)

        # Custom webhook (generic)
        if self.webhook_config.get("webhook", {}).get("enabled"):
            self._send_generic_webhook(message, drift)

    def _format_alert_message(self, drift: BehaviorDriftDB) -> str:
        """
        Format drift as human-readable alert message.

        Language constraints:
        - Use "observed increase/decrease", "distribution shifted"
        - Avoid "better/worse", "correct/incorrect"
        - Reference baseline used
        - Include statistical significance

        Args:
            drift: BehaviorDriftDB object

        Returns:
            Formatted alert message string
        """
        # Determine change direction (neutral language)
        if drift.delta > 0:
            change_verb = "observed increase"
        elif drift.delta < 0:
            change_verb = "observed decrease"
        else:
            change_verb = "no change"

        # Format message
        message = (
            f"Behavioral drift detected\n"
            f"\n"
            f"Agent: {drift.agent_id} v{drift.agent_version} ({drift.environment})\n"
            f"Metric: {drift.metric}\n"
            f"Change: {change_verb} from {drift.baseline_value:.2%} to {drift.observed_value:.2%} "
            f"({drift.delta_percent:+.1f}%)\n"
            f"Severity: {drift.severity}\n"
            f"\n"
            f"Baseline: {drift.baseline_id}\n"
            f"Statistical significance: p={drift.significance:.4f}\n"
            f"Test method: {drift.test_method}\n"
            f"Detected: {drift.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"\n"
            f"Observation window: {drift.observation_window_start.strftime('%Y-%m-%d %H:%M')} to "
            f"{drift.observation_window_end.strftime('%Y-%m-%d %H:%M')} "
            f"({drift.observation_sample_size} runs)\n"
        )

        return message

    def _log_alert(self, message: str, drift: BehaviorDriftDB) -> None:
        """
        Log alert to application logs.

        Args:
            message: Formatted alert message
            drift: BehaviorDriftDB object
        """
        logger.warning(
            f"DRIFT_DETECTED: {drift.agent_id} v{drift.agent_version} - {drift.metric}",
            extra={
                "drift_id": str(drift.drift_id),
                "agent_id": drift.agent_id,
                "agent_version": drift.agent_version,
                "environment": drift.environment,
                "drift_type": drift.drift_type,
                "metric": drift.metric,
                "delta_percent": drift.delta_percent,
                "severity": drift.severity,
                "significance": drift.significance,
            },
        )

    def _send_slack_webhook(self, message: str, drift: BehaviorDriftDB) -> None:
        """
        Send alert to Slack webhook.

        Args:
            message: Formatted alert message
            drift: BehaviorDriftDB object
        """
        slack_config = self.webhook_config.get("slack", {})
        webhook_url = slack_config.get("webhook_url")

        if not webhook_url:
            logger.debug("Slack webhook URL not configured, skipping")
            return

        # Severity emoji (neutral, not judgmental)
        severity_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🔔",
        }
        emoji = severity_emoji.get(drift.severity, "ℹ️")

        # Build Slack message
        slack_message = {
            "text": f"{emoji} Behavioral Drift Detected",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} Behavioral Drift Detected",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Agent:*\n{drift.agent_id} v{drift.agent_version}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Environment:*\n{drift.environment}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Metric:*\n{drift.metric}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{drift.severity}",
                        },
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*Observed change:* {drift.baseline_value:.2%} → {drift.observed_value:.2%} "
                            f"({drift.delta_percent:+.1f}%)\n"
                            f"*Statistical significance:* p={drift.significance:.4f}\n"
                            f"*Sample size:* {drift.observation_sample_size} runs"
                        ),
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Detected at {drift.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                        }
                    ],
                },
            ],
        }

        # Send to Slack
        try:
            response = requests.post(
                webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Slack alert sent for drift {drift.drift_id}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    def _send_pagerduty_alert(self, message: str, drift: BehaviorDriftDB) -> None:
        """
        Send alert to PagerDuty.

        Args:
            message: Formatted alert message
            drift: BehaviorDriftDB object
        """
        pagerduty_config = self.webhook_config.get("pagerduty", {})
        routing_key = pagerduty_config.get("routing_key")

        if not routing_key:
            logger.debug("PagerDuty routing key not configured, skipping")
            return

        # Map severity to PagerDuty severity
        severity_map = {
            "low": "info",
            "medium": "warning",
            "high": "error",
        }
        pd_severity = severity_map.get(drift.severity, "info")

        # Build PagerDuty event
        event = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": f"Behavioral drift detected: {drift.agent_id} v{drift.agent_version} - {drift.metric}",
                "severity": pd_severity,
                "source": "AgentTracer Phase 3",
                "custom_details": {
                    "agent_id": drift.agent_id,
                    "agent_version": drift.agent_version,
                    "environment": drift.environment,
                    "metric": drift.metric,
                    "baseline_value": drift.baseline_value,
                    "observed_value": drift.observed_value,
                    "delta_percent": drift.delta_percent,
                    "significance": drift.significance,
                    "baseline_id": str(drift.baseline_id),
                    "drift_id": str(drift.drift_id),
                },
            },
        }

        # Send to PagerDuty
        try:
            response = requests.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=event,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"PagerDuty alert sent for drift {drift.drift_id}")
        except Exception as e:
            logger.error(f"Failed to send PagerDuty alert: {e}")

    def _send_generic_webhook(self, message: str, drift: BehaviorDriftDB) -> None:
        """
        Send alert to generic webhook.

        Args:
            message: Formatted alert message
            drift: BehaviorDriftDB object
        """
        webhook_config = self.webhook_config.get("webhook", {})
        webhook_url = webhook_config.get("url")

        if not webhook_url:
            logger.debug("Generic webhook URL not configured, skipping")
            return

        # Build generic payload
        payload = {
            "event": "drift_detected",
            "drift_id": str(drift.drift_id),
            "baseline_id": str(drift.baseline_id),
            "agent_id": drift.agent_id,
            "agent_version": drift.agent_version,
            "environment": drift.environment,
            "drift_type": drift.drift_type,
            "metric": drift.metric,
            "baseline_value": drift.baseline_value,
            "observed_value": drift.observed_value,
            "delta": drift.delta,
            "delta_percent": drift.delta_percent,
            "significance": drift.significance,
            "test_method": drift.test_method,
            "severity": drift.severity,
            "detected_at": drift.detected_at.isoformat(),
            "observation_window_start": drift.observation_window_start.isoformat(),
            "observation_window_end": drift.observation_window_end.isoformat(),
            "observation_sample_size": drift.observation_sample_size,
            "message": message,
        }

        # Send to webhook
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            logger.info(f"Generic webhook alert sent for drift {drift.drift_id}")
        except Exception as e:
            logger.error(f"Failed to send generic webhook alert: {e}")

    def _load_webhook_config(self) -> dict:
        """
        Load webhook configuration from environment variables.

        Returns:
            Dict of webhook configuration
        """
        config = {
            "slack": {
                "enabled": os.getenv("PHASE3_SLACK_ENABLED", "false").lower() == "true",
                "webhook_url": os.getenv("PHASE3_SLACK_WEBHOOK_URL"),
                "channel": os.getenv("PHASE3_SLACK_CHANNEL", "#agent-alerts"),
            },
            "pagerduty": {
                "enabled": os.getenv("PHASE3_PAGERDUTY_ENABLED", "false").lower() == "true",
                "routing_key": os.getenv("PHASE3_PAGERDUTY_ROUTING_KEY"),
            },
            "webhook": {
                "enabled": os.getenv("PHASE3_WEBHOOK_ENABLED", "false").lower() == "true",
                "url": os.getenv("PHASE3_WEBHOOK_URL"),
            },
        }

        return config


# Convenience function

def emit_drift_alert(drift: BehaviorDriftDB) -> None:
    """
    Convenience function to emit an alert for a drift event.

    Args:
        drift: BehaviorDriftDB object representing detected drift
    """
    emitter = AlertEmitter()
    emitter.emit(drift)
