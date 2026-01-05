"""
E2E Test Fixtures for Gate E.

P6.5: Provides HTTP client fixture and pass-aware LLM stubs
for deterministic API + SSE testing.

Uses uvicorn server in background thread for SSE streaming support.
"""

import threading
import time
import pytest
import httpx
import uvicorn

from main import app
from domain.state import (
    WorkflowState,
    StepName,
    PassType,
    ValidationResult,
)
from application.event_stream import reset_event_broker
from routes.workflows import reset_graph
import infrastructure.postgres as postgres_module


# =============================================================================
# Server Thread for Real HTTP Testing
# =============================================================================


class ServerThread(threading.Thread):
    """Background thread running uvicorn server."""

    def __init__(self, app, host: str, port: int):
        super().__init__(daemon=True)
        self.app = app
        self.host = host
        self.port = port
        self.server = None

    def run(self):
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="error",
        )
        self.server = uvicorn.Server(config)
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


# =============================================================================
# Pass-Aware LLM Stubs
# =============================================================================


@pytest.fixture
def stub_llm_nodes(monkeypatch):
    """Pass-aware stub: methodology for Pass 1, packages for Pass 2.

    Monkeypatches generate_step_output and validate_output for deterministic testing.
    """

    async def fake_generate_step_output(state: WorkflowState) -> dict:
        """Return deterministic output based on step and pass type."""
        step = state.current_step
        pass_type = state.current_pass

        if pass_type == PassType.DEFINITION:
            # Pass 1: Return full methodology structure (4 doc types × 3 versions)
            step_value = step.value if hasattr(step, "value") else str(step)
            return {
                "v1": {
                    "data_sheet": f"# Data Sheet V1\n\nStep: {step_value}\n\nCore data and definitions.",
                    "todo_list": f"# To-Do List V1\n\nStep: {step_value}\n\n- [ ] Task 1\n- [ ] Task 2",
                    "guidance": f"# Guidance V1\n\nStep: {step_value}\n\nGuidance content.",
                    "detailed_procedure": f"# Procedure V1\n\nStep: {step_value}\n\n1. Step one\n2. Step two",
                },
                "v2": {
                    "data_sheet": f"# Data Sheet V2\n\nStep: {step_value}\n\nRefined data.",
                    "todo_list": f"# To-Do List V2\n\nStep: {step_value}\n\n- [ ] Refined task 1",
                    "guidance": f"# Guidance V2\n\nStep: {step_value}\n\nRefined guidance.",
                    "detailed_procedure": f"# Procedure V2\n\nStep: {step_value}\n\n1. Refined step one",
                },
                "v3": {
                    "data_sheet": f"# Data Sheet V3\n\nStep: {step_value}\n\nFinal data.",
                    "todo_list": f"# To-Do List V3\n\nStep: {step_value}\n\n- [ ] Final task 1",
                    "guidance": f"# Guidance V3\n\nStep: {step_value}\n\nFinal guidance.",
                    "detailed_procedure": f"# Procedure V3\n\nStep: {step_value}\n\n1. Final step one",
                },
            }
        else:
            # Pass 2: Return step package structure
            step_value = step.value if hasattr(step, "value") else str(step)

            if step_value == "problem_definition":
                return {
                    "title": "Test Problem",
                    "canonical_problem_definition": {
                        "statement": "Test problem statement for Gate E verification"
                    },
                    "stakeholders": [
                        {
                            "id": "SH-001",
                            "name_or_group": "Test User",
                            "role": "Tester",
                            "needs": ["Verify API flow"],
                            "concerns": ["Test reliability"],
                            "impact": "High",
                        }
                    ],
                    "constraints": {
                        "hard": [
                            {
                                "id": "HC-001",
                                "statement": "Must pass tests",
                                "rationale": "CI requirement",
                            }
                        ],
                        "soft": [],
                    },
                    "scope": {
                        "in": [{"id": "IN-001", "item": "Gate E testing"}],
                        "out": [
                            {
                                "id": "OUT-001",
                                "item": "Gate C/D testing",
                                "rationale": "Different slices",
                            }
                        ],
                    },
                    "success_criteria": [
                        {
                            "id": "CRT-001",
                            "metric_or_signal": "Tests pass",
                            "target": "100%",
                            "how_verified": "pytest",
                        }
                    ],
                }
            elif step_value == "requirements":
                return {
                    "overview": {
                        "summary": "Test requirements for Gate E",
                        "boundaries": ["Gate E scope"],
                        "total_requirements": 1,
                        "priority_distribution": {"must": 1, "should": 0, "could": 0},
                    },
                    "requirements": [
                        {
                            "id": "FR-001",
                            "category": "FR",
                            "priority": "must",
                            "statement": "API must work",
                            "rationale": "Core Gate E requirement",
                            "source": {"type": "stakeholder", "id": "SH-001", "aspect": "need"},
                            "component": ["api"],
                            "testability": {"method": "test", "description": "E2E test"},
                            "trace": {"stakeholders": ["SH-001"]},
                        }
                    ],
                    "coverage_map": [
                        {
                            "source_type": "stakeholder",
                            "source_id": "SH-001",
                            "requirement_ids": ["FR-001"],
                            "coverage_note": "Fully covered",
                        }
                    ],
                }
            else:
                # Step 3 (objectives) or beyond
                return {
                    "overview": {
                        "intent": "Test objectives for Gate E",
                        "measurement_principles": ["Deterministic"],
                        "boundaries": ["Gate E"],
                        "total_objectives": 1,
                        "consolidation_ratio": 1.0,
                    },
                    "objectives": [
                        {
                            "id": "CAP-001",
                            "category": "CAP",
                            "tier": "primary",
                            "statement": "Gate E enforced",
                            "rationale": "Core requirement",
                            "owner_type": "system",
                            "linked_requirements": ["FR-001"],
                            "consolidated": False,
                            "success_criteria": {
                                "definition": "API works",
                                "verification": {
                                    "method": "test",
                                    "description": "pytest",
                                    "evidence_artifacts": ["test_gate_e.py"],
                                },
                            },
                            "component": ["api"],
                            "acceptance_criteria": ["CRT-001"],
                        }
                    ],
                    "success_framework": {
                        "minimum_viable": {
                            "description": "Gate E works",
                            "objectives": ["CAP-001"],
                            "requirement_coverage": ["FR-001"],
                        },
                        "target": {
                            "description": "All tests pass",
                            "objectives": ["CAP-001"],
                            "requirement_coverage": ["FR-001"],
                        },
                        "aspirational": {
                            "description": "Full coverage",
                            "objectives": ["CAP-001"],
                            "requirement_coverage": ["FR-001"],
                        },
                    },
                    "trace_map": [
                        {
                            "objective_id": "CAP-001",
                            "requirement_ids": ["FR-001"],
                            "consolidated": False,
                        }
                    ],
                }

    async def fake_validate_output(
        step: StepName,
        output: dict,
        pass_type: PassType = None,
    ) -> ValidationResult:
        """Return passing validation without LLM."""
        return ValidationResult(passed=True, errors=[], warnings=[])

    # Patch the module-level functions
    monkeypatch.setattr(
        "orchestration.nodes.generate_step_output", fake_generate_step_output
    )
    monkeypatch.setattr("orchestration.nodes.validate_output", fake_validate_output)


# =============================================================================
# HTTP Client Fixture with Real Server
# =============================================================================


def find_free_port() -> int:
    """Find a free port on localhost."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


# Session-scoped server to avoid event loop issues between tests
_server_port = None
_server_thread = None


@pytest.fixture(scope="session")
def server():
    """Session-scoped server that persists across all tests.

    Avoids event loop conflicts by keeping one server for entire test session.
    """
    global _server_port, _server_thread

    port = find_free_port()
    _server_port = port

    _server_thread = ServerThread(app, "127.0.0.1", port)
    _server_thread.start()
    time.sleep(0.5)  # Wait for server startup

    yield port

    # Cleanup at end of session
    _server_thread.stop()
    time.sleep(0.1)


@pytest.fixture
def client(stub_llm_nodes, server):
    """HTTP client connected to session-scoped server.

    Uses session-scoped server for SSE streaming (TestClient has SSE issues).
    Depends on stub_llm_nodes for deterministic behavior.
    """
    # Reset event broker between tests for clean state
    reset_event_broker()
    reset_graph()

    # Create httpx client pointing to session-scoped server
    with httpx.Client(base_url=f"http://127.0.0.1:{server}", timeout=10.0) as client:
        yield client
