# 新闻订阅工具 (News Selector)

基于Inoreader API的新闻订阅和管理工具，帮助用户获取和管理最新的新闻推送。同时支持自定义RSS订阅功能，无需依赖第三方API。

## 功能特性

### Inoreader集成
- 🔐 OAuth2认证登录
- 📰 获取订阅源列表
- 📖 获取最新文章
- 🔍 文章详情查看和搜索
- ⭐ 星标文章管理
- 📊 统计信息显示

### 自定义RSS订阅 🆕
- 📡 直接添加RSS/Atom订阅源
- 🏷️ 按分类管理订阅源
- 🔄 自动刷新和手动刷新
- 📱 本地存储，无需网络API
- 🎯 文章过滤和搜索

### 界面功能
- 💻 友好的命令行界面
- 🖥️ 直观的图形用户界面
- 📑 多标签页设计

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置相关参数：

```bash
cp .env.example .env
```

### 3. 运行程序

#### 命令行界面
```bash
python main.py --help
```

#### 图形界面
```bash
python gui.py
```

## 使用指南

### 首次使用

1. **登录认证**
   ```bash
   python main.py login
   ```
   这将打开浏览器进行OAuth2认证，按照提示完成登录。

   **重要说明**:
   - 应用会启动本地服务器监听认证回调
   - 浏览器会自动打开Inoreader授权页面
   - 完成登录和授权后会自动返回应用
   - 整个过程是自动的，无需手动操作

2. **查看登录状态**
   ```bash
   python main.py status
   ```

### 主要功能

#### 获取最新新闻
```bash
# 获取最新20篇文章
python main.py news

# 获取最新50篇文章
python main.py news -c 50

# 仅显示未读文章
python main.py news -u

# 获取最近6小时内的文章
python main.py news -h 6
```

#### 查看订阅源
```bash
# 显示所有订阅源
python main.py feeds

# 显示订阅源及未读数量
python main.py feeds -u
```

#### 获取特定订阅源的文章
```bash
# 搜索并选择订阅源
python main.py feed "技术"

# 仅显示未读文章
python main.py feed "新闻" -u
```

#### 搜索文章
```bash
# 搜索包含关键词的文章
python main.py search "人工智能"

# 在更大范围内搜索
python main.py search "技术" -c 100
```

#### 查看星标文章
```bash
python main.py starred
```

#### 查看统计信息
```bash
python main.py stats
```

#### 登出
```bash
python main.py logout
```

### 图形界面使用

#### 启动GUI
```bash
python gui.py
```

#### 主要功能
1. **登录认证**: 通过菜单栏 "文件" -> "登录" 进行OAuth2认证
2. **订阅源管理**: 左侧面板显示所有订阅源，支持搜索和查看未读数量
3. **文章浏览**: 右侧显示文章列表，支持按状态过滤（全部/未读/星标）
4. **文章详情**: 双击文章查看详细内容，支持打开原文链接
5. **搜索功能**: 支持搜索订阅源和文章内容
6. **星标管理**: 可以给文章添加或移除星标
7. **统计信息**: 通过菜单栏 "查看" -> "显示统计" 查看详细统计

#### 界面说明
- **左侧面板**: 订阅源管理，包含两个标签页
  - **Inoreader订阅**: 显示Inoreader订阅源列表和未读数量
  - **自定义RSS**: RSS订阅源管理界面
- **右侧面板**: 统一的文章显示区域
  - **文章列表**: 显示选中订阅源的文章，支持过滤和搜索
  - **文章详情**: 显示完整的文章内容
- **智能文章处理**:
  - RSS文章双击时可选择打开原文或查看详情
  - Inoreader文章双击直接查看详情
- **状态栏**: 显示当前操作状态和提示信息

### 自定义RSS订阅使用

#### 快速开始
1. 启动GUI: `python gui.py`
2. 在左侧"订阅源管理"区域，点击"自定义RSS"标签页
3. 点击"添加RSS"按钮
4. 输入RSS URL（如：`https://feeds.bbci.co.uk/news/rss.xml`）
5. 设置分类（可选）
6. 点击确定

#### 主要功能
1. **添加订阅源**: 支持RSS/Atom格式，自动验证URL有效性
2. **分类管理**: 按分类组织订阅源，便于管理
3. **刷新控制**: 支持单个刷新和批量刷新
4. **文章过滤**: 按分类、时间、已读状态过滤文章
5. **本地存储**: 订阅配置保存在本地，无需网络API

#### 主要特性
1. **统一的文章管理**: RSS文章和Inoreader文章共享同一个文章列表
2. **智能文章处理**: 自动识别文章类型，提供相应的操作选项
3. **简化的界面**: 减少重复元素，提供更清晰的功能分区
4. **一致的用户体验**: 统一的过滤、搜索和操作方式

详细使用说明请参考：
- [自定义RSS功能指南](docs/custom_rss_guide.md)
- [统一界面设计指南](docs/unified_interface_guide.md)

## 项目结构

```
news_selector/
├── docs/                    # 文档
├── src/                     # 源代码
│   ├── config/              # 配置模块
│   ├── api/                 # API接口模块
│   ├── models/              # 数据模型
│   ├── services/            # 业务逻辑
│   ├── cli/                 # 命令行界面
│   └── gui/                 # 图形用户界面
├── tests/                   # 测试
├── main.py                  # 命令行启动脚本
├── gui.py                   # GUI启动脚本
├── .env.example             # 环境变量示例
├── requirements.txt         # 依赖包
└── README.md               # 项目说明
```

## 开发

### 运行测试

```bash
pytest
```

### 代码格式化

```bash
black src/ tests/
```

### 类型检查

```bash
mypy src/
```

## 故障排除

### 登录问题

### 登录问题排查

#### 1. 重定向URI配置
**最重要**: 确保在Inoreader开发者门户中正确配置重定向URI：
- 访问: https://www.inoreader.com/developers/
- 在应用设置中添加重定向URI: `http://localhost:8080`

#### 2. 端口检查
```bash
# 检查端口8080是否可用
python check_port.py
```

#### 3. 完整诊断
```bash
# 运行完整的登录诊断
python debug_login.py
```

#### 4. 测试登录
```bash
# 测试认证流程
python test_auth.py

# 测试认证实例共享
python test_auth_sharing.py

# 测试GUI认证功能
python test_gui_auth.py

# 测试文章解析功能
python test_article_parsing.py
```

#### 5. 常见问题
- **端口被占用**: 关闭占用8080端口的程序
- **防火墙阻止**: 允许Python程序监听端口
- **重定向URI不匹配**: 检查Inoreader中的配置
- **网络问题**: 确保能访问inoreader.com

### 其他常见问题

- **网络连接**: 确保能正常访问 inoreader.com
- **依赖安装**: 运行 `pip install -r requirements.txt`
- **Python版本**: 需要 Python 3.8 或更高版本

## 许可证

MIT License
