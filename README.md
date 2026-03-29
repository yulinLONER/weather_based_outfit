<<<<<<< HEAD
# Weather & Outfit Suggestion App (天气与穿搭推荐系统)

根据产品需求图优化的智能穿搭推荐系统。

## 📁 项目结构 (System Architecture)

```text
Python/
├── api/                # 外部 API 集成
│   └── weather_service.py # 实时天气获取 (apihz.cn)
├── core/               # 核心业务逻辑
│   ├── integrations/   # 电商平台 API 集成 (TB, PDD, JD)
=======
# 天气与穿搭推荐系统 (Weather & Outfit Suggestion App)

这是一个根据产品需求优化的智能穿搭推荐系统，提供基于天气的个性化服装建议。

## 功能特性

- 商品标准化模型：支持材质、颜色（Hex/Pantone）、层级分类、功能标签、多维尺码及季节属性。
- 多平台 API 集成：统一集成淘宝、拼多多、京东开放平台 API，实现商品详情获取、价格监控及库存同步。
- 自动化同步：支持实时与定时同步模式，内置频率控制、异常处理及缓存优化机制。
- 数据质量监控：建立全流程同步日志与数据完整性评估体系。

## 系统要求

- Python 3.7 或更高版本
- 依赖包：requests, Flask
- 可选：Docker（用于容器化部署）

## 安装步骤

1. 克隆或下载项目代码到本地。

2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 运行测试

运行单元测试以验证系统功能：
```bash
python3 -m unittest tests.test_product_system
```

## 部署和使用

### Web 版本（推荐）

1. 启动 Web 应用：
   ```bash
   python3 run_web.py
   ```

2. 打开浏览器访问：http://127.0.0.1:5001

### 命令行版本

启动命令行界面：
```bash
python3 run_cli.py
```

### Docker 部署

1. 构建 Docker 镜像：
   ```bash
   docker build -t weather-outfit-app .
   ```

2. 启动容器：
   ```bash
   docker run -d -p 5001:5001 --name outfit-app weather-outfit-app
   ```

3. 访问系统：在浏览器中输入 http://localhost:5001

## 项目结构

```
├── api/                # 外部 API 集成
│   └── weather_service.py # 实时天气获取
├── core/               # 核心业务逻辑
│   ├── integrations/   # 电商平台 API 集成
>>>>>>> 03401c4 (Update project structure and README, add tests package)
│   ├── services/       # 商品同步与管理服务
│   └── recommender.py  # 穿搭推荐引擎逻辑
├── models/             # 商品标准化数据模型
│   └── product.py      # Product & SKU 定义与校验
├── data/               # 数据存储
│   └── wardrobe.db     # 核心商品与衣橱数据库
├── db/                 # 数据库管理
│   └── manager.py      # 商品管理系统数据库初始化
<<<<<<< HEAD
├── web/                # 用户界面 (Frontend - Web)
│   ├── app_web.py      # Flask 后端服务
│   ├── static/         # 静态资源 (CSS/JS)
│   └── templates/      # HTML 模板
├── docs/               # 交付文档 (数据库设计、接口说明)
├── tests/              # 单元测试与集成测试
├── run_cli.py          # 命令行版启动脚本
└── run_web.py          # Web 版启动脚本
```

## ✨ 核心功能 (Core Features)

1. **1.1 商品标准化模型 (Standardized Product Model)**: 深度支持材质、颜色(Hex/Pantone)、层级分类、功能标签、多维尺码及季节属性。
2. **1.2 多平台 API 集成 (E-commerce Integration)**: 统一集成淘宝、拼多多、京东开放平台 API，实现详情获取、价格监控及库存同步。
3. **1.3 自动化同步 (Auto-Sync Logic)**: 支持实时与定时同步模式，内置频率控制、异常处理及缓存优化机制。
4. **1.4 数据质量监控 (Data Quality)**: 建立全流程同步日志与数据完整性评估体系。

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

## 📝 优化记录 (Requirements Alignment)

- [x] **全局重构**: 实现了前后端分离的系统结构。
- [x] **数据流优化**: `位置请求 -> 外部 API -> 核心引擎 -> 数据库匹配 -> 结果展示`。
- [x] **风格匹配**: 在数据库和推荐算法中增加了风格权重和过滤。
- [x] **UX 提升**: 使用多标签页和响应式布局优化用户体验。
- [ ] *用户注册与提醒 (按需求暂不实现)*
=======
├── web/                # 用户界面
│   ├── app_web.py      # Flask 后端服务
│   ├── static/         # 静态资源
│   └── templates/      # HTML 模板
├── docs/               # 交付文档
├── tests/              # 单元测试与集成测试
├── run_cli.py          # 命令行版启动脚本
├── run_web.py          # Web 版启动脚本
├── requirements.txt    # 依赖包列表
├── Dockerfile          # Docker 构建文件
└── README.md           # 项目说明
```

## 数据源

- 电商平台 API：淘宝开放平台、拼多多 DDK、京东联盟 API
- 数据库：SQLite，支持复杂的商品元数据存储

## 注意事项

- 本项目包含本地 SQLite 数据库文件，容器化部署时已打包入镜像。
- 确保网络连接正常，以访问外部天气和电商 API。
- 如需自定义配置，请参考 docs/ 目录下的文档。

## 优化记录

- 全局重构：实现前后端分离结构。
- 数据流优化：位置请求 -> 外部 API -> 核心引擎 -> 数据库匹配 -> 结果展示。
- 风格匹配：在数据库和推荐算法中增加风格权重和过滤。
- 用户体验提升：使用多标签页和响应式布局。
>>>>>>> 03401c4 (Update project structure and README, add tests package)
