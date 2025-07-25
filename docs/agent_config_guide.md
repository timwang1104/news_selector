# AI Agent配置功能使用指南

## 概述

AI Agent配置功能为新闻订阅工具提供了灵活的AI服务配置管理，允许用户自定义API设置、提示词模板和高级参数，以优化AI筛选的效果和性能。

## 功能特性

### 🔧 API配置管理
- **多API支持**: 支持OpenAI、Claude等多种AI服务
- **灵活配置**: 自定义API Key、Base URL、模型名称等
- **参数调优**: 可调节Temperature、Max Tokens等生成参数
- **连接测试**: 内置API连接测试功能

### 📝 提示词管理
- **分层提示词**: 支持系统提示词、评估提示词、批量提示词
- **模板化**: 支持变量替换和格式化
- **版本控制**: 提示词版本管理和历史记录
- **实时编辑**: 可视化提示词编辑器

### ⚙️ 高级设置
- **网络配置**: 代理设置、SSL验证等
- **自定义请求头**: 支持添加自定义HTTP头
- **性能优化**: 超时设置、重试机制等
- **配置管理**: 多配置切换、导入导出

## 界面说明

### 配置管理区域
- **配置选择**: 下拉菜单选择当前使用的配置
- **配置信息**: 显示配置的创建时间、更新时间等信息
- **操作按钮**: 新建、复制、删除配置

### API配置标签页

#### 基础设置
| 字段 | 说明 | 示例 |
|------|------|------|
| 配置名称 | 配置的显示名称 | "OpenAI GPT-4" |
| 描述 | 配置的详细说明 | "用于生产环境的GPT-4配置" |

#### API设置
| 字段 | 说明 | 示例 |
|------|------|------|
| API Key | AI服务的API密钥 | "sk-..." |
| Base URL | API服务的基础URL | "https://api.openai.com" |
| 模型名称 | 使用的AI模型 | "gpt-4", "claude-3-sonnet" |

#### 请求参数
| 参数 | 范围 | 说明 |
|------|------|------|
| Temperature | 0.0-2.0 | 控制生成的随机性，越低越确定 |
| Max Tokens | 100-4000 | 最大生成token数量 |
| 超时时间 | 5-300秒 | API请求超时时间 |
| 重试次数 | 0-10次 | 失败时的重试次数 |

### 提示词配置标签页

#### 基础信息
- **提示词名称**: 提示词配置的名称
- **版本**: 提示词的版本号
- **描述**: 提示词的用途说明

#### 提示词内容
- **系统提示词**: 定义AI的角色和行为规范
- **评估提示词**: 单篇文章评估的指令模板
- **批量评估提示词**: 批量文章评估的指令模板

### 高级设置标签页

#### 网络设置
- **代理地址**: HTTP/HTTPS代理配置
- **SSL验证**: 是否验证SSL证书

#### 自定义请求头
- **添加请求头**: 支持添加自定义HTTP头
- **请求头列表**: 显示和管理已配置的请求头

## 使用方法

### 1. 打开配置界面

#### 方法一：菜单访问
1. 启动GUI应用：`python gui.py`
2. 点击菜单栏 **"筛选"** → **"AI Agent配置"**

#### 方法二：快捷访问
- 在筛选功能中遇到AI配置问题时，系统会提示打开配置界面

### 2. 创建新配置

#### 步骤1：点击"新建配置"
- 系统会创建一个基础配置模板

#### 步骤2：配置API设置
1. 填写配置名称和描述
2. 输入API Key（必需）
3. 设置Base URL（可选，默认使用官方API）
4. 选择AI模型
5. 调整请求参数

#### 步骤3：配置提示词
1. 编写系统提示词，定义AI角色
2. 设计评估提示词模板
3. 配置批量评估指令

#### 步骤4：高级设置（可选）
1. 配置网络代理
2. 添加自定义请求头
3. 调整性能参数

#### 步骤5：测试和保存
1. 点击"测试连接"验证配置
2. 点击"保存"保存配置

### 3. 管理现有配置

#### 切换配置
- 在配置选择下拉菜单中选择不同的配置

#### 复制配置
- 选择要复制的配置
- 点击"复制配置"创建副本
- 修改副本的设置

#### 删除配置
- 选择要删除的配置
- 点击"删除配置"
- 确认删除操作

## 配置示例

