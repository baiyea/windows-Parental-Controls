#!/bin/bash

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

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
        -d "{\"tag_name\": \"v${version}\", \"target_commitish\": \"master\", \"name\": \"v${version}\", \"body\": \"v${version}\"}")

    # 检查是否创建成功（返回包含 id 表示成功）
    local release_id
    release_id=$(echo "$release_response" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)

    if [ -z "$release_id" ]; then
        # 可能已存在，尝试获取现有的 release_id
        echo -e "${YELLOW}Release 可能已存在，尝试获取...${NC}"
        release_id=$(curl -s "${api_url}/releases/latest?tag_name=v${version}" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
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

echo -e "${YELLOW}开始打包家长控制程序（含系统托盘）...${NC}"

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}错误: 未找到 uv${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}安装依赖: pystray, pillow, pyinstaller, plyer...${NC}"
uv add pystray pillow pyinstaller plyer -v

# 清理
rm -rf build dist *.spec

# 打包（包含音频文件、utils模块和隐藏导入）
echo -e "${YELLOW}打包中...${NC}"
uv run pyinstaller \
    --onefile \
    --noconsole \
    --name ParentControl \
    --add-data "doc/audio:audio" \
    --hidden-import=pystray \
    --hidden-import=PIL \
    --hidden-import=PIL._imagingtk \
    --hidden-import=PIL._tkinter_finder \
    --hidden-import=plyer.platforms.win.notification \
    --hidden-import=utils \
    --hidden-import=utils.logger \
    --clean \
    main.py

if [ $? -eq 0 ]; then
    # 递增版本号
    VERSION_FILE="pyproject.toml"
    # 提取当前版本号
    CURRENT_VERSION=$(grep -oP 'version = "\K[0-9.]+' "$VERSION_FILE")
    # 提取最后两位数字
    MAJOR_VERSION=$(echo "$CURRENT_VERSION" | cut -d'.' -f1-2)
    MINOR_VERSION=$(echo "$CURRENT_VERSION" | cut -d'.' -f3)
    # 递增（处理 99 后回到 00）
    if [ "$MINOR_VERSION" -eq 99 ]; then
        NEW_MINOR="00"
    else
        NEW_MINOR=$(printf "%02d" $((10#$MINOR_VERSION + 1)))
    fi
    NEW_VERSION="${MAJOR_VERSION}.${NEW_MINOR}"
    # 写回 pyproject.toml
    sed -i "s/version = \"[0-9.]*\"/version = \"$NEW_VERSION\"/" "$VERSION_FILE"
    echo "版本号已更新: $CURRENT_VERSION -> $NEW_VERSION"

    # 写入版本号文件
    echo "$NEW_VERSION" > dist/version.txt
    echo "版本号已写入: dist/version.txt"

    # 发布到 Gitee
    publish_to_gitee "$NEW_VERSION"

    echo -e "${GREEN}✓ 打包成功: dist/ParentControl.exe${NC}"
    echo ""
    echo "功能说明:"
    echo "  • 系统托盘显示剩余时间"
    echo "  • 右键菜单: 立即锁屏 / 开机启动 / 退出"
    echo "  • 每30分钟强制休息30分钟"
    echo "  • 提前5分钟通知和声音提醒"
    echo "  • 日志自动保存到 log/年-月-日.log"
    echo ""
    echo "安装开机启动:"
    echo "  ./dist/ParentControl.exe --install"
    echo ""
    echo "日志位置:"
    echo "  exe所在目录/log/年-月-日.log"
else
    echo -e "${RED}✗ 打包失败${NC}"
    exit 1
fi