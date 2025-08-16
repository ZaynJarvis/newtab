#!/bin/bash

# Docker Setup Test Script for Local Web Memory
# This script validates the Docker configuration without requiring a running daemon

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Testing Docker Setup for Local Web Memory${NC}"
echo -e "${BLUE}============================================${NC}"

# Function to check file exists
check_file() {
    local file="$1"
    local description="$2"
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $description exists: $file${NC}"
        return 0
    else
        echo -e "${RED}❌ $description missing: $file${NC}"
        return 1
    fi
}

# Function to check directory exists
check_dir() {
    local dir="$1"
    local description="$2"
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ $description exists: $dir${NC}"
        return 0
    else
        echo -e "${RED}❌ $description missing: $dir${NC}"
        return 1
    fi
}

# Function to validate Dockerfile syntax
validate_dockerfile() {
    local dockerfile="$1"
    local name="$2"
    
    echo -e "${BLUE}🔍 Validating $name...${NC}"
    
    if [ ! -f "$dockerfile" ]; then
        echo -e "${RED}❌ $name not found: $dockerfile${NC}"
        return 1
    fi
    
    # Basic syntax checks
    local errors=0
    
    # Check for required instructions
    if ! grep -q "^FROM" "$dockerfile"; then
        echo -e "${RED}❌ Missing FROM instruction in $name${NC}"
        errors=$((errors + 1))
    fi
    
    if ! grep -q "^WORKDIR" "$dockerfile"; then
        echo -e "${YELLOW}⚠️  No WORKDIR instruction in $name${NC}"
    fi
    
    if ! grep -q "^EXPOSE" "$dockerfile"; then
        echo -e "${YELLOW}⚠️  No EXPOSE instruction in $name${NC}"
    fi
    
    if ! grep -q "^CMD\|^ENTRYPOINT" "$dockerfile"; then
        echo -e "${RED}❌ Missing CMD or ENTRYPOINT in $name${NC}"
        errors=$((errors + 1))
    fi
    
    # Check for security best practices
    if grep -q "^USER root\|^USER 0" "$dockerfile"; then
        echo -e "${YELLOW}⚠️  Running as root user in $name (security concern)${NC}"
    elif grep -q "^USER" "$dockerfile"; then
        echo -e "${GREEN}✅ Non-root user specified in $name${NC}"
    fi
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✅ $name syntax validation passed${NC}"
        return 0
    else
        echo -e "${RED}❌ $name has $errors syntax errors${NC}"
        return 1
    fi
}

# Function to validate docker-compose file
validate_compose() {
    local compose_file="$1"
    local name="$2"
    
    echo -e "${BLUE}🔍 Validating $name...${NC}"
    
    if [ ! -f "$compose_file" ]; then
        echo -e "${RED}❌ $name not found: $compose_file${NC}"
        return 1
    fi
    
    # Check if docker-compose is available for validation
    if command -v docker-compose &> /dev/null; then
        if docker-compose -f "$compose_file" config > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $name syntax validation passed${NC}"
            return 0
        else
            echo -e "${RED}❌ $name has syntax errors${NC}"
            docker-compose -f "$compose_file" config
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  docker-compose not available, skipping syntax validation${NC}"
        
        # Basic YAML checks
        if grep -q "version:" "$compose_file" && grep -q "services:" "$compose_file"; then
            echo -e "${GREEN}✅ $name basic structure looks correct${NC}"
            return 0
        else
            echo -e "${RED}❌ $name missing required sections${NC}"
            return 1
        fi
    fi
}

# Function to check environment configuration
check_env_config() {
    echo -e "${BLUE}🔍 Checking environment configuration...${NC}"
    
    if [ -f ".env" ]; then
        echo -e "${GREEN}✅ .env file exists${NC}"
        
        # Check for required variables
        if grep -q "ARK_API_TOKEN=" ".env"; then
            local token=$(grep "ARK_API_TOKEN=" ".env" | cut -d'=' -f2)
            if [ "$token" != "your-ark-api-token-here" ] && [ -n "$token" ]; then
                echo -e "${GREEN}✅ ARK_API_TOKEN is configured${NC}"
            else
                echo -e "${YELLOW}⚠️  ARK_API_TOKEN needs to be set${NC}"
            fi
        else
            echo -e "${RED}❌ ARK_API_TOKEN not found in .env${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  .env file not found, using .env.example${NC}"
        if [ -f ".env.example" ]; then
            echo -e "${GREEN}✅ .env.example exists for reference${NC}"
        else
            echo -e "${RED}❌ Neither .env nor .env.example found${NC}"
        fi
    fi
}

# Function to test directory structure
check_directory_structure() {
    echo -e "${BLUE}🔍 Checking directory structure...${NC}"
    
    local errors=0
    
    # Required directories
    check_dir "backend" "Backend directory" || errors=$((errors + 1))
    check_dir "backend/src" "Backend source directory" || errors=$((errors + 1))
    check_dir "backend/tests" "Backend tests directory" || errors=$((errors + 1))
    check_dir "extension" "Extension directory" || errors=$((errors + 1))
    check_dir "nginx" "Nginx configuration directory" || errors=$((errors + 1))
    
    # Data directories (should be created)
    check_dir "data" "Data directory" || mkdir -p data
    check_dir "logs" "Logs directory" || mkdir -p logs
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✅ Directory structure is correct${NC}"
        return 0
    else
        echo -e "${RED}❌ Directory structure has $errors issues${NC}"
        return 1
    fi
}

