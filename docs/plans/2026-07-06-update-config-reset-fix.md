# 自动更新配置重建修复记录

## 问题

当前自动更新流程会在下次启动时生成 `update.bat`，替换 exe 并写入 `version.txt`，但不会处理旧的 `config.json`。

这会带来两个问题：

- 新版本新增的配置项需要依赖兼容补齐逻辑，旧配置可能长期保留历史运行状态。
- 如果旧配置中残留过期计时、夜间临时放行等运行态字段，更新后仍会被新版本读取。

检查更新逻辑还存在一个风险：只要 Release 中存在任意 `ParentControl.windows.*.exe` 就会被接受，没有确认 exe 文件名版本与 `tag_name` 一致。

## 处理方式

1. 将更新资产匹配从宽松前缀匹配改为精确匹配：
   - `tag_name = v1.7.18` 时只接受 `ParentControl.windows.1.7.18.exe`。
   - 如果没有匹配资产，则不下载更新。
2. 更新脚本中增加复制失败保护：
   - `copy /y ... || exit /b 1`
   - 只有 exe 替换成功后才继续后续步骤。
3. 更新成功后删除程序同目录的 `config.json`：
   - 新 exe 重启后会通过 `config.load_config()` 重新生成默认配置。

## 验证

- 新增测试覆盖 Release 中同时存在旧 exe 和新 exe 时只选择新 exe。
- 新增测试覆盖 Release 中只有错版 exe 时不下载。
- 新增测试覆盖 `update.bat` 包含删除 `config.json` 的命令。
- 运行完整 unittest、ruff 和打包验证。
