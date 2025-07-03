@echo off
echo Installing RAG Chatbot - Windows Setup
echo =====================================

echo.
echo Step 1: Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Error: Failed to create virtual environment. Please ensure Python is installed.
    pause
    exit /b 1
)

echo.
echo Step 2: Activating virtual environment...
call venv\Scripts\activate

echo.
echo Step 3: Installing dependencies...
pip install -r local_requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo Step 4: Creating required directories...
if not exist "uploads" mkdir uploads
if not exist "faiss_index" mkdir faiss_index

echo.
echo Step 5: Creating .env file template...
if not exist ".env" (
    echo OPENAI_API_KEY=your_openai_api_key_here > .env
    echo SESSION_SECRET=your_secret_key_here >> .env
    echo.
    echo IMPORTANT: Please edit the .env file and add your actual OpenAI API key!
)

echo.
echo Installation complete!
echo.
echo Next steps:
echo 1. Edit the .env file and add your OpenAI API key
echo 2. Run: python main.py
echo 3. Open your browser to: http://localhost:5000
echo.
pause