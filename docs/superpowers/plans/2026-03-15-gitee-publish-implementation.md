# 自动发布到 Gitee Releases 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 build.sh 打包成功后，增加发布到 Gitee Releases 的功能

**Architecture:** 在 build.sh 中添加发布函数，打包成功后询问用户确认后调用

**Tech Stack:** Bash + curl + Gitee API v5

---

## 文件结构

- **修改**: `build.sh` - 添加发布函数并调用

---

## Task 1: 修改 build.sh 添加发布功能

**Files:**
- Modify: `build.sh`

- [ ] **Step 1: 在 build.sh 末尾添加发布函数**

在 `fi` 之前（打包成功后）添加：

```bash
# ============================================
# 发布到 Gitee Releases 函数
# ============================================

publish_to_gitee() {
    local version="$1"
    local token=""

    # 读取 .env 文件中的 token
    if [ -f ".env" ]; then
        token=$(grep "GITEE_PERSONAL_ACCESS_TOKEN" .env | cut -d'=' -f2)
    fi

    # 检查 token
    if [ -z "$token" ]; then
        echo -e "${YELLOW}未配置 GITEE_PERSONAL_ACCESS_TOKEN，跳过发布${NC}"
        echo "请在 .env 文件中添加: GITEE_PERSONAL_ACCESS_TOKEN=your_token"
        return 1
    fi

    echo -e "${YELLOW}准备发布 v${version} 到 Gitee Releases...${NC}"

    # 询问用户确认
    read -p "是否发布到 Gitee？[y/n]: " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "已取消发布"
        return 0
    fi

    local owner="degao"
    local repo="parental-control"
    local api_url="https://gitee.com/api/v5/repos/${owner}/${repo}"

    # 1. 创建 Release
    echo -e "${YELLOW}创建 Release...${NC}"
    local release_response
    release_response=$(curl -s -X POST "${api_url}/releases" \
        -H "Authorization: token ${token}" \
        -H "Content-Type: application/json" \
        -d "{\"tag_name\": \"v${version}\", \"target_commitish\": \"master\", \"name\": \"v${version}\"}")

    # 检查是否创建成功（返回包含 id 表示成功）
    local release_id
    release_id=$(echo "$release_response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

    if [ -z "$release_id" ]; then
        # 可能已存在，尝试获取现有的 release_id
        echo -e "${YELLOW}Release 可能已存在，尝试获取...${NC}"
        release_id=$(curl -s "${api_url}/releases/tags/v${version}" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    fi

    if [ -z "$release_id" ]; then
        echo -e "${RED}创建 Release 失败: ${release_response}${NC}"
        return 1
    fi

    echo -e "${GREEN}Release 创建成功，ID: ${release_id}${NC}"

    # 2. 上传 exe 资产
    echo -e "${YELLOW}上传 ParentControl.exe...${NC}"
    local upload_response
    upload_response=$(curl -s -X POST "${api_url}/releases/${release_id}/attach_files" \
        -H "Authorization: token ${token}" \
        -F "file=@dist/ParentControl.exe")

    # 检查上传结果
    if echo "$upload_response" | grep -q '"browser_download_url"'; then
        local download_url
        download_url=$(echo "$upload_response" | grep -o '"browser_download_url":"[^"]*"' | cut -d'"' -f4)
        echo -e "${GREEN}✓ 发布成功！${NC}"
        echo "下载链接: ${download_url}"
    else
        echo -e "${RED}上传失败: ${upload_response}${NC}"
        return 1
    fi

    return 0
}
```

- [ ] **Step 2: 在打包成功后调用发布函数**

在 `echo "版本号已写入: dist/version.txt"` 之后，`echo -e "${GREEN}✓ 打包成功..."` 之前添加：

```bash
    # 发布到 Gitee
    publish_to_gitee "$NEW_VERSION"
```

- [ ] **Step 3: 验证脚本语法**

```bash
bash -n /d/Code/parental-control/build.sh
```
Expected: 无错误输出

- [ ] **Step 4: Commit**

```bash
git add build.sh
git commit -m "feat: 打包后支持发布到 Gitee Releases"
```

---

## 执行顺序

1. Task 1: 修改 build.sh
