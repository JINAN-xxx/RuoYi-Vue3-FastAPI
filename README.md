<h1 align="center">
    <img alt="logo" src="https://oscimg.oschina.net/oscnet/up-d3d0a9303e11d522a06cd263f3079027715.png">
</h1>
<h1 align="center" style="margin: 30px 0 30px; font-weight: bold;">RuoYi-Vue3-FastAPI</h1>
<h4 align="center">基于RuoYi-Vue3+FastAPI前后端分离的快速开发框架</h4>
<p align="center">
    <a href="https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/stargazers">
        <img alt="Gitee" src="https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/badge/star.svg?theme=dark">
    </a>
    <a href="https://github.com/insistence/RuoYi-Vue3-FastAPI">
        <img alt="Github" src="https://img.shields.io/github/stars/insistence/RuoYi-Vue3-FastAPI?style=social">
    </a>
    <a href="https://github.com/insistence/RuoYi-Vue3-FastAPI/actions?query=branch%3Amaster+event%3Apush+workflow%3A%22%22Playwright+Tests%22%22">
        <img alt="Playwright Tests" src="https://github.com/insistence/RuoYi-Vue3-FastAPI/workflows/Playwright Tests/badge.svg">
    </a>
    <a href="https://github.com/insistence/RuoYi-Vue3-FastAPI/actions?query=branch%3Amaster+event%3Apush+workflow%3A%22%22Ruff+Check%22%22">
        <img alt="Ruff Check" src="https://github.com/insistence/RuoYi-Vue3-FastAPI/workflows/Ruff Check/badge.svg">
    </a>
    <a href="https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI">
        <img alt="project version" src="https://img.shields.io/badge/version-1.9.0-brightgreen.svg">
    </a>
    <a href="https://github.com/astral-sh/ruff">
        <img alt="Ruff" src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json">
    </a>
    <a href="https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI/blob/master/LICENSE">
        <img alt="LICENSE" src="https://img.shields.io/github/license/mashape/apistatus.svg">
    </a>
    <img alt="node version" src="https://img.shields.io/badge/node-≥18-blue">
    <img alt="python version" src="https://img.shields.io/badge/python-≥3.10-blue">
    <img alt="mysql version" src="https://img.shields.io/badge/MySQL-≥5.7-blue">
    <img alt="redis version" src="https://img.shields.io/badge/redis-≥6.2-blue">
</p>

## 平台简介

RuoYi-Vue3-FastAPI是一套全部开源的快速开发平台，毫无保留给个人及企业免费使用。

