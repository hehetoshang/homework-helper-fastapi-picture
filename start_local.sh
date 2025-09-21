#!/bin/bash

# 本地开发环境启动脚本

# 设置中文字体支持
export LANG=zh_CN.UTF-8

echo "欢迎使用向量搜索微服务本地开发启动脚本"
echo "---------------------------------------"

# 检查是否已安装Python
echo "检查Python环境..."
if ! command -v python3 &> /dev/null
then
    echo "错误: Python 3 未安装，请先安装Python 3.8或更高版本"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '(?<=Python )(\d+\.\d+)')
if (( $(echo "$PYTHON_VERSION < 3.8" | bc -l) )); then
    echo "错误: Python 版本过低，请升级到3.8或更高版本"
    exit 1
fi

echo "Python版本符合要求: $PYTHON_VERSION"

# 检查是否已安装Docker
echo "检查Docker环境..."
if ! command -v docker &> /dev/null
then
    echo "警告: Docker 未安装，Milvus数据库需要使用Docker运行"
    echo "请参考https://www.docker.com/get-started安装Docker"
    read -p "是否继续启动服务（Milvus连接将失败）? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "错误: 创建虚拟环境失败"
        exit 1
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "错误: 无法激活虚拟环境"
    exit 1
fi

# 安装依赖
echo "安装项目依赖..."
pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "错误: 安装依赖失败"
    exit 1
fi

# 启动Milvus（如果Docker可用）
if command -v docker &> /dev/null; then
    echo "检查Milvus容器状态..."
    if [ "$(docker ps -q -f name=milvus-standalone)" ]; then
        echo "Milvus容器已在运行"
    elif [ "$(docker ps -aq -f name=milvus-standalone)" ]; then
        echo "启动已存在的Milvus容器..."
        docker start milvus-standalone
        if [ $? -ne 0 ]; then
            echo "错误: 启动Milvus容器失败"
        else
            echo "Milvus容器已启动，等待30秒初始化..."
            sleep 30
        fi
    else
        echo "拉取并启动Milvus容器..."
        docker run -d --name milvus-standalone -p 19530:19530 -p 9091:9091 milvusdb/milvus:v2.2.8
        if [ $? -ne 0 ]; then
            echo "错误: 启动Milvus容器失败"
        else
            echo "Milvus容器已启动，等待30秒初始化..."
            sleep 30
        fi
    fi
fi

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "未找到.env文件，复制.env.example..."
    cp .env.example .env
    echo "请根据您的环境配置.env文件"
fi

# 启动FastAPI服务
echo "启动FastAPI服务..."
echo "服务将在 http://localhost:8000 启动"
echo "API文档: http://localhost:8000/docs"
echo "指标端点: http://localhost:8000/metrics"
echo "按Ctrl+C停止服务"

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload