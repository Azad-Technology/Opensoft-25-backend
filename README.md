# Opensoft-25-backend

## Development Setup

### Setting up the development environment

1. Clone the repository

    ```bash
    git clone https://github.com/your-org/opensoft-25-backend.git
    cd opensoft-25-backend
    ```

2. Create and activate a virtual environment

    ```bash
    # Create a virtual environment
    python -m venv .venv

    # On Windows:
    .venv\Scripts\activate

    # On Unix/MacOS:
    source .venv/bin/activate
    ```

3. Install dependencies (for all the developers, use the second one)

    ```bash
    # Install all project dependencies
    pip install -e .

    # Or if you have development dependencies:
    pip install -e ".[dev]"
    ```

4. Install pre-commit hooks

    ```bash
    # Install pre-commit hooks for code quality
    pre-commit install
    ```

5. BEFORE YOU MAKE A PUSH/PR, RUN THIS COMMAND

    ```bash
    pre-commit run --all-files
    ```

and if you find issues from the code you make, it's your responsibility to fix it.