# Function to check required files
check_required_files() {
    echo -e "${BLUE}🔍 Checking required files...${NC}"
    
    local errors=0
    
    # Docker files
    check_file "backend/Dockerfile" "Backend Dockerfile" || errors=$((errors + 1))
    check_file "backend/.dockerignore" "Backend .dockerignore" || errors=$((errors + 1))
    check_file "docker-compose.yml" "Main docker-compose file" || errors=$((errors + 1))
    check_file "docker-compose.dev.yml" "Development docker-compose file" || errors=$((errors + 1))
    
    # Configuration files
    check_file "nginx/nginx.conf" "Nginx main config" || errors=$((errors + 1))
    check_file "nginx/conf.d/default.conf" "Nginx server config" || errors=$((errors + 1))
    check_file ".env.example" "Environment example file" || errors=$((errors + 1))
    
    # Backend files
    check_file "backend/src/main.py" "Backend main application" || errors=$((errors + 1))
    check_file "backend/pyproject.toml" "Backend project config" || errors=$((errors + 1))
    
    if [ $errors -eq 0 ]; then
        echo -e "${GREEN}✅ All required files are present${NC}"
        return 0
    else
        echo -e "${RED}❌ $errors required files are missing${NC}"
        return 1
    fi
}

# Function to simulate Docker build (dry run)
simulate_docker_build() {
    echo -e "${BLUE}🔍 Simulating Docker build process...${NC}"
    
    local dockerfile="backend/Dockerfile"
    
    if [ ! -f "$dockerfile" ]; then
        echo -e "${RED}❌ Dockerfile not found${NC}"
        return 1
    fi
    
    # Check for multi-stage build
    local stages=$(grep -c "^FROM.*as" "$dockerfile" || echo 0)
    if [ $stages -gt 0 ]; then
        echo -e "${GREEN}✅ Multi-stage build detected ($stages stages)${NC}"
    fi
    
    # Check for dependency installation
    if grep -q "uv sync\|pip install\|poetry install" "$dockerfile"; then
        echo -e "${GREEN}✅ Dependency installation found${NC}"
    else
        echo -e "${YELLOW}⚠️  No dependency installation detected${NC}"
    fi
    
    # Check for security practices
    if grep -q "groupadd.*useradd\|adduser" "$dockerfile"; then
        echo -e "${GREEN}✅ Non-root user creation found${NC}"
    else
        echo -e "${YELLOW}⚠️  No non-root user creation detected${NC}"
    fi
    
    # Check for health check
    if grep -q "HEALTHCHECK" "$dockerfile"; then
        echo -e "${GREEN}✅ Health check configured${NC}"
    else
        echo -e "${YELLOW}⚠️  No health check configured${NC}"
    fi
    
    echo -e "${GREEN}✅ Docker build simulation completed${NC}"
}

# Function to generate Docker commands
generate_docker_commands() {
    echo -e "${BLUE}📋 Docker Commands for Manual Testing${NC}"
    echo -e "${BLUE}=====================================${NC}"
    
    echo -e "${YELLOW}1. Build the backend image:${NC}"
    echo "   docker build -t localwebmemory-backend:latest ./backend"
    echo ""
    
    echo -e "${YELLOW}2. Run development environment:${NC}"
    echo "   docker-compose -f docker-compose.dev.yml up --build"
    echo ""
    
    echo -e "${YELLOW}3. Run production environment:${NC}"
    echo "   docker-compose up --build -d"
    echo ""
    
    echo -e "${YELLOW}4. Run tests in container:${NC}"
    echo "   docker-compose -f docker-compose.dev.yml --profile testing up test-runner"
    echo ""
    
    echo -e "${YELLOW}5. View logs:${NC}"
    echo "   docker-compose logs -f backend"
    echo ""
    
    echo -e "${YELLOW}6. Stop all services:${NC}"
    echo "   docker-compose down"
    echo ""
}

# Main execution
main() {
    echo "Starting Docker setup validation..."
    echo ""
    
    local total_errors=0
    
    # Run all checks
    check_directory_structure || total_errors=$((total_errors + 1))
    echo ""
    
    check_required_files || total_errors=$((total_errors + 1))
    echo ""
    
    validate_dockerfile "backend/Dockerfile" "Backend Dockerfile" || total_errors=$((total_errors + 1))
    echo ""
    
    validate_compose "docker-compose.yml" "Main docker-compose.yml" || total_errors=$((total_errors + 1))
    echo ""
    
    validate_compose "docker-compose.dev.yml" "Development docker-compose.yml" || total_errors=$((total_errors + 1))
    echo ""
    
    check_env_config
    echo ""
    
    simulate_docker_build
    echo ""
    
    generate_docker_commands
    echo ""
    
    # Final summary
    if [ $total_errors -eq 0 ]; then
        echo -e "${GREEN}🎉 Docker setup validation completed successfully!${NC}"
        echo -e "${GREEN}✅ All configurations appear to be correct${NC}"
        echo -e "${BLUE}💡 To test with actual Docker, ensure Docker daemon is running and use the commands above${NC}"
    else
        echo -e "${RED}❌ Docker setup validation completed with $total_errors errors${NC}"
        echo -e "${RED}🔧 Please fix the issues above before proceeding${NC}"
        return 1
    fi
}

# Run main function
main "$@"