本仓库基于开源项目 <u>[insistence/RuoYi-Vue3-FastAPI](https://github.com/insistence/RuoYi-Vue3-FastAPI.git)</u> 进行二次开发与业务改造，在保留原有后台管理、权限控制、代码生成、AI模型管理与AI对话等基础能力的同时，重点补充了知识库能力。

* 前端采用Vue3、Element Plus，基于<u>[RuoYi-Vue3](https://github.com/insistence/RuoYi-Vue3-FastAPI.git)</u>前端项目修改。
* 移动端采用uni-app、Vue3、Vite，内置tailwindcss，基于<u>[RuoYi-App](https://github.com/yangzongzhuan/RuoYi-App)</u>项目修改。
* 后端采用FastAPI、sqlalchemy、MySQL（PostgreSQL）、Redis、OAuth2 & Jwt。
* 权限认证使用OAuth2 & Jwt，支持多终端认证系统。
* 支持加载动态权限菜单，多方式轻松权限控制。
* 特别鸣谢：<u>[RuoYi-Vue3](https://github.com/yangzongzhuan/RuoYi-Vue3)</u>、<u>[RuoYi-App](https://github.com/yangzongzhuan/RuoYi-App)</u>

## 本仓库改造说明

相较于原始项目，本仓库主要围绕智能协作与知识增强场景进行了扩展，当前重点改造内容如下：

* 新增知识库管理模块，支持知识文档上传、列表查看、删除、状态跟踪与权限隔离。
* 新增知识库向量化能力，支持文档切片、Embedding、Milvus 向量索引与相似度检索。
* 新增 AI 对话与知识库联动能力，可在对话时选择启用知识库，将检索结果作为上下文注入模型回答流程。
* 支持企业、部门、个人三级知识范围隔离，便于在组织内部进行精细化知识权限控制。
* 对 AI 管理、知识库、对话界面进行了中文化与交互体验优化，更适合实际业务场景落地。

## 内置功能

1. 用户管理：用户是系统操作者，该功能主要完成系统用户配置。
2. 角色管理：角色菜单权限分配、设置角色按机构进行数据范围权限划分。
3. 菜单管理：配置系统菜单，操作权限，按钮权限标识等。
4. 部门管理：配置系统组织机构（公司、部门、小组）。
5. 岗位管理：配置系统用户所属担任职务。
6. 字典管理：对系统中经常使用的一些较为固定的数据进行维护。
7. 参数管理：对系统动态配置常用参数。
8. 通知公告：系统通知公告信息发布维护。
9. 操作日志：系统正常操作日志记录和查询；系统异常信息日志记录和查询。
10. 登录日志：系统登录日志记录查询包含登录异常。
11. 在线用户：当前系统中活跃用户状态监控。
12. 定时任务：在线（添加、修改、删除）任务调度包含执行结果日志。
13. 服务监控：监视当前系统CPU、内存、磁盘、堆栈等相关信息。
14. 缓存监控：对系统的缓存信息查询，命令统计等。
15. 在线构建器：拖动表单元素生成相应的HTML代码。
16. 系统接口：根据业务代码自动生成相关的api接口文档。
17. 代码生成：配置数据库表信息一键生成前后端代码（python、sql、vue、js），支持下载。
18. AI管理：提供AI模型管理和AI对话功能。
19. 知识库管理：提供知识文档上传、向量索引、权限隔离、检索增强与对话联动能力。

## 代码结构说明

```text
RuoYi-Vue3-FastAPI
├── ruoyi-fastapi-backend        # FastAPI 后端
│   ├── app.py                   # 后端启动入口
│   ├── server.py                # FastAPI 应用工厂与生命周期管理
│   ├── config/                  # 环境、数据库、Redis、调度器等配置
│   ├── common/                  # 通用依赖、切面、路由、上下文、响应模型
│   ├── middlewares/             # 中间件
│   ├── module_admin/            # 系统管理模块
│   ├── module_ai/               # AI 模型管理、AI 对话
│   ├── module_knowledge/        # 知识库管理、隔离规则、向量索引
│   ├── module_generator/        # 代码生成模块
│   ├── module_monitor/          # 服务监控、缓存监控等
│   ├── module_task/             # 定时任务
│   ├── sql/                     # 初始化 SQL 脚本
│   └── utils/                   # 日志、上传、分页、通用工具类
├── ruoyi-fastapi-frontend       # Vue3 + Element Plus 管理后台
│   ├── src/api/                 # 前端接口封装
│   ├── src/views/               # 页面视图
│   ├── src/router/              # 静态路由配置
│   ├── src/store/               # Pinia 状态管理
│   ├── src/permission.js        # 动态路由与权限控制入口
│   └── vite.config.js           # 前端开发代理与构建配置
├── ruoyi-fastapi-app            # uni-app 移动端
│   ├── src/pages/               # 页面目录
│   ├── src/pages.json           # 路由配置
│   └── src/main.ts              # 移动端入口
├── ruoyi-fastapi-test           # Playwright / Pytest 自动化测试
├── docker-compose.my.yml        # MySQL 版本 Docker Compose 编排
├── docker-compose.pg.yml        # PostgreSQL 版本 Docker Compose 编排
└── README.md                    # 项目说明文档
```

### 后端模块组织

后端采用分模块设计，每个业务模块基本遵循如下目录结构：

```text
module_xxx
├── controller/   # 路由层，负责接收请求与返回响应
├── service/      # 业务层，负责核心业务逻辑
├── dao/          # 数据访问层，负责数据库操作
└── entity/
    ├── do/       # 数据库实体对象（Data Object）
    └── vo/       # 请求/响应模型对象（View Object）
```

其中：

* `common/router.py` 会自动扫描各模块下的 `controller` 并注册路由。
* `config/get_db.py` 会在启动时初始化数据库连接和表结构。
* `common/aspect/` 提供权限认证、数据权限、数据库会话等通用依赖。

### 前端模块组织

前端基于 RuoYi-Vue3 改造，主要遵循以下约定：

* `src/views` 存放页面组件，菜单中的 `component` 字段会映射到这里的页面文件。
* `src/api` 按业务模块封装请求方法，与后端接口一一对应。
* `src/store/modules/permission.js` 负责把后端返回的菜单树转换为前端动态路由。
* `src/permission.js` 是登录后动态加载菜单和路由的入口。

### 当前仓库包含的主要子系统

* `module_admin`：用户、角色、菜单、部门、岗位、字典、参数、日志等基础系统能力。
* `module_ai`：AI 模型管理、AI 对话、会话配置等。
* `module_knowledge`：知识库文档管理、企业/部门/个人隔离、Milvus 向量索引。
* `module_generator`：代码生成与模板输出。
* `module_task`：定时任务与任务日志。

## 环境说明

项目按前后端分别使用环境文件，不同运行方式会读取不同的 `.env` 配置。

### 后端环境文件

后端目录：`ruoyi-fastapi-backend`

* `.env.dev`：本地开发环境，默认通过 `python3 app.py --env=dev` 加载。
* `.env.prod`：生产环境，通常通过 `python3 app.py --env=prod` 加载。
* `.env.dockermy`：MySQL Docker 部署环境，适合配合 `docker-compose.my.yml` 使用。

后端核心环境项包括：

* `APP_HOST`、`APP_PORT`、`APP_ROOT_PATH`：服务监听地址、端口和代理根路径。
* `DB_*`：数据库连接配置。
* `REDIS_*`：Redis 连接配置。
* `JWT_*`：登录认证与令牌配置。
* `KNOWLEDGE_*`：知识库 Milvus、Embedding、切片相关配置。

说明：

* 本地开发建议 `APP_RELOAD = true`，方便热更新。
* 服务器部署建议关闭 `APP_RELOAD` 和 `DB_ECHO`，避免重复重载和大量 SQL 日志。

### 前端环境文件

前端目录：`ruoyi-fastapi-frontend`

* `.env.development`：本地开发环境。
* `.env.staging`：测试环境构建配置。
* `.env.production`：生产环境构建配置。
* `.env.docker`：Docker 部署环境配置。

前端核心环境项主要包括：

* `VITE_APP_BASE_API`：后端接口基础路径。
* `VITE_APP_ENV`：当前构建环境标识。

说明：

* 本地开发时，前端实际通过 `vite.config.js` 中的 `proxy` 转发到后端。
* 如果后端端口有调整，例如从 `9099` 改到 `9100`，需要同步修改前端代理配置。

### 当前项目常见运行组合

* 本地开发：
  * 后端使用 `ruoyi-fastapi-backend/.env.dev`
  * 前端使用 `ruoyi-fastapi-frontend/.env.development`
* Docker MySQL 部署：
  * 后端使用 `ruoyi-fastapi-backend/.env.dockermy`
  * 前端使用 `ruoyi-fastapi-frontend/.env.docker`
* 测试/预发布构建：
  * 前端常用 `ruoyi-fastapi-frontend/.env.staging`

## 依赖说明

### 后端依赖

后端依赖文件位于 `ruoyi-fastapi-backend` 目录：

* `requirements.txt`：MySQL 版本默认依赖
* `requirements-pg.txt`：PostgreSQL 版本依赖

安装方式：

```bash
cd ruoyi-fastapi-backend

# MySQL 版本
pip3 install -r requirements.txt

# PostgreSQL 版本
pip3 install -r requirements-pg.txt
```

后端依赖主要分为几类：

* Web 框架：`fastapi`、`uvicorn`
* 数据库：`SQLAlchemy`、`asyncmy`、`PyMySQL`
* 缓存与任务：`redis`、`APScheduler`
* AI 能力：`agno`、`openai`、`anthropic`、`ollama`、`groq` 等
* 知识库能力：`pymilvus`、`python-docx`、`pypdf`

说明：

* 如果只是基础后台运行，安装 `requirements.txt` 即可。
* 如果需要使用知识库真实索引能力，必须确保 `pymilvus`、`python-docx`、`pypdf` 已正确安装。
* 如果运行环境切换了虚拟环境，需要确认 `pip install` 和 `python3 app.py` 使用的是同一个解释器。

### 前端依赖

前端依赖文件位于 `ruoyi-fastapi-frontend` 目录，使用 `package.json` 管理。

安装方式：

```bash
cd ruoyi-fastapi-frontend
npm install
```

或：

```bash
cd ruoyi-fastapi-frontend
yarn
```

前端运行依赖主要包括：

* `vue`、`vue-router`
* `pinia`
* `element-plus`
* `vite`
* 以及若依前端所需的图标、请求、富文本、工具库等

### 移动端依赖

移动端依赖文件位于 `ruoyi-fastapi-app` 目录，推荐使用 `pnpm`：

```bash
cd ruoyi-fastapi-app
pnpm install
```

主要依赖包括：

* `uni-app`
* `vue3`
* `vite`
* `tailwindcss`

## 项目开发及发布相关

### 开发

```bash
# 克隆项目
git clone https://gitee.com/insistence2022/RuoYi-Vue3-FastAPI.git

# 进入项目根目录
cd RuoYi-Vue3-FastAPI
```

#### 前端

```bash
# 进入前端目录
cd ruoyi-fastapi-frontend

# 安装依赖
npm install 或 yarn --registry=https://registry.npmmirror.com

# 建议不要直接使用 cnpm 安装依赖，会有各种诡异的 bug。可以通过如下操作解决 npm 下载速度慢的问题
npm install --registry=https://registry.npmmirror.com

# 启动服务
npm run dev 或 yarn dev
```

#### 移动端

```bash
# 进入移动端目录
cd ruoyi-fastapi-app

# 安装依赖
npm install -g pnpm
pnpm install

# 启动 H5
pnpm dev:h5

# 启动微信小程序
pnpm dev:mp-weixin
```

移动端详细文档请参考：[ruoyi-fastapi-app/README.md](./ruoyi-fastapi-app/README.md)

#### 后端

```bash
# 进入后端目录
cd ruoyi-fastapi-backend

# 如果使用的是MySQL数据库，请执行以下命令安装项目依赖环境
pip3 install -r requirements.txt
# 如果使用的是PostgreSQL数据库，请执行以下命令安装项目依赖环境
pip3 install -r requirements-pg.txt

# 配置环境
在.env.dev文件中配置开发环境的数据库和redis

# 运行sql文件
1.新建数据库ruoyi-fastapi(默认，可修改)
2.如果使用的是MySQL数据库，使用命令或数据库连接工具运行sql文件夹下的ruoyi-fastapi.sql；如果使用的是PostgreSQL数据库，使用命令或数据库连接工具运行sql文件夹下的ruoyi-fastapi-pg.sql

# 运行后端
python3 app.py --env=dev
```

#### 访问

```bash
# 默认账号密码
账号：admin
密码：admin123

# 浏览器访问
地址：http://localhost:80
```

### 发布

#### 前端

```bash
# 构建测试环境
npm run build:stage 或 yarn build:stage

# 构建生产环境
npm run build:prod 或 yarn build:prod
```

#### 后端

```bash
# 配置环境
在.env.prod文件中配置生产环境的数据库和redis

# 运行后端
python3 app.py --env=prod
```

### Docker Compose部署方式

> ⚠️ **警告：** 默认未做数据持久化配置，请注意数据备份或自行配置持久化

#### MySQL版本

```bash
docker compose -f docker-compose.my.yml up -d --build
```

#### PostgreSQL版本

```bash
docker compose -f docker-compose.pg.yml up -d --build
```
