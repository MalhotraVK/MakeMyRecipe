# MakeMyRecipe

An LLM-based chat application that helps users create recipes catering to various cuisines and ingredients. The application provides proven recipes with links to actual pages or YouTube videos, remembers user choices over time, and shows analytics.

## Features

- 🤖 LLM-powered recipe recommendations
- 🍳 Multi-cuisine recipe database
- 💾 Conversation memory and history
- 📊 User analytics and preferences
- 🔗 Links to recipe sources and videos
- 🌐 Web-based chat interface

## Tech Stack

- **Backend**: FastAPI with Python 3.9+
- **LLM**: LiteLLM (abstraction layer for multiple LLM providers)
- **Database**: SQLite with SQLAlchemy
- **Package Management**: UV
- **Testing**: Pytest
- **Code Quality**: Black, isort, flake8, mypy

## Quick Start

### Prerequisites

- Python 3.9 or higher
- UV package manager

### Installation

1. Clone the repository:
```bash
git clone https://github.com/MalhotraVK/MakeMyRecipe.git
cd MakeMyRecipe
```

2. Install UV (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Install dependencies:
```bash
make dev-install
# or
uv sync --extra dev
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the Application

Start the development server:
```bash
make run
# or
uv run python -m makemyrecipe.api.main
```

The API will be available at:
- Main application: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Development

### Project Structure

```
MakeMyRecipe/
├── src/makemyrecipe/          # Main application code
│   ├── api/                   # FastAPI routes and endpoints
│   ├── core/                  # Core functionality (config, logging)
│   ├── models/                # Data models and database schemas
│   └── utils/                 # Utility functions
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   └── integration/           # Integration tests
├── config/                    # Configuration files
├── data/                      # Database and data files (gitignored)
├── docs/                      # Documentation
└── scripts/                   # Utility scripts
```

### Available Commands

```bash
make help           # Show all available commands
make install        # Install production dependencies
make dev-install    # Install development dependencies
make test           # Run all tests
make test-unit      # Run unit tests only
make test-integration # Run integration tests only
make lint           # Run linting
make format         # Format code
make clean          # Clean temporary files
make run            # Start development server
```

### Testing

Run the test suite:
```bash
make test
```

Run tests with coverage:
```bash
make test-cov
```

### Code Quality

Format code:
```bash
make format
```

Run linting:
```bash
make lint
```

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and customize:

- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `OPENAI_API_KEY`: Your OpenAI API key (optional)
- `LITELLM_MODEL`: Default LLM model to use
- `DATABASE_URL`: Database connection string
- `API_HOST` / `API_PORT`: Server configuration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
