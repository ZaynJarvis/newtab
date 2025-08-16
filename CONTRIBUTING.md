# Contributing to New Tab

First off, thank you for considering contributing to New Tab! 🎉

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs 🐛

Before creating bug reports, please check the existing issues list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples to demonstrate the steps**
- **Describe the behavior you observed and what behavior you expected**
- **Include screenshots and animated GIFs if possible**
- **Include your environment details** (OS, browser, Python version)

### Suggesting Enhancements 💡

Enhancement suggestions are welcome! Please provide:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Provide specific examples to demonstrate the enhancement**
- **Describe the current behavior and explain which behavior you expected**
- **Explain why this enhancement would be useful**

### Pull Requests 🔄

- Fill in the required template
- Do not include issue numbers in the PR title
- Follow the Python and JavaScript style guides
- Include thoughtfully-worded, well-structured tests
- Document new code with clear comments
- End all files with a newline

## Development Setup

### Backend Development

```bash
# Clone the repository
git clone <repository-url>
cd newtab

# Setup Python environment
cd backend
uv sync

# Start development server
uv run python main.py
```

### Extension Development

```bash
# Load extension in Chrome
# 1. Open chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked" and select the extension/ folder
```

### Testing

```bash
# Run backend tests
cd backend
uv run python ../demo/quick-test.py

# Generate test data
uv run python ../demo/test-data-generator.py
```

## Style Guides

### Python Style Guide

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints where possible
- Write docstrings for all public functions
- Keep functions small and focused
- Use meaningful variable names

### JavaScript Style Guide

- Use ES6+ features
- Use `const` for constants, `let` for variables
- Use meaningful function and variable names
- Follow consistent indentation (2 spaces)
- Add JSDoc comments for complex functions

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

Example:
```
Add semantic search endpoint

- Implement vector similarity search
- Add embedding generation pipeline  
- Include relevance scoring algorithm

Resolves #123
```

## Project Architecture

### Backend Structure

```
backend/
├── main.py           # FastAPI application entry point
├── models.py         # Pydantic data models
├── database.py       # SQLite database operations
├── vector_store.py   # In-memory vector search
└── api_client.py     # External API integrations
```

### Extension Structure

```
extension/
├── manifest.json     # Extension configuration
├── background/       # Service worker scripts
├── content/         # Content extraction scripts
├── newtab/          # New tab override UI
└── popup/           # Extension popup interface
```

## Testing Philosophy

- Write tests for all new features
- Ensure backward compatibility
- Test both success and error cases  
- Include integration tests
- Performance test critical paths

## Questions?

Don't hesitate to reach out if you have questions:

- Create an issue for general questions
- Start a discussion for broader topics
- Check existing documentation first

Thanks for contributing! 🙏