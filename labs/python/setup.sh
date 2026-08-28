#!/bin/bash
# Setup script for Porto SDK Python Lab
# Automatically installs the SDK and sets up the environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SDK_DIR="$SCRIPT_DIR/../../sdks/porto-sdk-python"
PYTHON_BIN="${PYTHON_BIN:-python3.13}"

# ============================================================================
# Functions
# ============================================================================

# Check if SDK directory exists
check_sdk_exists() {
    local sdk_path="$1"
    if [ ! -d "$sdk_path" ]; then
        echo "❌ Error: SDK package not found at $sdk_path"
        exit 1
    fi
}

# Setup Python virtual environment
setup_venv() {
    recreate_venv() {
        # venv is a Docker volume mountpoint; remove contents, not the directory.
        shopt -s dotglob nullglob
        rm -rf venv/*
        shopt -u dotglob nullglob
        "$PYTHON_BIN" -m venv venv
    }

    if ! command -v "$PYTHON_BIN" > /dev/null 2>&1; then
        echo "❌ Error: $PYTHON_BIN not found (required for SDK baseline Python >=3.13)"
        exit 1
    fi

    if [ -d "venv" ]; then
        # Check if pip is broken - recreate venv if needed
        if [ ! -x venv/bin/python ] || ! venv/bin/python -m pip --version > /dev/null 2>&1; then
            echo "📦 Recreating virtual environment due to pip corruption..."
            recreate_venv
            return 0
        fi

        # Recreate if existing venv uses unsupported Python version.
        existing_major_minor="$(venv/bin/python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
        if [ "$existing_major_minor" != "3.13" ]; then
            echo "📦 Recreating virtual environment for Python 3.13 baseline..."
            recreate_venv
            return 0
        fi
    fi

    if [ ! -d "venv" ]; then
        echo "📦 Creating virtual environment..."
        "$PYTHON_BIN" -m venv venv
    fi
}

# Install Python dependencies
install_python_deps() {
    local sdk_path="$1"
    local resources_data_path="$SCRIPT_DIR/../../resources/porto-data"
    local resources_features_path="$SCRIPT_DIR/../../resources/porto-features"

    echo "🔌 Activating virtual environment..."
    source venv/bin/activate

    echo "📥 Installing Python SDK and dependencies..."
    echo "   - Upgrading pip..."
    python -m pip install --upgrade pip --quiet

    echo "   - Installing local resource packages (porto-data + porto-features)..."
    python -m pip install -e "$resources_data_path" --quiet
    python -m pip install -e "$resources_features_path" --quiet

    echo "   - Installing SDK in editable mode (with dev extras)..."
    python -m pip install -e "$sdk_path[dev]" --quiet

    echo "   - Installing FastAPI lab dependencies..."
    python -m pip install "fastapi>=0.116.0" "uvicorn[standard]>=0.35.0" "httpx>=0.28.0" python-dotenv watchfiles --quiet

    echo "   ✅ SDK installed successfully!"
}

# Create .env file from example or template
create_env_file() {
    if [ -f "../../.env" ]; then
        return 0
    fi

    echo "📝 Creating repo root .env from .env.example"
    if [ -f "../../.env.example" ]; then
        cp "../../.env.example" "../../.env"
        echo "   Edit PORTO_DEUTSCHEPOST_INTERNETMARKE_* in ../../.env"
    fi
}

# Print usage instructions
print_usage() {
    echo ""
    echo "To use the lab:"
    echo ""
    echo "    source venv/bin/activate"
    echo "    python example_basic.py  # CLI smoke: porto config check --json"
    echo "    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    echo "    python example_cli_provider.py  # Bound provider smoke"
    echo "    deactivate  # When done"
    echo ""
}

# ============================================================================
# Main Setup
# ============================================================================

echo "🐍 Setting up Porto SDK Python Lab..."
echo ""

check_sdk_exists "$SDK_DIR"
setup_venv
install_python_deps "$SDK_DIR"
create_env_file

echo ""
echo "✅ Setup complete!"
print_usage
