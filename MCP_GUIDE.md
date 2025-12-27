# Depth Pro MCP 使用指南

## 概述

Depth Pro MCP Server 提供单目深度估计功能，可通过 MCP 协议与 AI 助手集成。

## 可用工具

| 工具 | 描述 |
|------|------|
| `estimate_depth` | 估计单张图像深度 |
| `batch_estimate_depth` | 批量处理多张图像 |
| `get_gpu_status` | 获取 GPU 状态 |
| `release_gpu` | 释放 GPU 显存 |

## 配置方法

### 方法 1: Claude Desktop

将以下配置添加到 `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "depth-pro": {
      "command": "docker",
      "args": ["exec", "-i", "depth-pro", "python3", "mcp_server.py"]
    }
  }
}
```

### 方法 2: 其他 MCP 客户端

使用项目中的 `mcp_config.json` 配置文件。

## 使用示例

### 单图深度估计

```
请使用 depth-pro 工具估计 /path/to/image.jpg 的深度
```

### 批量处理

```
请批量处理以下图像的深度估计:
- /path/to/image1.jpg
- /path/to/image2.jpg
```

### 查看 GPU 状态

```
请查看 depth-pro 的 GPU 状态
```

## 输出说明

- `min_depth_m`: 最近距离（米）
- `max_depth_m`: 最远距离（米）
- `mean_depth_m`: 平均深度（米）
- `focal_length_px`: 估计焦距（像素）
- `depth_npz_path`: 深度数据文件路径
- `depth_image_path`: 深度可视化图像路径

## 前置条件

确保 depth-pro 容器正在运行:

```bash
cd /home/neo/upload/ml-depth-pro
docker compose up -d depth-pro
```

## 访问地址

- **UI 界面**: http://localhost:8500/
- **Swagger 文档**: http://localhost:8500/apidocs/
- **健康检查**: http://localhost:8500/health