### OpenAI GPT-4配置
```
配置名称: OpenAI GPT-4 生产环境
API Key: sk-your-api-key-here
Base URL: https://api.openai.com
模型名称: gpt-4
Temperature: 0.3
Max Tokens: 1000

系统提示词:
你是上海市科委的专业顾问，专门负责评估科技新闻对政策制定的价值。
你具有深厚的科技政策背景和丰富的行业经验。

评估提示词:
请评估以下科技新闻文章：
标题：{title}
摘要：{summary}
内容：{content_preview}

从政策相关性、创新影响、实用性三个维度评分...
```

### Claude配置
```
配置名称: Claude-3 Sonnet
API Key: your-claude-api-key
Base URL: https://api.anthropic.com
模型名称: claude-3-sonnet-20240229
Temperature: 0.2
Max Tokens: 1500

系统提示词:
You are a technology policy advisor for Shanghai Science and Technology Commission...
```

### 自定义API配置
```
配置名称: 自定义AI服务
API Key: custom-api-key
Base URL: https://your-custom-api.com
模型名称: custom-model-v1
代理地址: http://proxy.company.com:8080
自定义请求头:
  Authorization: Bearer custom-token
  X-Custom-Header: custom-value
```

## 提示词模板变量

### 可用变量
- `{title}`: 文章标题
- `{summary}`: 文章摘要
- `{content_preview}`: 文章内容预览
- `{articles_info}`: 批量文章信息（仅批量模板）

### 模板示例
```
请评估以下文章对科技政策的价值：

标题：{title}
摘要：{summary}
内容：{content_preview}

评估维度：
1. 政策相关性 (0-10分)
2. 创新影响 (0-10分)
3. 实用性 (0-10分)

返回JSON格式：
{
  "relevance_score": 分数,
  "innovation_impact": 分数,
  "practicality": 分数,
  "total_score": 总分,
  "reasoning": "评估理由",
  "confidence": 置信度
}
```

## 最佳实践

### API配置优化
1. **选择合适的模型**: GPT-4精度高但成本高，GPT-3.5性价比好
2. **调节Temperature**: 评估任务建议0.2-0.4，创意任务可用0.6-0.8
3. **设置合理的Token限制**: 避免过长响应，控制成本
4. **配置重试机制**: 提高服务可靠性

### 提示词设计
1. **明确角色定位**: 在系统提示词中明确AI的专业背景
2. **结构化指令**: 使用清晰的步骤和格式要求
3. **提供示例**: 在提示词中包含期望的输出示例
4. **版本管理**: 记录提示词的修改历史和效果

### 性能优化
1. **批量处理**: 对大量文章使用批量评估提示词
2. **缓存策略**: 启用结果缓存减少重复请求
3. **网络优化**: 配置代理和超时参数
4. **监控指标**: 定期查看性能指标和成功率

## 故障排除

### 常见问题

#### Q: API连接测试失败
A: 检查以下项目：
- API Key是否正确
- Base URL是否可访问
- 网络连接是否正常
- 代理设置是否正确

#### Q: AI评估结果不理想
A: 优化建议：
- 调整提示词的具体性和明确性
- 修改Temperature参数
- 增加评估示例
- 检查模型选择是否合适

#### Q: 配置保存失败
A: 可能原因：
- 配置目录权限不足
- 磁盘空间不足
- 配置名称包含特殊字符

#### Q: 提示词变量不生效
A: 检查事项：
- 变量名称是否正确
- 大括号格式是否正确
- 文章数据是否完整

### 调试技巧
1. **使用测试连接**: 验证API配置的正确性
2. **查看日志**: 检查控制台输出的错误信息
3. **简化提示词**: 从简单的提示词开始测试
4. **对比配置**: 与工作正常的配置进行对比

## 安全注意事项

### API Key安全
- 不要在提示词中包含敏感信息
- 定期更换API Key
- 使用环境变量存储敏感配置
- 限制API Key的权限范围

### 数据隐私
- 了解AI服务的数据处理政策
- 避免发送敏感或机密信息
- 考虑使用本地部署的AI服务
- 定期清理缓存数据

## 技术说明

### 配置存储
- 配置文件存储在 `config/agents/` 目录
- 使用JSON格式保存配置
- 支持配置的导入和导出
- 自动备份重要配置

### 集成方式
- AI客户端自动加载当前配置
- 支持运行时配置切换
- 配置变更立即生效
- 向后兼容旧版本配置
