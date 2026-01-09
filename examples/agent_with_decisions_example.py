"""
Phase 2 Example: Agent with Decision and Quality Signal Tracking

This example demonstrates the Phase 2 features:
- Recording structured decision points
- Recording observable quality signals
- Combining Phase 1 execution tracking with Phase 2 decision/quality tracking

Privacy guarantee: No prompts, responses, or reasoning text stored.
Only structured enums and numeric values.
"""

import random
import time

from sdk.agenttrace import AgentTracer


def simulate_customer_support_agent():
    """
    Simulates a customer support agent that:
    1. Analyzes the query
    2. Decides between using cache vs. calling API
    3. Retrieves information
    4. Records quality signals about the retrieval
    5. Generates a response
    """

    tracer = AgentTracer(
        agent_id="customer_support_agent",
        agent_version="2.0.0",  # Phase 2 version
        api_url="http://localhost:8000",
        environment="production",
    )

    print("🚀 Starting customer support agent run (with Phase 2 tracking)...\n")

    with tracer.start_run() as run:
        # Step 1: Analyze query
        print("📊 Step 1: Analyzing customer query...")
        with run.step("plan", "analyze_query") as step:
            time.sleep(0.05)  # Simulate analysis

            # Simulated analysis result
            query_type = "order_status"
            cache_age_minutes = random.randint(1, 15)

            print(f"   - Query type: {query_type}")
            print(f"   - Cache age: {cache_age_minutes} minutes")
            step.add_metadata({"query_type": query_type, "cache_age_minutes": cache_age_minutes})

        # Step 2: Decide on data source
        print("\n🤔 Step 2: Deciding on data source...")
        with run.step("plan", "choose_data_source") as step:
            time.sleep(0.03)

            # Decision logic: use cache if < 5 minutes old
            if cache_age_minutes < 5:
                selected_source = "cache"
                reason = "cached_data_sufficient"
                confidence = 0.95
            else:
                selected_source = "api"
                reason = "fresh_data_required"
                confidence = 0.85

            print(f"   ✓ Decision: {selected_source} ({reason}, confidence={confidence})")

            # Phase 2: Record decision
            run.record_decision(
                decision_type="tool_selection",
                selected=selected_source,
                reason_code=reason,
                candidates=["cache", "api", "database"],
                confidence=confidence,
                step_id=step.step_id,
                metadata={"cache_age_minutes": cache_age_minutes},
            )

        # Step 3: Retrieve data
        print(f"\n📥 Step 3: Retrieving data from {selected_source}...")
        with run.step(
            "retrieve" if selected_source == "cache" else "tool", "fetch_order_data"
        ) as step:
            time.sleep(0.1)

            # Simulate retrieval
            retrieval_success = random.random() > 0.1  # 90% success rate
            num_results = random.randint(1, 5) if retrieval_success else 0

            if retrieval_success:
                print(f"   ✓ Retrieved {num_results} orders successfully")
            else:
                print("   ✗ No results found")

            step.add_metadata(
                {
                    "source": selected_source,
                    "result_count": num_results,
                    "success": retrieval_success,
                }
            )

            # Phase 2: Record quality signal for retrieval
            if num_results == 0:
                run.record_quality_signal(
                    signal_type="empty_retrieval",
                    signal_code="no_results",
                    value=True,
                    step_id=step.step_id,
                    metadata={"query_type": query_type},
                )
                print("   ⚠️  Quality signal: empty_retrieval")
            else:
                run.record_quality_signal(
                    signal_type="tool_success",
                    signal_code="first_attempt",
                    value=True,
                    step_id=step.step_id,
                    metadata={"result_count": num_results},
                )
                print("   ✓ Quality signal: tool_success")

        # Step 4: Validate response schema
        print("\n✅ Step 4: Validating response schema...")
        with run.step("other", "validate_schema") as step:
            time.sleep(0.02)

            # Simulate schema validation
            schema_valid = num_results > 0 and random.random() > 0.05  # 95% valid if data exists

            if schema_valid:
                schema_result = "full_match"
                print("   ✓ Schema validation: PASSED")
            else:
                schema_result = "validation_failed"
                print("   ✗ Schema validation: FAILED")

            # Phase 2: Record quality signal for schema validation
            run.record_quality_signal(
                signal_type="schema_valid",
                signal_code=schema_result,
                value=schema_valid,
                weight=0.9,  # High importance for schema validation
                step_id=step.step_id,
            )

        # Step 5: Decide on response mode
        print("\n💬 Step 5: Deciding on response format...")
        with run.step("plan", "choose_response_mode") as step:
            time.sleep(0.02)

            # Decision logic: streaming for large results
            if num_results > 3:
                response_mode = "streaming"
                mode_reason = "batch_preferred"  # Actually we want streaming for large
                confidence = 0.75
            else:
                response_mode = "batch"
                mode_reason = "batch_preferred"
                confidence = 0.90

            print(f"   ✓ Decision: {response_mode} mode ({mode_reason})")

            # Phase 2: Record response mode decision
            run.record_decision(
                decision_type="response_mode",
                selected=response_mode,
                reason_code=mode_reason,
                candidates=["streaming", "batch"],
                confidence=confidence,
                step_id=step.step_id,
                metadata={"result_count": num_results},
            )

        # Step 6: Generate response
        print(f"\n📤 Step 6: Generating {response_mode} response...")
        with run.step("respond", "generate_response") as step:
            time.sleep(0.15)

            latency_ms = random.randint(100, 200)
            threshold_exceeded = latency_ms > 150

            print(f"   - Response generated in {latency_ms}ms")
            step.add_metadata({"response_mode": response_mode, "latency_ms": latency_ms})

            # Phase 2: Record latency signal
            if threshold_exceeded:
                run.record_quality_signal(
                    signal_type="latency_threshold",
                    signal_code="exceeded_threshold",
                    value=True,
                    step_id=step.step_id,
                    metadata={"latency_ms": latency_ms, "threshold_ms": 150},
                )
                print("   ⚠️  Quality signal: latency_threshold exceeded")
            else:
                run.record_quality_signal(
                    signal_type="latency_threshold",
                    signal_code="under_threshold",
                    value=True,
                    step_id=step.step_id,
                    metadata={"latency_ms": latency_ms},
                )

    print("\n✅ Agent run completed successfully!")
    print("📊 Phase 2 data recorded:")
    print("   - Decisions: tool_selection, response_mode")
    print("   - Quality signals: retrieval, schema_valid, latency_threshold")


