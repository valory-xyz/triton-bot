# Contributing to Triton

Thank you for your interest in contributing to Triton! This document provides guidelines and instructions for contributing to the project.

## Getting Started

For initial setup instructions, environment configuration, and how to run Triton locally, please refer to the [README.md](README.md#prepare-the-repo).

**Before starting development:**
1. Clone and set up the repository as described in the README
2. Ensure you have Python 3.10-3.11 installed
3. Have Poetry installed for dependency management
4. Configure the `.env` file with your Telegram bot token and Gnosis RPC endpoint

## Code Quality & Standards

We maintain high code quality through automated checks. Before submitting a pull request, ensure your code passes all checks:

### Code Formatting

We use **Black** for code formatting and **isort** for import sorting:

```bash
# Format code
make formatters

# Check formatting without changes
make code-check
```

### Linting & Static Analysis

We use multiple tools for code quality:

- **flake8**: Style guide enforcement
- **pylint**: Static code analysis
- **mypy**: Type checking
- **darglint**: Docstring linting

All checks are run automatically in CI/CD. Run locally with:

```bash
make code-check
```

### Python Version

- **Minimum:** 3.10
- **Maximum:** 3.11
- Always specify types in function signatures

## Testing

### Running Tests

```bash
poetry run pytest
```

### Writing Tests

- Place test files in the `tests/` directory
- Follow the naming convention: `test_*.py`
- Use pytest fixtures and mocking to isolate units
- Tests should be independent and deterministic
- Aim for high coverage of critical paths

## Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Keep commits focused and atomic
   - Write clear commit messages
   - Update relevant documentation

3. **Format and test your code:**
   ```bash
   make formatters
   make code-check
   poetry run pytest
   ```

4. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request:**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure all checks pass
   - Wait for review

## Key Components

### TritonService (`triton/service.py`)

Manages operations for a single service:
- Loading service configurations
- Querying blockchain data (balances, staking status)
- Executing transactions (claiming rewards, withdrawals)
- Interacting with staking contracts

### Chain Module (`triton/chain.py`)

Blockchain interactions:
- RPC calls to Gnosis chain
- Balance queries (native token, OLAS, wrapped OLAS)
- Staking status and rewards
- Slot availability
- Price data from CoinGecko

### Main Bot (`triton/triton.py`)

Telegram bot implementation:
- Command handlers (status, balance, claim, withdraw)
- Job scheduling (periodic balance checks, autoclaiming)
- Markdown formatting for Telegram messages
- Error handling and user notifications

### Tools & Utilities (`triton/tools.py`)

Helper functions:
- Telegram message formatting
- Number formatting
- Data validation

## Deployment

For deployment instructions as a systemd service, including how to start, stop, and manage the service, please refer to [README.md](README.md#run-triton-as-a-systemd-service).

## Documentation

- Keep code well-commented, especially complex logic
- Update README.md if adding user-facing features
- Write docstrings for all public functions and classes
- Include type hints in function signatures

## Reporting Issues

When reporting bugs, include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, relevant config)
- Relevant logs or error messages

## Questions?

- Check the README.md for common questions
- Review existing issues and pull requests
- Ask in pull request discussions

## License

By contributing to Triton, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to Triton! 🐚
