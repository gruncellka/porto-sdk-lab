#!/bin/bash
# Setup script for Porto SDK TypeScript Lab

set -e

SDK_PACKAGE_PATH="../../sdks/porto-sdk-typescript"
PACKAGE_MANAGER_CMD="pnpm"

# ============================================================================
# Functions
# ============================================================================

# Check if we're in the correct directory
check_lab_directory() {
    if [ ! -f "package.json" ] || [ ! -f "setup.sh" ]; then
        echo "❌ Error: Must run setup.sh from labs/typescript directory"
        exit 1
    fi
}

# Check if pnpm is installed
check_pnpm_installed() {
    if ! command -v pnpm &> /dev/null; then
        echo "❌ Error: pnpm is not installed"
        echo "   Enable it with Corepack: corepack enable && corepack prepare pnpm@10 --activate"
        exit 1
    fi
}

# Create .npmrc to isolate from parent workspace
create_npmrc() {
    if [ -f ".npmrc" ]; then
        return 0
    fi

    echo "📝 Creating .npmrc to isolate this project from workspace..."
    cat > .npmrc << 'EOF'
# Ignore parent workspace - install only for this lab project
ignore-workspace-root-check=true
EOF
}

# Install lab dependencies
install_lab_dependencies() {
    echo "📥 Installing dependencies with pnpm..."
    echo "   This will install TypeScript and tsx locally (not globally)..."
    echo "   Installing only for this lab project (ignoring root workspace)..."

    # Lab lockfiles may drift while SDK integration evolves; allow refresh.
    $PACKAGE_MANAGER_CMD install --no-frozen-lockfile

    echo "   - Linking local resource packages into SDK node_modules (no manifest changes) ..."
}

# Verify local tools are installed
verify_local_tools() {
    if [ -f "node_modules/.bin/tsc" ]; then
        echo "✅ TypeScript installed locally: $(node_modules/.bin/tsc --version)"
    else
        echo "⚠️  Warning: TypeScript not found in node_modules/.bin/"
    fi

    if [ -f "node_modules/.bin/tsx" ]; then
        if node_modules/.bin/tsx --version > /dev/null 2>&1; then
            local tsx_version=$(node_modules/.bin/tsx --version)
            echo "✅ tsx installed locally: $tsx_version"
        else
            echo "⚠️  Warning: tsx binary is broken, attempting to fix..."
            $PACKAGE_MANAGER_CMD install tsx --force
            if node_modules/.bin/tsx --version > /dev/null 2>&1; then
                echo "✅ tsx fixed and working"
            else
                echo "❌ Error: Could not fix tsx installation"
            fi
        fi
    else
        echo "⚠️  Warning: tsx not found in node_modules/.bin/"
    fi
}

# Setup SDK package (install deps and build)
setup_sdk_package() {
    local sdk_path="$1"

    if [ ! -d "$sdk_path" ]; then
        echo "⚠️  Warning: SDK package not found at $sdk_path"
        return 0
    fi

    # Install SDK dependencies if needed (volume may create an empty node_modules dir)
    if [ ! -d "$sdk_path/node_modules" ] || [ ! -d "$sdk_path/node_modules/zod" ]; then
        echo "📦 Installing SDK package dependencies..."
        (cd "$sdk_path" && $PACKAGE_MANAGER_CMD install)
    else
        echo "✅ SDK package dependencies already installed"
    fi

    echo "   - Linking local resource packages into SDK node_modules (Lab-owned) ..."
    node "$(cd "$sdk_path/../.." && pwd)/scripts/lab/link-typescript.mjs" "$sdk_path"

    local had_dist=0
    if [ -d "$sdk_path/dist" ]; then
        had_dist=1
    fi

    echo "🔨 Building SDK package (TypeScript compilation)..."
    if ! (cd "$sdk_path" && $PACKAGE_MANAGER_CMD run build); then
        if [ "$had_dist" -eq 1 ]; then
            echo "   ⚠️  SDK build failed, using existing dist output."
            echo "   Continue working and fix SDK build errors in sdks/porto-sdk-typescript."
        else
            echo "❌ SDK build failed and no existing dist output is available."
            return 1
        fi
    fi
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
    echo "  pnpm run example:basic  # CLI smoke: pnpm exec porto config check --json"
    echo "  pnpm run dev"
    echo "  pnpm run example:stamp  # Requires credentials in .env"
    echo ""
}

# ============================================================================
# Main Setup
# ============================================================================

echo "📘 Setting up Porto SDK TypeScript Lab..."
echo ""

check_lab_directory
check_pnpm_installed
create_npmrc
install_lab_dependencies
verify_local_tools
setup_sdk_package "$SDK_PACKAGE_PATH"
create_env_file

echo ""
echo "✅ Setup complete!"
print_usage
