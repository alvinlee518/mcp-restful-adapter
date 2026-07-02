# MCP RESTful Adapter

将 RESTful API（Swagger 2.0 / OpenAPI 3.0）自动转换为 MCP Server。每个 API 端点变成一个 MCP Tool。

## 快速开始

### 1. 在 Claude Desktop / Cursor / Claude Code 中使用

编辑配置文件（Claude Desktop: `~/Library/Application Support/Claude/claude_desktop_config.json`）：

**从 PyPI 安装（推荐）：**

```json
{
  "mcpServers": {
    "petstore": {
      "command": "uvx",
      "args": ["mcp-restful-adapter"],
      "env": {
        "API_SPEC_URL": "https://petstore3.swagger.io/api/v3/openapi.json",
        "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
        "API_TAGS": "pet,store"
      }
    }
  }
}
```

**本地开发（未发布时）：**

```json
{
  "mcpServers": {
    "petstore": {
      "command": "uv",
      "args": [
        "run",
        "--project", "/path/to/mcp-restful-adapter",
        "mcp-restful-adapter"
      ],
      "env": {
        "API_SPEC_URL": "https://petstore3.swagger.io/api/v3/openapi.json",
        "API_BASE_URL": "https://petstore3.swagger.io/api/v3",
        "API_TAGS": "pet,store"
      }
    }
  }
}
```

> 将 `/path/to/mcp-restful-adapter` 替换为本项目的实际路径。

配置完成后，Claude 就能直接调用 Petstore 的 API 了：

- `findPetsByStatus(status="available")` → 查询可用宠物
- `getPetById(petId=1)` → 查询宠物详情
- `addPet(name="Buddy", ...)` → 创建宠物

### 2. 在终端中使用

```bash
# PyPI 版本
API_SPEC_URL=https://petstore3.swagger.io/api/v3/openapi.json \
API_BASE_URL=https://petstore3.swagger.io/api/v3 \
API_TAGS=pet \
uvx mcp-restful-adapter

# 本地开发
API_SPEC_URL=https://petstore3.swagger.io/api/v3/openapi.json \
API_BASE_URL=https://petstore3.swagger.io/api/v3 \
API_TAGS=pet \
uv run mcp-restful-adapter
```

### 3. 带认证的 API

```json
{
  "mcpServers": {
    "my-api": {
      "command": "uvx",
      "args": ["mcp-restful-adapter"],
      "env": {
        "API_SPEC_URL": "https://your-api.example.com/openapi.json",
        "API_BASE_URL": "https://your-api.example.com",
        "API_HEADERS": "{\"Authorization\": \"Bearer your-bearer-token\", \"X-Tenant\": \"acme\"}"
      }
    }
  }
}
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `API_SPEC_URL` | OpenAPI/Swagger 文档地址 | **必填** |
| `API_BASE_URL` | 后端 API 地址 | **必填** |
| `API_TAGS` | Tag 白名单，逗号分隔，**OR** 逻辑（匹配任一 tag 即保留） | 全部 |
| `API_METHODS` | HTTP 方法白名单，逗号分隔 | 全部 |
| `API_PATHS` | 路径正则白名单（如 `^/api/v1/`） | 全部 |
| `API_HEADERS` | 自定义请求头（JSON 格式，含认证等） | 空 |
| `LOG_LEVEL` | 日志级别（`INFO` 记录请求 URL，`DEBUG` 记录请求头和 body） | `WARNING` |

### 过滤示例

```bash
# 只要 GET 请求
API_METHODS=GET

# 只要 pet 或 store 相关的端点
API_TAGS=pet,store

# 只要 /api/v1/ 开头的路径
API_PATHS=^/api/v1/

# 组合使用：pet tag 下的 GET 和 POST
API_TAGS=pet
API_METHODS=GET,POST
```

## 开发

```bash
uv sync                                    # 安装依赖
uv run mcp-restful-adapter                 # 运行
uv run pytest tests/ -v                    # 运行测试
uv run pytest tests/ --cov=mcp_restful_adapter  # 覆盖率
```

## 示例代码

| 文件 | 说明 |
|------|------|
| [`examples/agent_usage.py`](examples/agent_usage.py) | Agent 中使用 — 连接 MCP Server、列出 tools、调用 tools |
| [`examples/claude_desktop_config.json`](examples/claude_desktop_config.json) | Claude Desktop 配置模板 |

```bash
uv run python examples/agent_usage.py
```
