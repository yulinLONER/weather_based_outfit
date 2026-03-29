# 天气与穿搭推荐系统 (Weather & Outfit Suggestion App)

这是一个根据产品需求优化的智能穿搭推荐系统，提供基于天气的个性化服装建议。

## ✨ 功能特性

- 🎨 **商品标准化模型**：支持材质、颜色（Hex/Pantone）、层级分类、功能标签、多维尺码及季节属性
- 🛒 **多平台 API 集成**：统一集成淘宝、拼多多、京东开放平台 API，实现商品详情获取、价格监控及库存同步
- ⚙️ **自动化同步**：支持实时与定时同步模式，内置频率控制、异常处理及缓存优化机制
- 📊 **数据质量监控**：建立全流程同步日志与数据完整性评估体系

## 📋 系统要求

- Python 3.8 或更高版本
- 依赖包：见 requirements.txt
- 可选：Docker（用于容器化部署）

## 🚀 快速开始

### 安装依赖
```bash
# 1. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 创建 .env 文件（复制 .env.example）
cp .env.example .env
# 编辑 .env 填入你的 API 密钥和配置
```

### 运行测试
```bash
python3 -m unittest tests.test_product_system
```

### 启动应用

**Web 版本（推荐）**
```bash
python3 run_web.py
# 打开浏览器访问：http://127.0.0.1:5001
```

**命令行版本**
```bash
python3 run_cli.py
```

## 🐳 Docker 部署

```bash
# 1. 构建镜像
docker build -t weather-outfit-app .

# 2. 启动容器
docker run -d -p 5001:5001 --name outfit-app weather-outfit-app

# 3. 访问系统
# 在浏览器中输入：http://localhost:5001
```

## 📁 项目结构

```
├── api/                # 外部 API 集成
│   ├── weather_service.py # 实时天气获取
│   └── ai_tools.py     # AI 处理工具
├── core/               # 核心业务逻辑
│   ├── ai_client.py    # AI 客户端
│   ├── recommender.py  # 穿搭推荐引擎
│   ├── integrations/   # 电商平台 API 集成
│   │   ├── base_client.py # 基础客户端
│   │   └── platform_clients.py # 平台客户端集成
│   └── services/       # 商品同步与管理服务
│       └── sync_service.py # 商品同步服务
├── models/             # 商品标准化数据模型
│   └── product.py      # Product & SKU 定义与校验
├── data/               # 数据存储
│   └── wardrobe.db     # 核心商品与衣橱数据库
├── db/                 # 数据库管理
│   └── manager.py      # 商品管理系统数据库初始化
├── web/                # 用户界面
│   ├── app_web.py      # Flask 后端服务
│   ├── static/         # 静态资源 (CSS/JS)
│   └── templates/      # HTML 模板
├── docs/               # 交付文档（数据库设计、接口说明）
├── tests/              # 单元测试与集成测试
│   └── test_product_system.py # 商品系统测试
├── scripts/            # 工具脚本
│   └── seed_demo_wardrobe.py # 演示数据生成脚本
├── config.py           # 配置管理模块
├── .env.example        # 环境变量模板
├── .gitignore          # Git 忽略配置
├── requirements.txt    # 依赖包列表
├── Dockerfile          # Docker 构建文件
├── run_cli.py          # 命令行版启动脚本
├── run_web.py          # Web 版启动脚本
└── README.md           # 项目说明

## 🛠️ 数据源 (Data Sources)

- **E-commerce APIs**: Taobao Open Platform, PDD DDK, JD Union API.
- **Wardrobe Database**: 升级版 SQLite，支持复杂的商品元数据存储。

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install requests Flask
```

### 2. 运行测试 (验证模型与同步逻辑)
```bash
python3 -m unittest tests/test_product_system.py
```

### 3. 运行 Web 界面
```bash
python3 run_web.py
```

#### 🌐 Web 网页版 (推荐)
```bash
python3 run_web.py
```
*启动后会自动在浏览器中打开 http://127.0.0.1:5001/*

#### ⌨️ CLI 命令行版
```bash
python3 run_cli.py
```

## 📦 容器化部署 (Docker Deployment)

为了确保在任何环境下都能一致运行，本项目支持 Docker 部署：

### 1. 构建镜像
```bash
docker build -t weather-outfit-app .
```

### 2. 启动容器
```bash
docker run -d -p 5001:5001 --name outfit-app weather-outfit-app
```

### 3. 访问系统
在浏览器中输入：`http://localhost:5001/`

---
*注：本项目包含本地 SQLite 数据库 [data/wardrobe.db](data/wardrobe.db)，容器化时已将其打包入镜像中，确保了开箱即用的体验。*

## 📝 优化记录

- [x] **全局重构**: 实现了前后端分离的系统结构
- [x] **数据流优化**: 位置请求 → 外部 API → 核心引擎 → 数据库匹配 → 结果展示
- [x] **风格匹配**: 在数据库和推荐算法中增加了风格权重和过滤
- [x] **UX 提升**: 使用多标签页和响应式布局优化用户体验
- [x] **商品标准化**: 实现了复杂的商品元数据存储模型
- [x] **多平台集成**: 统一集成了三大电商平台

## ⚙️ 配置说明

### 环境变量

复制 `.env.example` 为 `.env` 并配置：

```bash
# Flask 配置
FLASK_SECRET_KEY=your_strong_secret_key_here

# AI API 配置（可选）
AI_API_KEY=your_api_key_here
AI_API_BASE_URL=https://api.openai.com
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=30

# 数据库配置
DB_PATH=data/wardrobe.db

# 天气 API 超时设置
WEATHER_API_TIMEOUT=10
```

## 📌 注意事项

- 本项目包含本地 SQLite 数据库文件 `data/wardrobe.db`，容器化部署时已打包入镜像
- 确保网络连接正常以访问外部天气和电商 API
- 请将敏感信息（API 密钥等）存储在 `.env` 文件中，不要上传到版本控制
- 如需自定义配置，请参考 `docs/` 目录下的详细文档

## 📄 许可证

MIT License - 详见 LICENSE 文件
