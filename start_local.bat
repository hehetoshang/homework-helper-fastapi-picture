@echo off

REM 本地开发环境启动脚本（Windows版本）

cls
echo 欢迎使用向量搜索微服务本地开发启动脚本

echo 检查Python环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: Python 未安装，请先安装Python 3.8或更高版本
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 检查Python版本
for /f "tokens=2 delims=." %%a in ('python --version 2^>^&1') do (
    set "PYTHON_MINOR=%%a"
)

if %PYTHON_MINOR% lss 8 (
    echo 错误: Python 版本过低，请升级到3.8或更高版本
    pause
    exit /b 1
)

echo Python版本符合要求

REM 检查是否已安装Docker
echo 检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 警告: Docker 未安装，Milvus数据库需要使用Docker运行
    echo 请参考https://www.docker.com/get-started安装Docker
    set /p CONTINUE=是否继续启动服务（Milvus连接将失败）? (y/n): 
    if /i "%CONTINUE%" neq "y" (
        exit /b 1
    )
)

REM 创建虚拟环境
if not exist "venv" (
    echo 创建Python虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo 错误: 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo 错误: 无法激活虚拟环境
    pause
    exit /b 1
)

REM 安装依赖
echo 安装项目依赖...
pip install --upgrade pip
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 错误: 安装依赖失败
    pause
    exit /b 1
)

REM 启动Milvus（如果Docker可用）
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    echo 检查Milvus容器状态...
    docker ps -q -f name=milvus-standalone >nul 2>&1
    if %errorlevel% equ 0 (
        echo Milvus容器已在运行
    ) else (
        docker ps -aq -f name=milvus-standalone >nul 2>&1
        if %errorlevel% equ 0 (
            echo 启动已存在的Milvus容器...
            docker start milvus-standalone
            if %errorlevel% neq 0 (
                echo 错误: 启动Milvus容器失败
            ) else (
                echo Milvus容器已启动，等待30秒初始化...
                timeout /t 30 >nul
            )
        ) else (
            echo 拉取并启动Milvus容器...
            docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.2.8
            if %errorlevel% neq 0 (
                echo 错误: 启动Milvus容器失败
            ) else (
                echo Milvus容器已启动，等待30秒初始化...
                timeout /t 30 >nul
            )
        )
    )
)

REM 检查.env文件
if not exist ".env" (
    echo 未找到.env文件，复制.env.example...
    copy .env.example .env
    echo 请根据您的环境配置.env文件
)

REM 启动FastAPI服务
echo 启动FastAPI服务...
echo 服务将在 http://localhost:8000 启动
echo API文档: http://localhost:8000/docs
echo 指标端点: http://localhost:8000/metrics
echo 按Ctrl+C停止服务

echo.

REM 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM 服务停止后，恢复命令提示符
if %errorlevel% neq 0 (
    echo 服务启动失败
    pause
)