#!/bin/bash

echo "Installing RAG Chatbot - Unix/Linux/macOS Setup"
echo "=============================================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo
echo "Step 1: Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error: Failed to create virtual environment."
    exit 1
fi

echo
echo "Step 2: Activating virtual environment..."
source venv/bin/activate

echo
echo "Step 3: Installing dependencies..."
pip install -r local_requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

echo
echo "Step 4: Creating required directories..."
mkdir -p uploads
mkdir -p faiss_index

echo
echo "Step 5: Creating .env file template..."
if [ ! -f ".env" ]; then
    cat > .env << EOL
OPENAI_API_KEY=your_openai_api_key_here
SESSION_SECRET=your_secret_key_here
EOL
    echo "IMPORTANT: Please edit the .env file and add your actual OpenAI API key!"
fi

echo
echo "Installation complete!"
echo
echo "Next steps:"
echo "1. Edit the .env file and add your OpenAI API key"
echo "2. Activate virtual environment: source venv/bin/activate"
echo "3. Run: python main.py"
echo "4. Open your browser to: http://localhost:5000"
echo