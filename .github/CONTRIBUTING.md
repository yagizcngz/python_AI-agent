# Contributing Guidelines

Thank you for your interest in contributing to Python AI Agent!

## Development Setup

1. **Fork and Clone:** Fork the repository on GitHub and clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/python_AI-agent.git
   cd python_AI-agent
   ```
2. **Environment & API Keys:** Follow the [README.md](../README.md#getting-started) for general environment setup and API key configuration (`.env` or `API_KEYS_OPEN_ROUTER.txt`).
3. **Install Development Dependencies:** Install the project in editable mode with development/test dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Making Changes

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your improvements or bug fixes.
3. **Run Tests:** Ensure all existing and new tests pass before submitting:
   ```bash
   pytest
   ```

## Submitting a Pull Request

1. Commit your changes with a clear, descriptive message:
   ```bash
   git commit -m "feat: describe your change"
   ```
2. Push the branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
3. Open a Pull Request against the `main` branch.
4. Your pull request will be reviewed, and feedback will be provided if any adjustments are needed. Once approved, it will be merged.

Thank you for contributing!
