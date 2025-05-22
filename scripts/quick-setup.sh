#!/bin/bash

# Propcorn Rate Limiter - Quick Setup Script
# This script helps you get started with the rate limiter project quickly

set -e

echo "🚀 Propcorn Rate Limiter - Quick Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_status "Docker found: $(docker --version)"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    print_status "Docker Compose found: $(docker-compose --version)"
}

# Check if Poetry is installed
check_poetry() {
    if ! command -v poetry &> /dev/null; then
        print_warning "Poetry is not installed. Installing Poetry..."
        curl -sSL https://install.python-poetry.org | python3 -
        export PATH="$HOME/.local/bin:$PATH"
        if ! command -v poetry &> /dev/null; then
            print_error "Failed to install Poetry. Please install it manually."
            echo "Visit: https://python-poetry.org/docs/#installation"
            exit 1
        fi
    fi
    print_status "Poetry found: $(poetry --version)"
}

# Setup selection
show_setup_menu() {
    echo ""
    echo "Choose your setup option:"
    echo "1) Development setup (with code reloading)"
    echo "2) Production setup (optimized containers)"
    echo "3) Testing only (run tests and visualizations)"
    echo "4) Full setup (development + run tests)"
    echo ""
    read -p "Enter your choice (1-4): " choice
    echo ""
}

# Development setup
setup_development() {
    print_step "Setting up development environment..."
    
    # Install Python dependencies
    print_status "Installing Python dependencies with Poetry..."
    poetry install
    
    # Start development containers
    print_status "Starting development containers..."
    docker-compose -f docker-compose.dev.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 10
    
    # Test the connection
    print_status "Testing application health..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_status "✅ Application is running successfully!"
        echo ""
        echo "🌟 Development environment is ready!"
        echo "📖 API Documentation: http://localhost:8000/docs"
        echo "🔍 Health Check: http://localhost:8000/health"
        echo ""
        echo "To run the application locally:"
        echo "  poetry run uvicorn propcorn_ratelimiter.main:app --reload"
        echo ""
        echo "To run tests:"
        echo "  poetry run pytest tests/ -v"
        echo ""
        echo "To generate visualizations:"
        echo "  poetry run pytest tests/test_visualization.py -v"
    else
        print_warning "Application health check failed. Check the logs:"
        echo "  docker-compose -f docker-compose.dev.yml logs"
    fi
}

# Production setup
setup_production() {
    print_step "Setting up production environment..."
    
    # Build and start production containers
    print_status "Building production containers..."
    docker-compose -f docker-compose.prod.yml build
    
    print_status "Starting production containers..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Test the connection
    print_status "Testing application health..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_status "✅ Production environment is running successfully!"
        echo ""
        echo "🌟 Production environment is ready!"
        echo "📖 API Documentation: http://localhost:8000/docs"
        echo "🔍 Health Check: http://localhost:8000/health"
        echo ""
        echo "To view logs:"
        echo "  docker-compose -f docker-compose.prod.yml logs -f"
        echo ""
        echo "To restart services:"
        echo "  docker-compose -f docker-compose.prod.yml restart"
    else
        print_warning "Application health check failed. Check the logs:"
        echo "  docker-compose -f docker-compose.prod.yml logs"
    fi
}

# Testing setup
setup_testing() {
    print_step "Setting up testing environment..."
    
    # Install dependencies
    print_status "Installing dependencies..."
    poetry install
    
    # Start Redis for testing
    print_status "Starting Redis for testing..."
    docker-compose -f docker-compose.dev.yml up -d redis
    
    # Wait for Redis
    sleep 5
    
    # Run tests
    print_status "Running test suite..."
    poetry run pytest tests/ -v --cov=src/propcorn_ratelimiter
    
    print_status "Generating visualization tests..."
    poetry run pytest tests/test_visualization.py -v
    
    print_status "✅ Testing completed!"
    echo ""
    echo "📊 Check the results/ directory for visualization outputs"
    echo "📈 Coverage report generated"
}

# Full setup
setup_full() {
    print_step "Setting up full development environment..."
    
    setup_development
    echo ""
    print_step "Running tests and generating visualizations..."
    poetry run pytest tests/ -v
    poetry run pytest tests/test_visualization.py -v
    
    print_status "✅ Full setup completed!"
    echo ""
    echo "📊 Check the results/ directory for visualization outputs"
}

# Cleanup function
cleanup() {
    echo ""
    print_step "Cleaning up..."
    docker-compose -f docker-compose.dev.yml down > /dev/null 2>&1 || true
    docker-compose -f docker-compose.prod.yml down > /dev/null 2>&1 || true
    print_status "Cleanup completed"
}

# Main execution
main() {
    # Trap for cleanup on exit
    trap cleanup EXIT
    
    # Check prerequisites
    print_step "Checking prerequisites..."
    check_docker
    check_docker_compose
    check_poetry
    
    # Show menu and get user choice
    show_setup_menu
    
    case $choice in
        1)
            setup_development
            ;;
        2)
            setup_production
            ;;
        3)
            setup_testing
            ;;
        4)
            setup_full
            ;;
        *)
            print_error "Invalid choice. Please run the script again and choose 1-4."
            exit 1
            ;;
    esac
    
    echo ""
    print_status "Setup completed! 🎉"
    echo ""
    echo "Useful commands:"
    echo "  📚 View documentation: docs/EC2_SETUP.md, docs/GITHUB_SETUP.md"
    echo "  🔧 Run tests: poetry run pytest tests/ -v"
    echo "  📊 Generate visualizations: poetry run pytest tests/test_visualization.py -v"
    echo "  🚀 Start development: docker-compose -f docker-compose.dev.yml up -d"
    echo "  🏭 Start production: docker-compose -f docker-compose.prod.yml up -d"
    echo ""
}

# Run main function
main "$@" 