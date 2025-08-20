.PHONY: install test lint clean dev venv

# Virtual environment detection and activation
VENV_NAME ?= .venv

# Detect OS for proper path handling
ifeq ($(OS),Windows_NT)
	VENV_ACTIVATE = $(VENV_NAME)\Scripts\activate
	VENV_TEST = $(VENV_NAME)\Scripts\pytest.exe
	VENV_PYTHON = $(VENV_NAME)\Scripts\python.exe
	RM_CMD = rmdir /s /q
	CP = copy
	SEP = \\
	ACTIVATE_CMD = call
else
	VENV_ACTIVATE = $(VENV_NAME)/bin/activate
	VENV_TEST = $(VENV_NAME)/bin/pytest
	VENV_PYTHON = $(VENV_NAME)/bin/python
	RM_CMD = rm -rf
	CP = cp
	SEP = /
	ACTIVATE_CMD = .
endif

# Python interpreter
PYTHON = python
# Path to package manager (uv or pip)
# Check if uv is available, otherwise use plain pip
UV := $(shell command -v uv 2> /dev/null)
ifeq ($(UV),)
	PACKAGE_CMD = pip install
else
	PACKAGE_CMD = $(UV) pip install
endif

# Project paths
SRC_DIR = mcp_claude_code
TEST_DIR = tests

# Create virtual environment
venv:
	$(PYTHON) -m venv $(VENV_NAME)
ifeq ($(OS),Windows_NT)
	@echo "Virtual environment created. Run '$(VENV_ACTIVATE)' to activate it."
else
	@echo "Virtual environment created. Run 'source $(VENV_ACTIVATE)' to activate it."
endif

install: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && $(PACKAGE_CMD) -e "."

uninstall: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && $(PYTHON) -m pip uninstall -y mcp-claude-code

reinstall: uninstall install

install-dev: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && $(PACKAGE_CMD) -e ".[dev]"

install-test: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && $(PACKAGE_CMD) -e ".[test]"

test: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && python -m pytest $(TEST_DIR) --disable-warnings

test-cov: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && python -m pytest --cov=$(SRC_DIR) $(TEST_DIR)

lint: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && ruff check $(SRC_DIR) $(TEST_DIR)

format: venv-check
	$(ACTIVATE_CMD) $(VENV_ACTIVATE) && ruff format $(SRC_DIR) $(TEST_DIR)

clean:
	$(RM_CMD) .pytest_cache htmlcov .coverage 2>nul || true
ifeq ($(OS),Windows_NT)
	for /d /r . %d in (__pycache__) do @if exist "%d" rd /s /q "%d"
else
	find . -name "__pycache__" -type d -exec rm -rf {} +
endif

# Helper to check for virtual environment
venv-check:
	@if [ ! -f $(VENV_ACTIVATE) ]; then \
		echo "Virtual environment not found. Creating one..." ; \
		$(MAKE) venv ; \
	fi

# Default target
all: test
