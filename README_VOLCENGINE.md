# 火山引擎集成说明

## 快速开始

### 1. 获取配置信息

从 [火山引擎控制台](https://console.volcengine.com/) 获取：
- **API密钥**: 以`sk-`开头的字符串
- **Endpoint ID**: 以`ep-`开头的字符串

### 2. 配置方法

#### 方法A: 使用配置脚本（推荐）
```bash
python scripts/fix_volcengine_config.py
```

#### 方法B: 环境变量
```bash
export VOLCENGINE_API_KEY=sk-your-api-key-here
```

#### 方法C: GUI配置
1. 打开应用 → AI配置
2. 点击"加载火山引擎预设"
3. 输入API密钥和Endpoint ID

### 3. 验证配置
```bash
python scripts/check_volcengine_config.py
```

### 4. 开始使用
```bash
python main.py filter-news --filter-type ai --max-results 20
```

## 解决401错误

如果遇到401错误：
```
AI evaluation failed: 401 Client Error: Unauthorized
```

**解决步骤**:
1. 运行 `python scripts/check_volcengine_config.py`
2. 检查API密钥格式（必须以`sk-`开头）
3. 检查Endpoint ID格式（必须以`ep-`开头）
4. 确认账户余额充足
5. 运行 `python scripts/fix_volcengine_config.py` 重新配置

## 支持的模型

| 模型系列 | Endpoint示例 | 适用场景 |
|---------|-------------|----------|
| Doubao-Pro | ep-20241219105016-8xqzm | 高质量文本理解 |
| Doubao-Lite | ep-20241219105016-xxxxx | 快速响应场景 |

## 配置文件位置

- 配置文件: `config/agents/火山引擎.json`
- 检查脚本: `scripts/check_volcengine_config.py`
- 修复脚本: `scripts/fix_volcengine_config.py`

## 相关文档

- [详细集成指南](docs/volcengine_integration_guide.md)
- [401错误解决方案](docs/volcengine_401_fix.md)
- [使用示例](examples/volcengine_usage_example.py)

## 技术支持

遇到问题时：
1. 查看错误日志
2. 运行配置检查脚本
3. 参考故障排除文档
4. 联系技术支持
