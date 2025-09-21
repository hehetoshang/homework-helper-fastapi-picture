import pytest
import httpx
import base64
import os
from fastapi.testclient import TestClient
import numpy as np

from app.main import app
from app.milvus_client import milvus_client

# 创建测试客户端
client = TestClient(app)


# 测试前的准备工作
@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown():
    """测试前连接Milvus，测试后清理数据"""
    # 连接Milvus
    try:
        milvus_client.connect()
    except Exception as e:
        pytest.skip(f"无法连接到Milvus: {e}")
    
    # 测试前清理可能存在的测试数据
    try:
        milvus_client.delete_by_id("test_question_1")
        milvus_client.delete_by_id("test_question_2")
    except Exception:
        pass
    
    yield  # 测试执行
    
    # 测试后清理数据
    try:
        milvus_client.delete_by_id("test_question_1")
        milvus_client.delete_by_id("test_question_2")
    except Exception:
        pass


# 创建一个测试用的base64编码图片
def get_test_image_base64():
    """创建一个简单的测试图片并返回其base64编码"""
    # 创建一个简单的黑白图片（1x1像素）
    image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00:~\x9bU\x00\x00\x00\x06bKGD\x00\x00\x00\x00\x00\x00\xbfa\x9c\x00\x00\x00\tpHYs\x00\x00\x0fa\x00\x00\x0fa\x01h\x61\xd4\x00\x00\x00\x07tIME\x07\xdd\x0c\x12\x05\x11\x08\x1d\xad\x97\x00\x00\x00\x0cIDAT\x08\xd7c\x00\x01\x00\x00\x05\x00\x01\xe3\xb2\xca\x00\x00\x00\x00IEND\xaeB`\x82'
    return base64.b64encode(image_data).decode('utf-8')


# 测试健康检查端点
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "database" in data
    assert "uptime" in data


# 测试统计信息端点
def test_get_stats():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "question_count" in data
    assert "collection_size" in data
    assert "avg_vector_size" in data
    assert "api_calls" in data
    assert "error_count" in data


# 测试添加题目端点
def test_add_question():
    # 准备测试数据
    image_base64 = get_test_image_base64()
    question_data = {
        "question_id": "test_question_1",
        "image_base64": image_base64,
        "metadata": {"subject": "math", "grade": "3"}
    }
    
    # 发送请求
    response = client.post("/questions", json=question_data)
    
    # 验证响应
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "题目添加成功"
    assert data["question_id"] == "test_question_1"
    
    # 验证数据是否正确添加
    get_response = client.get("/questions/test_question_1")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["question_id"] == "test_question_1"
    assert get_data["metadata"]["subject"] == "math"
    
    # 测试添加重复的题目ID
    duplicate_response = client.post("/questions", json=question_data)
    assert duplicate_response.status_code == 409


# 测试批量添加题目端点
def test_batch_add_questions():
    # 准备测试数据
    image_base64 = get_test_image_base64()
    batch_data = {
        "questions": [
            {
                "question_id": "test_question_2",
                "image_base64": image_base64,
                "metadata": {"subject": "english", "grade": "4"}
            }
        ]
    }
    
    # 发送请求
    response = client.post("/questions/batch", json=batch_data)
    
    # 验证响应
    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "批量题目添加成功"
    assert data["count"] == 1
    
    # 验证数据是否正确添加
    get_response = client.get("/questions/test_question_2")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["question_id"] == "test_question_2"


# 测试查询题目端点
def test_get_question():
    # 首先添加一个测试题目
    image_base64 = get_test_image_base64()
    question_data = {
        "question_id": "test_question_1",
        "image_base64": image_base64,
        "metadata": {"subject": "math", "grade": "3"}
    }
    client.post("/questions", json=question_data)
    
    # 查询已存在的题目
    response = client.get("/questions/test_question_1")
    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == "test_question_1"
    
    # 查询不存在的题目
    not_found_response = client.get("/questions/non_existent_id")
    assert not_found_response.status_code == 404


# 测试删除题目端点
def test_delete_question():
    # 首先添加一个测试题目
    image_base64 = get_test_image_base64()
    question_data = {
        "question_id": "test_question_1",
        "image_base64": image_base64,
        "metadata": {"subject": "math", "grade": "3"}
    }
    client.post("/questions", json=question_data)
    
    # 删除题目
    delete_response = client.delete("/questions/test_question_1")
    assert delete_response.status_code == 204
    
    # 验证题目已删除
    get_response = client.get("/questions/test_question_1")
    assert get_response.status_code == 404
    
    # 删除不存在的题目
    not_found_response = client.delete("/questions/non_existent_id")
    assert not_found_response.status_code == 404


# 测试搜索相似题目端点
def test_search_similar_questions():
    # 首先添加两个测试题目
    image_base64 = get_test_image_base64()
    
    client.post("/questions", json={
        "question_id": "test_question_1",
        "image_base64": image_base64,
        "metadata": {"subject": "math", "grade": "3"}
    })
    
    client.post("/questions", json={
        "question_id": "test_question_2",
        "image_base64": image_base64,  # 使用相同的图片，应该搜索到高相似度
        "metadata": {"subject": "english", "grade": "4"}
    })
    
    # 搜索相似题目
    search_data = {
        "image_base64": image_base64,
        "top_k": 5,
        "search_method": "vector"
    }
    
    response = client.post("/search", json=search_data)
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert "search_time" in data
    
    # 验证结果数量
    assert len(data["results"]) >= 2  # 应该至少找到我们添加的两个题目
    
    # 测试带过滤条件的搜索
    filtered_search_data = {
        "image_base64": image_base64,
        "top_k": 5,
        "search_method": "vector",
        "filters": {"subject": "math"}
    }
    
    filtered_response = client.post("/search", json=filtered_search_data)
    filtered_data = filtered_response.json()
    
    # 验证过滤结果
    for result in filtered_data["results"]:
        assert result["metadata"]["subject"] == "math"


# 测试错误处理
def test_error_handling():
    # 测试无效的Base64编码
    invalid_data = {
        "question_id": "test_error",
        "image_base64": "invalid_base64_data",
        "metadata": {"subject": "math"}
    }
    
    response = client.post("/questions", json=invalid_data)
    assert response.status_code == 422  # 验证错误状态码
    
    # 测试无效的题目ID格式
    invalid_id_data = {
        "question_id": "" * 101,  # 超过最大长度限制
        "image_base64": get_test_image_base64(),
        "metadata": {"subject": "math"}
    }
    
    response = client.post("/questions", json=invalid_id_data)
    assert response.status_code == 422