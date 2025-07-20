# 火山引擎集成指南

## 概述

本指南介绍如何在新闻筛选系统中集成和使用火山引擎豆包大模型服务。火山引擎提供了高质量的中文大语言模型服务，特别适合中文内容的理解和分析。

**重要更新**: 现在使用火山引擎官方SDK `volcengine-python-sdk`，提供更稳定和标准的API调用方式。

## 功能特性

### 支持的模型

- **doubao-pro-4k**: 豆包Pro 4K上下文版本，适合短文本处理
- **doubao-pro-32k**: 豆包Pro 32K上下文版本，适合长文本处理  
- **doubao-pro-128k**: 豆包Pro 128K上下文版本，适合超长文本处理
- **doubao-lite-4k**: 豆包Lite 4K版本，响应更快，成本更低
- **doubao-lite-32k**: 豆包Lite 32K版本
- **doubao-lite-128k**: 豆包Lite 128K版本

### 核心优势

1. **中文优化**: 专门针对中文内容优化，理解能力强
2. **高性价比**: 相比国外模型，价格更优惠
3. **低延迟**: 国内部署，网络延迟低
4. **稳定性**: 企业级服务保障

## 配置步骤

### 1. 获取API密钥和Endpoint

1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 注册并完成实名认证
3. 开通豆包大模型服务
4. 创建推理接入点(Endpoint)
5. 获取以下信息：
   - **API密钥**: 形如 `sk-xxx` 的字符串
   - **Endpoint ID**: 形如 `ep-20241219105016-8xqzm` 的字符串
   - **Base URL**: 通常为 `https://ark.cn-beijing.volces.com/api/v3`

**重要提示**: 火山引擎使用Endpoint ID而不是模型名称来标识具体的模型实例。

### 2. 安装依赖

```bash
# 安装火山引擎SDK和依赖
pip install volcengine-python-sdk httpx

# 或者安装完整依赖
pip install -r requirements.txt
```

### 3. 环境变量配置

```bash
# 设置火山引擎API密钥
export VOLCENGINE_API_KEY=your_api_key_here
# 或者使用ARK_API_KEY（SDK会自动识别）
export ARK_API_KEY=your_api_key_here
```

### 3. 系统配置

#### 方法一：通过GUI配置

1. 启动应用程序
2. 打开"AI配置"对话框
3. 点击"加载火山引擎预设"按钮
4. 输入您的API密钥
5. 选择合适的模型
6. 保存配置

#### 方法二：通过配置文件

创建或编辑 `config/agents/火山引擎.json`:

```json
{
  "config_name": "火山引擎",
  "api_config": {
    "name": "火山引擎平台",
    "description": "火山引擎豆包大模型服务",
    "api_key": "sk-your-api-key-here",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model_name": "ep-20241219105016-8xqzm",
    "temperature": 0.3,
    "max_tokens": 2000,
    "timeout": 90,
    "provider": "volcengine"
  }
}
```

**配置说明**:
- `api_key`: 从火山引擎控制台获取的API密钥
- `model_name`: 使用Endpoint ID，不是模型名称
- `base_url`: 火山引擎API的基础URL

## 使用方法

### 1. 通过GUI界面

1. 在主界面选择"AI筛选"
2. 在配置中选择火山引擎配置
3. 设置筛选参数
4. 开始筛选

### 2. 通过命令行

```bash
# 设置环境变量
export VOLCENGINE_API_KEY=your_api_key

# 执行筛选
python main.py filter-news --filter-type ai --max-results 20
```

### 3. 编程接口

```python
from src.ai.factory import create_ai_client
from src.config.filter_config import AIFilterConfig
from src.config.agent_config import agent_config_manager

# 设置火山引擎配置
agent_config_manager.set_current_config("火山引擎")

# 创建客户端
config = AIFilterConfig()
client = create_ai_client(config)

# 评估文章
evaluation = client.evaluate_article(article)
print(f"评估分数: {evaluation.total_score}")
```

## 性能对比

### 响应时间对比
| 服务商 | 平均响应时间 | 并发能力 | 中文理解 |
|--------|-------------|----------|----------|
| OpenAI GPT-4 | 3-5秒 | 中等 | 良好 |
| 硅基流动 Qwen2.5 | 2-3秒 | 高 | 优秀 |
| 火山引擎 Doubao-Pro | 1-3秒 | 高 | 优秀 |
| 火山引擎 Doubao-Lite | 1-2秒 | 很高 | 良好 |

### 成本对比
| 模型 | 输入价格(元/千tokens) | 输出价格(元/千tokens) |
|------|---------------------|---------------------|
| doubao-pro-4k | 0.0008 | 0.002 |
| doubao-pro-32k | 0.0008 | 0.002 |
| doubao-lite-4k | 0.0003 | 0.0006 |

## 最佳实践

### 1. 模型选择建议

- **短新闻文章** (< 1000字): 使用 `doubao-lite-4k`
- **中等长度文章** (1000-5000字): 使用 `doubao-pro-4k`
- **长文章** (> 5000字): 使用 `doubao-pro-32k`
- **批量处理**: 优先使用 `doubao-lite` 系列

### 2. 参数调优

```python
# 推荐配置
{
    "temperature": 0.3,      # 较低温度保证结果稳定性
    "max_tokens": 2000,      # 足够的输出长度
    "timeout": 90,           # 适当的超时时间
    "retry_times": 3         # 重试次数
}
```

### 3. 错误处理

系统内置了完善的错误处理机制：

- **网络超时**: 自动重试
- **API限流**: 指数退避重试
- **解析错误**: 降级到关键词筛选
- **配额不足**: 自动切换到备用配置

## 故障排除

### 401 Unauthorized 错误

这是最常见的问题，通常由配置错误导致：

```bash
# 快速检查配置
python scripts/check_volcengine_config.py

# 修复配置
python scripts/fix_volcengine_config.py
```

**常见原因**:
1. API密钥格式错误（应以`sk-`开头）
2. Endpoint ID错误（应以`ep-`开头）
3. 账户余额不足
4. API密钥权限不足

详细解决方案请参考: [火山引擎401错误解决方案](volcengine_401_fix.md)

### 其他常见问题

1. **网络连接问题**
   - 检查网络连接
   - 确认防火墙设置
   - 尝试更换网络环境

2. **响应解析失败**
   - 检查模型输出格式
   - 调整temperature参数
   - 查看详细错误日志

3. **Endpoint不存在**
   - 确认Endpoint ID是否正确
   - 检查Endpoint是否已部署
   - 验证Endpoint状态

### 日志分析

```bash
# 查看详细日志
tail -f logs/app.log | grep volcengine

# 查看错误日志
grep ERROR logs/app.log | grep volcengine
```

## 技术支持

如遇到问题，请：

1. 查看系统日志获取详细错误信息
2. 检查网络连接和API配置
3. 参考火山引擎官方文档
4. 联系技术支持团队

## 更新日志

- **v1.0.0**: 初始版本，支持基础的文章评估功能
- **v1.1.0**: 添加批量评估支持
- **v1.2.0**: 优化错误处理和重试机制
