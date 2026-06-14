# Contributing

## Quick Start

```bash
git clone https://github.com/nkyang10/video-srt.git
cd video-srt
pip install -e ".[dev]"
```

## Testing

```bash
pytest -v
```

## Code Style

```bash
ruff check .
```

## Pull Request Process

1. Create an issue describing the change
2. Fork and create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass and ruff is clean
5. Submit PR with `Closes #N` in description
