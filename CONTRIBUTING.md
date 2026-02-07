# Contributing to DocuMind

Thank you for your interest in contributing to DocuMind! This document provides guidelines and instructions for contributing.

## 🚀 Getting Started

### Development Environment Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/DocuMind.git
   cd DocuMind
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r src/requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

5. **Set up environment variables**
   ```bash
   cp src/.env.example src/.env
   # Edit .env with your configuration
   ```

## 📝 Code Style

We use the following tools to maintain code quality:

- **Black** - Code formatting (line length: 88)
- **Flake8** - Linting
- **isort** - Import sorting
- **mypy** - Type checking

Run all checks before committing:
```bash
pre-commit run --all-files
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_services.py -v
```

### Writing Tests
- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_<function_name>_<scenario>`
- Use fixtures from `tests/conftest.py`

## 🔀 Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Add/update tests as needed
   - Update documentation if required

3. **Commit with meaningful messages**
   ```bash
   git commit -m "feat: add support for XYZ format"
   ```
   
   We follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` - New features
   - `fix:` - Bug fixes
   - `docs:` - Documentation changes
   - `test:` - Test additions/changes
   - `refactor:` - Code refactoring
   - `chore:` - Maintenance tasks

4. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

5. **PR Requirements**
   - All tests must pass
   - Code must be properly formatted
   - Include description of changes
   - Reference any related issues

## 🐛 Reporting Issues

When reporting bugs, please include:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

## 💡 Feature Requests

For feature requests, please:
- Check if it already exists as an issue
- Describe the use case
- Explain the expected behavior

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Questions? Feel free to open an issue or reach out to the maintainers!
