#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "==============================================="
echo "   RAG Chatbot - Unix/Linux/macOS Installation"
echo "==============================================="
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip python3-venv"
    echo "  CentOS/RHEL: sudo yum install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

# Display Python version
PYTHON_VERSION=$(python3 --version)
print_info "Found $PYTHON_VERSION"

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is not installed"
    echo "Please install pip3:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-pip"
    echo "  CentOS/RHEL: sudo yum install python3-pip"
    echo "  macOS: pip3 should be installed with Python3"
    exit 1
fi

echo
echo "Step 1: Cleaning up previous installation..."
if [ -d "venv" ]; then
    print_info "Removing existing virtual environment..."
    rm -rf venv
fi

echo
echo "Step 2: Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    print_error "Failed to create virtual environment"
    echo "Please ensure python3-venv is installed:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-venv"
    exit 1
fi

echo
echo "Step 3: Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    print_error "Failed to activate virtual environment"
    exit 1
fi

echo
echo "Step 4: Upgrading pip..."
pip install --upgrade pip
if [ $? -ne 0 ]; then
    print_warning "Failed to upgrade pip, continuing anyway..."
fi

echo
echo "Step 5: Installing dependencies..."
print_info "This may take a few minutes..."
pip install -r local_requirements.txt
if [ $? -ne 0 ]; then
    print_error "Failed to install dependencies"
    echo "Please check your internet connection and try again"
    echo "If you're on Ubuntu/Debian, you may need to install:"
    echo "  sudo apt-get install build-essential python3-dev"
    exit 1
fi

echo
echo "Step 6: Creating required directories..."
mkdir -p uploads && print_info "Created uploads directory"
mkdir -p faiss_index && print_info "Created faiss_index directory"
mkdir -p static/logos && print_info "Created static/logos directory"

echo
echo "Step 7: Creating environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << EOL
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Session Configuration
SESSION_SECRET=your_secret_key_here

# Database Configuration (Optional)
# DATABASE_URL=postgresql://user:pass@localhost:5432/chatbot
# MYSQL_DATABASE_URL=mysql://user:pass@localhost:3306/chatbot
EOL
    print_info "Created .env file template"
    print_warning "Please edit the .env file and add your actual OpenAI API key!"
else
    print_info ".env file already exists, skipping creation"
fi

echo
echo "Step 8: Setting up permissions..."
chmod +x install_unix.sh
chmod +x install_windows.bat

echo
echo "Step 9: Testing installation..."
python3 -c "import flask, openai, faiss; print('[INFO] Core dependencies imported successfully')"
if [ $? -ne 0 ]; then
    print_error "Installation verification failed"
    exit 1
fi

echo
echo "==============================================="
echo "   Installation Complete!"
echo "==============================================="
echo
echo "Next steps:"
echo "1. Edit the .env file and add your OpenAI API key:"
echo "   nano .env  # or your preferred editor"
echo
echo "2. To run the application:"
echo "   source venv/bin/activate"
echo "   python3 main.py"
echo
echo "3. Open your browser to:"
echo "   Main chatbot: http://localhost:5000"
echo "   Admin panel: http://localhost:5000/admin"
echo
echo "Note: Keep the virtual environment activated when running the application"
echo
echo "To stop the application: Press Ctrl+C in the terminal"
echo "To deactivate virtual environment: deactivate"
echo