def simulate_agent_with_retry_decision():
    """
    Demonstrates retry strategy decisions in Phase 2.
    """

    tracer = AgentTracer(
        agent_id="api_caller_agent",
        agent_version="2.0.0",
        api_url="http://localhost:8000",
        environment="production",
    )

    print("\n🔄 Retry Decision Example\n")

    with tracer.start_run() as run:
        # Simulate an API call that might fail
        for attempt in range(3):
            print(f"\n🔧 Attempt {attempt + 1}/3...")

            with run.step("tool", "call_external_api") as step:
                time.sleep(0.1)

                # Simulate API call
                success = random.random() > 0.6  # 40% success rate

                if success:
                    print("   ✓ API call succeeded")
                    step.add_metadata({"attempt": attempt + 1, "success": True})

                    # Record quality signal
                    signal_code = "first_attempt" if attempt == 0 else "after_retry"
                    run.record_quality_signal(
                        signal_type="tool_success",
                        signal_code=signal_code,
                        value=True,
                        step_id=step.step_id,
                        metadata={"attempt_number": attempt + 1},
                    )

                    if attempt > 0:
                        run.record_quality_signal(
                            signal_type="retry_occurred",
                            signal_code="single_retry" if attempt == 1 else "multiple_retries",
                            value=True,
                            step_id=step.step_id,
                        )

                    break
                else:
                    print("   ✗ API call failed (rate limited)")
                    step.add_metadata({"attempt": attempt + 1, "success": False})

                    # Record failure signal
                    run.record_quality_signal(
                        signal_type="tool_failure",
                        signal_code="rate_limited",
                        value=True,
                        step_id=step.step_id,
                    )

                    if attempt < 2:  # Not last attempt
                        # Record retry decision
                        print("   ⏳ Deciding to retry...")
                        with run.step("plan", "decide_retry") as decision_step:
                            time.sleep(0.01)

                            run.record_decision(
                                decision_type="retry_strategy",
                                selected="retry",
                                reason_code="rate_limit_encountered",
                                confidence=0.8,
                                step_id=decision_step.step_id,
                                metadata={"backoff_seconds": 2**attempt},
                            )

                        time.sleep(2**attempt)  # Exponential backoff
                    else:
                        # No retry - terminal error
                        print("   🛑 Max retries reached, giving up")
                        run.record_decision(
                            decision_type="retry_strategy",
                            selected="no_retry",
                            reason_code="retry_budget_exhausted",
                            confidence=1.0,
                            step_id=step.step_id,
                        )

                        run.record_failure(
                            failure_type="tool",
                            failure_code="max_retries_exceeded",
                            message="API call failed after 3 attempts (rate limited)",
                        )

    print("\n✅ Retry example completed!")


if __name__ == "__main__":
    print("=" * 70)
    print("Phase 2 Example: Decision & Quality Signal Tracking")
    print("=" * 70)

    # Example 1: Customer support agent with decisions and signals
    simulate_customer_support_agent()

    print("\n" + "=" * 70 + "\n")

    # Example 2: Retry strategy decisions
    simulate_agent_with_retry_decision()

    print("\n" + "=" * 70)
    print("✅ All Phase 2 examples completed!")
    print("=" * 70)
