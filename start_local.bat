@echo off
chcp 65001
cls

REM 本地开发环境启动脚本（Windows版本）

echo Welcome to Vector Search Microservice Local Development Startup Script

echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed, please install Python 3.8 or higher
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查Python版本
for /f "tokens=2 delims=." %%a in ('python --version 2^>^&1') do (
    set "PYTHON_MINOR=%%a"
)

if %PYTHON_MINOR% lss 8 (
    echo Error: Python version is too low, please upgrade to 3.8 or higher
    pause
    exit /b 1
)

echo Python version meets requirements

REM 创建虚拟环境
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM 修复虚拟环境（如果pip缺失）
echo Checking virtual environment...
if not exist "venv\Scripts\pip.exe" (
    echo Fixing virtual environment...
    python -m venv venv --upgrade
)

REM 激活虚拟环境
echo Activating virtual environment...
call venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo Error: Cannot activate virtual environment
    pause
    exit /b 1
)

REM 确保pip可用
echo Ensuring pip is available...
python -m ensurepip --default-pip
python -m pip install --upgrade pip

REM 安装依赖
echo Installing project dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

REM 检查.env文件
if not exist ".env" (
    echo .env file not found, copying from .env.example...
    copy .env.example .env
    echo Please configure the .env file according to your environment
)

REM 启动FastAPI服务
echo Starting FastAPI service...
echo Service will start at http://localhost:8000
echo API documentation: http://localhost:8000/docs
echo Metrics endpoint: http://localhost:8000/metrics
echo Press Ctrl+C to stop the service

echo.

REM 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM 服务停止后，恢复命令提示符
if %errorlevel% neq 0 (
    echo Service startup failed
    pause
)