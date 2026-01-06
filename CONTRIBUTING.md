# Contributing to AgentTracer

Thank you for your interest in contributing to AgentTracer! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Submitting Changes](#submitting-changes)
- [Issue Guidelines](#issue-guidelines)
- [License](#license)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- **Be respectful** and considerate in your communication
- **Be collaborative** and open to different perspectives
- **Focus on what is best** for the project and community
- **Show empathy** towards other community members

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title** describing the issue
- **Detailed description** of the problem
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, Docker version)
- **Relevant logs** or error messages

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear title** that describes the suggestion
- **Provide detailed description** of the proposed functionality
- **Explain why** this enhancement would be useful
- **Consider Phase 1 scope** - does this align with core observability?

### Pull Requests

We welcome pull requests! To ensure smooth integration:

1. **Fork the repository** and create your branch from `main`
2. **Follow coding standards** (see below)
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Ensure all tests pass** before submitting
6. **Write clear commit messages** following our conventions

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose
- Node.js 18+ (for UI development)
- Git

### Setting up the development environment

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/testing.git
cd testing

# 2. Set up Python environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv (recommended)
uv pip install -e ".[dev]"
# Or using pip: pip install -e ".[dev]"

# 3. Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# 4. Start services
docker compose up -d

# 5. Run tests
pytest tests/

# 6. For UI development
cd ui
npm install
npm run dev
```

## Coding Standards

### Python Code Style

We follow PEP 8 with the following specifics:

- **Line length**: 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Organized (stdlib, third-party, local)
- **Type hints**: Required for all public functions
- **Docstrings**: Required for modules, classes, and public functions

**Example:**

```python
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class AgentRunResponse(BaseModel):
    """
    Response model for agent runs.
    
    Args:
        run_id: Unique identifier for the run
        agent_id: Identifier for the agent
        status: Run status (success, failure, partial)
    """
    run_id: UUID
    agent_id: str
    status: str
    
    def get_summary(self) -> dict:
        """
        Get a summary of the run.
        
        Returns:
            Dictionary containing run summary
        """
        return {"run_id": str(self.run_id), "status": self.status}
```

### TypeScript Code Style

For UI contributions:

- **Use TypeScript** for all new files
- **Follow Prettier** formatting (run `npm run format`)
- **Use functional components** with hooks
- **Type all props and state**

**Example:**

```typescript
interface RunCardProps {
  runId: string;
  status: 'success' | 'failure' | 'partial';
  onSelect: (id: string) => void;
}

export const RunCard: React.FC<RunCardProps> = ({ runId, status, onSelect }) => {
  return (
    <div onClick={() => onSelect(runId)}>
      <span>{runId}</span>
      <span>{status}</span>
    </div>
  );
};
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**

```
feat(sdk): add retry metadata capture

Add support for capturing retry attempt numbers in step metadata.
This allows UI to display retry patterns in the timeline.

Closes #123
```

```
fix(api): correct step sequence validation

Fixed validation logic that was rejecting valid step sequences
starting from seq=0.

Fixes #456
```

### Privacy and Security Guidelines

**Critical: Never commit sensitive data**

- ❌ **Never store** prompts, responses, or PII
- ❌ **Never commit** `.env` files or credentials
- ✅ **Always validate** metadata for privacy violations
- ✅ **Always use** field validators for sensitive data

**When adding new features:**

1. **Ask**: Could this capture sensitive data?
2. **Validate**: Add privacy checks at SDK and API levels
3. **Test**: Include privacy violation tests
4. **Document**: Update privacy documentation

## Submitting Changes

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass (`pytest tests/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if applicable)
- [ ] Commit messages follow conventions
- [ ] Privacy requirements met (if applicable)

### Pull Request Process

1. **Update your fork** with the latest from `main`
2. **Create a feature branch** (`git checkout -b feat/my-feature`)
3. **Make your changes** with clear commits
4. **Push to your fork** (`git push origin feat/my-feature`)
5. **Create Pull Request** from your fork to main repository
6. **Address review feedback** if requested

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Privacy Impact
- [ ] No sensitive data captured
- [ ] Privacy validation added
- [ ] N/A (no data capture)

## Documentation
- [ ] README updated
- [ ] API docs updated
- [ ] Code comments added
- [ ] N/A
```

## Issue Guidelines

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
Clear description of what the bug is.

**To Reproduce**
1. Start services with '...'
2. Run agent with '...'
3. Query API '...'
4. See error

**Expected behavior**
What should happen

**Actual behavior**
What actually happens

**Environment**
- OS: [e.g., macOS 13.0]
- Python: [e.g., 3.10.5]
- Docker: [e.g., 24.0.0]

**Additional context**
Logs, screenshots, etc.
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Clear description of the problem.

**Describe the solution you'd like**
Clear description of what you want to happen.

**Describe alternatives you've considered**
Other approaches you've thought about.

**Phase 1 Scope**
- [ ] Aligns with execution visibility
- [ ] Does not require prompt storage
- [ ] Privacy-safe by design

**Additional context**
Any other context, mockups, etc.
```

## Testing Requirements

### Unit Tests

All new features must include unit tests:

```python
# tests/test_sdk.py
def test_step_context_timing():
    """Test that step context captures timing correctly."""
    tracer = AgentTracer(agent_id="test", agent_version="1.0.0")
    
    with tracer.start_run() as run:
        with run.step("plan", "test_step"):
            time.sleep(0.1)
    
    assert len(run._steps) == 1
    assert run._steps[0].latency_ms >= 100
```

### Integration Tests

For API or SDK changes:

```python
# tests/test_integration.py
def test_full_run_ingestion(db_session):
    """Test complete flow from SDK to database."""
    tracer = AgentTracer(
        agent_id="test_agent",
        agent_version="1.0.0",
        api_url="http://localhost:8000"
    )
    
    with tracer.start_run() as run:
        with run.step("plan", "analyze"):
            pass
    
    # Verify in database
    runs = db_session.query(AgentRunDB).filter_by(agent_id="test_agent").all()
    assert len(runs) == 1
```

### Privacy Tests

Always include privacy validation tests:

```python
def test_privacy_violation_rejected():
    """Test that sensitive metadata is rejected."""
    run = AgentRunCreate(
        run_id=uuid4(),
        agent_id="test",
        agent_version="1.0.0",
        status="success",
        started_at=datetime.now(),
        steps=[
            AgentStepCreate(
                seq=0,
                step_type="plan",
                name="test",
                latency_ms=100,
                started_at=datetime.now(),
                ended_at=datetime.now(),
                metadata={"prompt": "secret"}  # Should fail
            )
        ]
    )
    
    with pytest.raises(ValueError, match="may contain sensitive data"):
        # Trigger validation
        pass
```

## Areas for Contribution

We particularly welcome contributions in:

- **SDK improvements**: Additional language support, better error handling
- **API enhancements**: Performance optimizations, query improvements
- **UI features**: Better visualizations, advanced filtering
- **Documentation**: Examples, tutorials, architecture explanations
- **Testing**: More test coverage, performance tests
- **DevOps**: Deployment improvements, monitoring integration

## What We're NOT Looking For

Please do not submit contributions for:

- Prompt storage or versioning
- LLM response capture
- Agent self-modification
- Automated optimization
- Evaluation frameworks

These are explicitly out of scope for Phase 1.

## Getting Help

If you need help:

- **Documentation**: Check [docs/](./docs/) first
- **Issues**: Search existing issues
- **Discussions**: Start a discussion for questions
- **Examples**: Review [examples/](./examples/)

## Recognition

Contributors will be recognized in:

- Project README
- Release notes
- Git commit history

## License

By contributing to AgentTracer, you agree that your contributions will be licensed under the Apache License 2.0. See [LICENSE](./LICENSE) for details.

---

Thank you for contributing to AgentTracer! Your efforts help make AgentTracer better for everyone.
