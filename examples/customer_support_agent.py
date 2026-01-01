"""
Example Agent: Customer Support Agent with Observability

This example demonstrates how to integrate the Agent Observability SDK
into a production agent application.

The agent:
1. Analyzes customer queries
2. Retrieves relevant knowledge base articles
3. Calls external APIs for additional data
4. Generates responses

All steps are captured with full observability, following Phase-1 constraints.
"""

import random
import time
from typing import Dict, List

from sdk.agenttrace import AgentTracer


class CustomerSupportAgent:
    """
    A customer support agent with built-in observability.

    This agent demonstrates Phase-1 telemetry integration:
    - All steps are tracked with timing
    - Retries are captured as separate spans
    - Failures are semantically classified
    - No prompts or responses are stored (privacy-by-default)
    """

    def __init__(self, agent_id: str = "customer_support_agent", agent_version: str = "1.0.0"):
        self.agent_id = agent_id
        self.agent_version = agent_version

        # Initialize tracer
        self.tracer = AgentTracer(
            agent_id=self.agent_id,
            agent_version=self.agent_version,
            api_url="http://localhost:8000",
            environment="production",
        )

    def handle_query(self, query: str) -> str:
        """
        Handle a customer support query with full observability.

        Args:
            query: Customer query text

        Returns:
            str: Generated response
        """
        # Start a new agent run
        with self.tracer.start_run() as run:
            # Step 1: Analyze query
            with run.step("plan", "analyze_query") as step:
                query_analysis = self._analyze_query(query)
                step.add_metadata(
                    {
                        "query_type": query_analysis["type"],
                        "priority": query_analysis["priority"],
                    }
                )

            # Step 2: Retrieve knowledge base articles
            with run.step("retrieve", "search_knowledge_base") as step:
                kb_results = self._search_knowledge_base(query_analysis)
                step.add_metadata({"result_count": len(kb_results), "search_method": "semantic"})

            # Step 3: Call external API with retry logic
            # Each retry is a separate step span (Phase-1 requirement)
            api_data = None
            max_retries = 3

            for attempt in range(max_retries):
                with run.step("tool", "call_external_api") as step:
                    step.add_metadata({"attempt": attempt + 1, "api": "customer_data_api"})

                    try:
                        api_data = self._call_external_api(query_analysis)
                        step.add_metadata({"http_status": 200})
                        break  # Success!

                    except Exception as e:
                        step.add_metadata({"http_status": 500, "error_type": type(e).__name__})

                        if attempt == max_retries - 1:
                            # Final attempt failed - record failure
                            run.record_failure(
                                failure_type="tool",
                                failure_code="timeout",
                                message=f"External API failed after {max_retries} attempts",
                                step_id=step.step_id,
                            )
                            return "I apologize, but I'm experiencing technical difficulties. Please try again later."

                        time.sleep(0.5 * (attempt + 1))  # Exponential backoff

            # Step 4: Generate response
            with run.step("respond", "generate_response") as step:
                response = self._generate_response(query_analysis, kb_results, api_data)
                step.add_metadata(
                    {
                        "response_length": len(response),
                        "sources_used": len(kb_results),
                    }
                )

            return response

    def _analyze_query(self, query: str) -> Dict:
        """
        Analyze the customer query.

        Simulates query analysis (in production, this might use NLP).
        """
        time.sleep(0.05)  # Simulate processing time

        # Simple keyword-based analysis (for demo purposes)
        query_lower = query.lower()

        if "refund" in query_lower or "cancel" in query_lower:
            return {"type": "billing", "priority": "high"}
        elif "password" in query_lower or "login" in query_lower:
            return {"type": "account", "priority": "medium"}
        else:
            return {"type": "general", "priority": "low"}

    def _search_knowledge_base(self, query_analysis: Dict) -> List[Dict]:
        """
        Search knowledge base for relevant articles.

        Simulates vector search (in production, this might use a vector DB).
        """
        time.sleep(0.1)  # Simulate search time

        # Simulate retrieving articles
        articles = [
            {"title": "How to process refunds", "relevance": 0.95},
            {"title": "Refund policy", "relevance": 0.87},
            {"title": "Common billing questions", "relevance": 0.72},
        ]

        return articles[:random.randint(2, 3)]

    def _call_external_api(self, query_analysis: Dict) -> Dict:
        """
        Call external API for customer data.

        Simulates API call with random failures.
        """
        time.sleep(0.2)  # Simulate network latency

        # Simulate 30% failure rate
        if random.random() < 0.3:
            raise Exception("API timeout")

        return {
            "customer_tier": "premium",
            "account_age_days": 365,
            "previous_tickets": 2,
        }

    def _generate_response(
        self, query_analysis: Dict, kb_results: List[Dict], api_data: Dict
    ) -> str:
        """
        Generate customer response.

        NOTE: We do NOT store the actual response content (Phase-1 privacy).
        Only metadata like response_length is captured.
        """
        time.sleep(0.15)  # Simulate generation time

        # In production, this would use an LLM
        response = f"Thank you for contacting support. Based on {len(kb_results)} relevant articles and your account information, here's how we can help..."

        return response

    def close(self):
        """Clean up tracer resources"""
        self.tracer.close()


# ============================================================================
# Example Usage
# ============================================================================


def main():
    """
    Run example customer support agent queries.

    This demonstrates real-world usage of the observability SDK.
    """
    agent = CustomerSupportAgent()

    # Example queries
    queries = [
        "I want a refund for my recent purchase",
        "I forgot my password and can't log in",
        "What are your business hours?",
    ]

    print("=" * 60)
    print("Customer Support Agent with Observability")
    print("=" * 60)
    print()

    for i, query in enumerate(queries, 1):
        print(f"Query {i}: {query}")
        print("-" * 60)

        response = agent.handle_query(query)
        print(f"Response: {response}")
        print()

    print("=" * 60)
    print("All queries processed! Check the observability platform for:")
    print("  - Run timelines")
    print("  - Step latencies")
    print("  - Retry attempts")
    print("  - Failure classifications")
    print()
    print("Query API: http://localhost:8001/v1/runs")
    print("=" * 60)

    agent.close()


if __name__ == "__main__":
    main()
