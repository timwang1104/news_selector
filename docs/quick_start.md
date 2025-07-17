# 快速开始指南

## 安装和配置

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）
```bash
cp .env.example .env
# 编辑 .env 文件，修改配置参数（如果需要）
```

### 3. 首次登录
```bash
python main.py login
```
按照提示在浏览器中完成OAuth2认证。

## 基本使用

### 查看帮助
```bash
python main.py --help
```

### 获取最新新闻
```bash
# 获取最新20篇文章
python main.py news

# 获取最新50篇未读文章
python main.py news -c 50 -u
```

### 查看订阅源
```bash
# 显示所有订阅源及未读数量
python main.py feeds -u
```

### 搜索文章
```bash
python main.py search "人工智能"
```

### 查看统计信息
```bash
python main.py stats
```

## 常见问题

### Q: 登录失败怎么办？
A: 请检查网络连接，确保能访问Inoreader网站。登录流程说明：
1. 浏览器会打开Inoreader授权页面
2. 完成登录和授权后，页面会显示一个授权码
3. 复制该授权码并粘贴到应用中
4. 如果问题持续，请尝试重新登录：
```bash
python main.py logout
python main.py login
```

### Q: 如何获取特定订阅源的文章？
A: 使用feed命令搜索订阅源：
```bash
python main.py feed "订阅源名称"
```

### Q: 如何查看星标文章？
A: 使用starred命令：
```bash
python main.py starred
```

### Q: 如何限制获取的文章数量？
A: 使用-c参数：
```bash
python main.py news -c 10  # 获取10篇文章
```

### Q: 如何只看未读文章？
A: 使用-u参数：
```bash
python main.py news -u  # 只显示未读文章
```

## 高级用法

### 获取特定时间范围的文章
```bash
# 获取最近6小时内的文章
python main.py news -h 6
```

### 在特定订阅源中搜索
```bash
# 先获取订阅源的文章，然后搜索
python main.py feed "技术博客"
python main.py search "Python"
```

### 查看详细统计信息
```bash
python main.py stats
```

## 故障排除

### 认证问题
如果遇到认证相关的错误：
1. 检查网络连接
2. 确认Inoreader账号状态正常
3. 重新登录：`python main.py logout && python main.py login`

### API调用失败
如果API调用失败：
1. 检查网络连接
2. 确认API密钥配置正确
3. 检查是否超过API调用限制

### 依赖问题
如果遇到依赖相关的错误：
```bash
pip install --upgrade -r requirements.txt
```

## 开发和测试

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
