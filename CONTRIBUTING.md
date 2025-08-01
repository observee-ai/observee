# Contributing to Observee SDK

Thank you for your interest in contributing to the Observee SDK! This document provides guidelines and instructions for contributing to our multi-language SDK ecosystem.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Development Setup](#development-setup)
- [Making Contributions](#making-contributions)
- [Testing](#testing)
- [Documentation](#documentation)
- [Release Process](#release-process)
- [Community](#community)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. All contributors are expected to:

- Be respectful and constructive in all interactions
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

The Observee SDK consists of three main components across TypeScript and Python:

1. **Agents** - MCP tool integration with LLM providers
2. **Auth** - OAuth authentication for 15+ services  
3. **Logger** - Structured logging and monitoring

Each component has both TypeScript and Python implementations.

## Project Structure

```
observee/
   agents/           # MCP agent integration
      python/      # Python implementation
      ts/          # TypeScript implementation
   auth/            # OAuth authentication
      python/      # Python implementation
      ts/          # TypeScript implementation
   logger/          # Logging and monitoring
      python/      # Python implementation
      ts/          # TypeScript implementation
   docs/            # Documentation
   examples/        # Example code
   index.js         # Main SDK entry point
```

## Development Setup

### Prerequisites

- Node.js 16+ and npm/yarn
- Python 3.7+
- Git

### Initial Setup

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/your-username/observee.git
   cd observee
   ```

2. Install root dependencies:
   ```bash
   npm install
   ```

### TypeScript Development

For TypeScript packages (agents/ts, auth/ts, logger/ts):

```bash
cd agents/ts  # or auth/ts, logger/ts
npm install
npm run build
npm test
```

### Python Development

For Python packages (agents/python, auth/python, logger/python):

```bash
cd agents/python  # or auth/python, logger/python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
pytest
```

### Environment Setup

Create a `.env` file in the root directory:

```bash
OBSERVEE_API_KEY=your-development-api-key
ANTHROPIC_API_KEY=your-anthropic-key  # For agents testing
OPENAI_API_KEY=your-openai-key        # For agents testing
```

## Making Contributions

### Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following our coding standards

3. Write/update tests

4. Update documentation

5. Commit with conventional commits:
   ```bash
   git commit -m "feat(agents): add support for new tool"
   ```

6. Push and create a pull request

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `perf:` Performance improvements
- `test:` Test changes
- `chore:` Maintenance tasks

Include the component in parentheses:
- `feat(agents):` for agent-related changes
- `fix(auth):` for auth-related changes
- `docs(logger):` for logger documentation

### Code Style

#### TypeScript
- ESLint configuration is provided
- Use Prettier for formatting
- Run `npm run lint` before committing

#### Python
- Follow PEP 8
- Use Black for formatting
- Use mypy for type checking
- Run `black .` and `flake8` before committing

### Pull Request Guidelines

1. **Title**: Use conventional commit format
2. **Description**: Include:
   - What changes were made
   - Why they were necessary
   - Any breaking changes
   - Related issues

3. **Checklist**:
   - [ ] Tests pass
   - [ ] Documentation updated
   - [ ] Lint checks pass
   - [ ] No breaking changes (or documented)

## Testing

### Running Tests

#### All Tests
```bash
# From root directory
npm test  # Runs all TypeScript tests
```

#### Component-Specific Tests

TypeScript:
```bash
cd agents/ts
npm test
```

Python:
```bash
cd agents/python
pytest
```

### Writing Tests

- Write unit tests for all new functionality
- Mock external services (API calls, etc.)
- Aim for >80% code coverage
- Test edge cases and error conditions

### Integration Tests

For features that span multiple components:
```bash
cd examples/
# Run integration test examples
```

## Documentation

### Code Documentation

- TypeScript: Use JSDoc comments
- Python: Use docstrings (Google style)
- Include examples in documentation

### User Documentation

Documentation is in the `docs/` directory using MDX format:

1. Update relevant `.mdx` files
2. Add code examples
3. Update navigation if adding new pages

### API Documentation

- Keep API references up to date
- Document all public methods
- Include parameter types and return values

## Component-Specific Guidelines

### Agents

When contributing to agents:
- Test with multiple LLM providers
- Ensure MCP tool compatibility
- Update provider-specific documentation

### Auth

When contributing to auth:
- Follow OAuth 2.0 best practices
- Never commit credentials
- Test redirect flows thoroughly

### Logger

When contributing to logger:
- Maintain backward compatibility
- Test performance impact
- Consider log volume implications

## Adding New Features

### New LLM Provider (Agents)

1. Create provider implementation in `providers/`
2. Add tests for the provider
3. Update documentation
4. Add example usage

### New Auth Service

1. Add service configuration
2. Implement OAuth flow
3. Test with real service (staging)
4. Document service-specific parameters

### New Logger Feature

1. Ensure it doesn't break existing logs
2. Add configuration options
3. Document performance impact
4. Add usage examples

## Release Process

### Version Bumping

We use semantic versioning (MAJOR.MINOR.PATCH):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Steps

1. Update version in `package.json` or `pyproject.toml`
2. Update CHANGELOG.md
3. Create release PR
4. After merge, tag release:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

### Publishing

- TypeScript packages are published to npm
- Python packages are published to PyPI
- Releases are automated via GitHub Actions

## Debugging Tips

### Common Issues

1. **API Key Issues**: Ensure `.env` is properly configured
2. **Type Errors**: Run type checking before committing
3. **Import Errors**: Check package dependencies

### Development Tools

- Use VS Code with recommended extensions
- Enable format on save
- Use debugger configurations provided

## Security

- Never commit API keys or secrets
- Report security issues privately
- Follow OWASP guidelines
- Validate all inputs

## Performance

- Profile code for performance issues
- Consider memory usage
- Optimize for common use cases
- Document performance characteristics

## Community

### Getting Help

- Open an issue for bugs
- Use discussions for questions
- Join our Discord server
- Email: support@observee.ai

### Good First Issues

Look for issues labeled `good first issue` to get started.

### Code Reviews

- Be constructive and kind
- Focus on the code, not the person
- Suggest improvements
- Approve when ready

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Observee SDK! Your efforts help make AI development more accessible and powerful for everyone.