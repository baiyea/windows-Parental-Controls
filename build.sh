#!/bin/bash

YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}开始打包家长控制程序（含系统托盘）...${NC}"

# 检查 uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}错误: 未找到 uv${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}安装依赖: pystray, pillow, pyinstaller...${NC}"
uv add pystray pillow pyinstaller -v

# 清理
rm -rf build dist *.spec

# 打包（包含隐藏导入）
echo -e "${YELLOW}打包中...${NC}"
uv run pyinstaller \
    --onefile \
    --noconsole \
    --name ParentControl \
    --hidden-import=pystray \
    --hidden-import=PIL \
    --hidden-import=PIL._imagingtk \
    --hidden-import=PIL._tkinter_finder \
    --clean \
    parent_control.py

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 打包成功: dist/ParentControl.exe${NC}"
    echo ""
    echo "功能说明:"
    echo "  • 系统托盘显示剩余时间"
    echo "  • 右键菜单: 立即锁屏 / 修改密码 / 退出"
    echo "  • 每30分钟强制休息30分钟"
    echo ""
    echo "安装开机启动:"
    echo "  ./dist/ParentControl.exe --install"
else
    echo -e "${RED}✗ 打包失败${NC}"
    exit 1
fi