# Contributing to LocalNeural

We love your input! We want to make contributing to this project as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Development Process

We use GitHub to host code, to track issues and feature requests, as well as accept pull requests.

### 1. Fork the repo and create your branch

```bash
git clone https://github.com/rkriad585/LocalNeural.git
cd LocalNeural
git checkout -b feature/amazing-feature
```

### 2. Set up development environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your `SECRET_KEY` at minimum.

### 3. Make your changes

- Follow existing code style (no extra comments, same patterns)
- Test your changes locally by running `python app.py`
- Verify the app starts without errors

### 4. Commit your changes

```bash
git add .
git commit -m "Add some amazing feature"
```

### 5. Push and create a Pull Request

```bash
git push origin feature/amazing-feature
```

Open a Pull Request on [GitHub](https://github.com/rkriad585/LocalNeural).

## Code Style Guidelines

- **Python**: Follow PEP 8. Use descriptive variable names.
- **JavaScript**: Use jQuery conventions as existing codebase does.
- **HTML**: Use TailwindCSS utility classes. Keep templates clean.
- **No extra comments**: Don't add explanatory comments unless the logic is non-obvious.

## Pull Request Process

1. Ensure your code compiles without errors (`python -m py_compile app.py`)
2. Update the README.md or docs/ if needed for new features
3. Your PR will be reviewed by maintainers who may request changes

## Bug Reports

**Great bug reports** include:
- A quick summary
- Steps to reproduce
- What you expected vs what happened
- Screenshots (if applicable)
- Your environment (OS, Python version, browser)

We use GitHub issues to track bugs. File a report at:
[https://github.com/rkriad585/LocalNeural/issues](https://github.com/rkriad585/LocalNeural/issues)

## Feature Requests

Feature requests are welcome. Tell us what you'd like to see, why you need it, and how it should work.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
