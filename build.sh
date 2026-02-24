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