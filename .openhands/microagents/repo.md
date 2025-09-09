# Repository Purpose

MakeMyRecipe is an LLM-based chat application that helps users create recipes catering to various cuisines and ingredients. The application provides proven recipes with links to actual pages or YouTube videos, remembers user choices over time, and shows analytics.

# Setup Instructions

## Prerequisites
- Python 3.9 or higher
- UV package manager

## Installation
1. Clone the repository: `git clone https://github.com/MalhotraVK/MakeMyRecipe.git`
2. Install UV: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `make dev-install` or `uv sync --extra dev`
4. Set up environment variables: `cp .env.example .env` and edit with your API keys

## Running the Application
Start the development server: `make run` or `uv run python -m makemyrecipe.api.main`

The API will be available at:
- Main application: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

# Repository Structure

- `/src/makemyrecipe/`: Main application code
  - `/api/`: FastAPI routes and endpoints
  - `/core/`: Core functionality (config, logging)
  - `/models/`: Data models and database schemas
  - `/utils/`: Utility functions
- `/tests/`: Test suite
  - `/unit/`: Unit tests
  - `/integration/`: Integration tests
- `/config/`: Configuration files
- `/data/`: Database and data files (gitignored)
- `/docs/`: Documentation
- `/scripts/`: Utility scripts

# Tech Stack

- **Backend**: FastAPI with Python 3.9+
- **LLM**: LiteLLM (abstraction layer for multiple LLM providers)
- **Database**: SQLite with SQLAlchemy
- **Package Management**: UV
- **Testing**: Pytest
- **Code Quality**: Black, isort, flake8, mypy

# Development Guidelines

## Before Submitting a PR

1. **Ensure all unit test cases are passing**: Run `make test` to execute the full test suite
2. **Ensure lint is passing**: Run `make lint` to check code quality with flake8 and mypy

## Available Commands

- `make test`: Run all tests
- `make test-unit`: Run unit tests only
- `make test-integration`: Run integration tests only
- `make lint`: Run linting (flake8, mypy)
- `make format`: Format code (black, isort)
- `make run`: Start development server
- `make clean`: Clean temporary files

## Code Quality Standards

The project uses strict code quality tools:
- **Black**: Code formatting with 88 character line length
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking with strict settings
- **pytest**: Testing with coverage reporting

Always run `make format` before committing to ensure consistent code style, and `make lint` to catch any issues.