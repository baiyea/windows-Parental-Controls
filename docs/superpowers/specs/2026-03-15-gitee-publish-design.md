# 自动发布到 Gitee Releases 设计

## 概述

在 build.sh 打包成功后，增加发布到 Gitee Releases 的功能。

## 需求

1. 打包成功后询问用户是否发布
2. 用户确认后自动创建 Release 并上传 exe
3. 支持从 `.env` 文件读取 Gitee Token

## 技术方案

### API 接口

| 操作 | URL | 方法 |
|------|-----|------|
| 创建 Release | `https://gitee.com/api/v5/repos/{owner}/{repo}/releases` | POST |
| 上传资产 | `https://gitee.com/api/v5/repos/{owner}/{repo}/releases/{id}/attach_files` | POST |

### 参数说明

- 创建 Release: `tag_name`, `target_commitish`, `name`, `body`
- 上传资产: `file` 字段（二进制文件）

### 配置文件

`.env` 文件中添加：
```
GITEE_PERSONAL_ACCESS_TOKEN=your_token_here
```

## 实现步骤

1. 添加发布函数 `publish_to_gitee()`
2. 打包成功后调用该函数
3. 函数读取 `.env` 中的 token
4. 询问用户确认
5. 调用 API 创建 Release
6. 调用 API 上传 exe 资产

## 错误处理

- Token 不存在：提示用户配置 .env 文件
- 网络错误：显示错误信息，跳过发布
- 上传失败：显示错误信息
