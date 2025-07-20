# 火山引擎401错误解决方案

## 错误现象

```
AI evaluation failed for article: AI API request failed after 3 attempts: 401 Client Error: Unauthorized for url: https://ark.cn-beijing.volces.com/api/v3/chat/completions
```

## 问题原因

401错误通常由以下原因导致：

1. **API密钥无效或格式错误**
2. **Endpoint ID配置错误**
3. **账户余额不足**
4. **API密钥权限不足**

## 解决步骤

### 步骤1: 检查当前配置

运行配置检查脚本：
```bash
python scripts/check_volcengine_config.py
```

### 步骤2: 获取正确的配置信息

1. 登录 [火山引擎控制台](https://console.volcengine.com/)
2. 进入"豆包大模型"服务
3. 获取以下信息：

#### API密钥
- 位置：控制台 → API密钥管理
- 格式：`sk-xxxxxxxxxxxxxxxxxx`
- 示例：`sk-abc123def456ghi789`

#### Endpoint ID
- 位置：控制台 → 推理接入点
- 格式：`ep-yyyymmdd-xxxxxx`
- 示例：`ep-20241219105016-8xqzm`

### 步骤3: 修复配置

#### 方法1: 使用修复脚本（推荐）
```bash
python scripts/fix_volcengine_config.py
```

#### 方法2: 手动修改配置文件
编辑 `config/agents/火山引擎.json`：

```json
{
  "config_name": "火山引擎",
  "api_config": {
    "api_key": "sk-your-real-api-key-here",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model_name": "ep-your-endpoint-id-here",
    "provider": "volcengine"
  }
}
```

#### 方法3: 通过GUI配置
1. 打开应用程序
2. 点击"AI配置"
3. 选择"火山引擎"配置
4. 更新API密钥和模型名称(Endpoint ID)
5. 保存配置

### 步骤4: 验证配置

再次运行检查脚本：
```bash
python scripts/check_volcengine_config.py
```

应该看到：
```
✅ API密钥格式正确: sk-abc123d...
✅ Endpoint ID格式正确: ep-20241219105016-8xqzm
✅ API连接成功
🎉 所有检查通过！火山引擎配置正常。
```

## 常见问题

### Q1: API密钥格式错误
**现象**: `API密钥格式可能不正确`
**解决**: 确保API密钥以`sk-`开头

### Q2: Endpoint ID格式错误
**现象**: `Endpoint ID格式可能不正确`
**解决**: 确保使用正确的Endpoint ID，格式为`ep-yyyymmdd-xxxxxx`

### Q3: 账户余额不足
**现象**: API返回余额不足错误
**解决**: 在火山引擎控制台充值

### Q4: 权限不足
**现象**: API返回权限错误
**解决**: 确保API密钥有调用豆包大模型的权限

## 配置模板

### 完整配置示例
```json
{
  "config_name": "火山引擎",
  "created_at": "2024-12-19T10:50:16.000000",
  "updated_at": "2024-12-19T10:50:16.000000",
  "api_config": {
    "name": "火山引擎平台",
    "description": "火山引擎豆包大模型服务，支持Doubao等模型",
    "api_key": "sk-your-api-key-here",
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model_name": "ep-your-endpoint-id-here",
    "temperature": 0.3,
    "max_tokens": 2000,
    "timeout": 90,
    "retry_times": 3,
    "retry_delay": 1,
    "headers": {},
    "proxy": "",
    "verify_ssl": true,
    "provider": "volcengine"
  },
  "prompt_config": {
    "name": "火山引擎科技政策评估",
    "description": "适用于火山引擎豆包模型的科技政策评估提示词",
    "version": "1.0",
    "system_prompt": "你是上海市科委的专业顾问，具有深厚的科技政策背景和丰富的行业经验。请严格按照要求的JSON格式返回结果。"
  },
  "is_active": true,
  "is_default": false
}
```

## 环境变量配置

也可以通过环境变量设置：
```bash
export VOLCENGINE_API_KEY=sk-your-api-key-here
```

## 测试命令

配置完成后，可以通过以下命令测试：
```bash
# 检查配置
python scripts/check_volcengine_config.py

# 运行AI筛选测试
python main.py filter-news --filter-type ai --max-results 5
```

## 获取帮助

如果仍然遇到问题：

1. 检查火山引擎控制台的服务状态
2. 确认账户余额和权限
3. 查看详细的错误日志
4. 联系火山引擎技术支持

## 相关文档

- [火山引擎集成指南](volcengine_integration_guide.md)
- [火山引擎官方文档](https://www.volcengine.com/docs/82379)
- [豆包大模型API文档](https://www.volcengine.com/docs/82379/1099475)
