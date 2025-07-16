@echo off
setlocal EnableDelayedExpansion

echo ===============================================
echo   RAG Chatbot - Windows Installation Script
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Display Python version
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo [INFO] Found !PYTHON_VERSION!

echo.
echo Step 1: Cleaning up previous installation...
if exist "venv" (
    echo [INFO] Removing existing virtual environment...
    rmdir /s /q venv
)

echo.
echo Step 2: Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    echo Please ensure Python and pip are properly installed
    pause
    exit /b 1
)

echo.
echo Step 3: Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

echo.
echo Step 4: Upgrading pip...
python -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [WARNING] Failed to upgrade pip, continuing anyway...
)

echo.
echo Step 5: Installing dependencies...
echo [INFO] This may take a few minutes...
pip install -r local_requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    echo Please check your internet connection and try again
    pause
    exit /b 1
)

echo.
echo Step 6: Creating required directories...
if not exist "uploads" (
    mkdir uploads
    echo [INFO] Created uploads directory
)
if not exist "faiss_index" (
    mkdir faiss_index
    echo [INFO] Created faiss_index directory
)
if not exist "static\logos" (
    mkdir static\logos
    echo [INFO] Created static\logos directory
)

echo.
echo Step 7: Creating environment configuration...
if not exist ".env" (
    echo # OpenAI Configuration > .env
    echo OPENAI_API_KEY=your_openai_api_key_here >> .env
    echo. >> .env
    echo # Session Configuration >> .env
    echo SESSION_SECRET=your_secret_key_here >> .env
    echo. >> .env
    echo # Database Configuration (Optional) >> .env
    echo # DATABASE_URL=postgresql://user:pass@localhost:5432/chatbot >> .env
    echo # MYSQL_DATABASE_URL=mysql://user:pass@localhost:3306/chatbot >> .env
    echo.
    echo [INFO] Created .env file template
    echo [IMPORTANT] Please edit the .env file and add your actual OpenAI API key!
) else (
    echo [INFO] .env file already exists, skipping creation
)

echo.
echo Step 8: Testing installation...
python -c "import flask, openai, faiss; print('[INFO] Core dependencies imported successfully')"
if %errorlevel% neq 0 (
    echo [ERROR] Installation verification failed
    pause
    exit /b 1
)

echo.
echo ===============================================
echo   Installation Complete!
echo ===============================================
echo.
echo Next steps:
echo 1. Edit the .env file and add your OpenAI API key
echo 2. To run the application:
echo    - Activate virtual environment: venv\Scripts\activate
echo    - Start the server: python main.py
echo    - Open browser to: http://localhost:5000
echo.
echo For admin panel: http://localhost:5000/admin
echo For chatbot: http://localhost:5000/chatbot
echo.
echo Note: Keep the virtual environment activated when running the application
echo.
pause