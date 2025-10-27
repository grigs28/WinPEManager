# 统一WIM管理器

## 概述

统一WIM管理器是一个模块化的WIM文件管理解决方案，提供了完整的WIM文件挂载、卸载、ISO创建、USB制作等功能。

## 模块结构

```
core/unified_manager/
├── __init__.py              # 模块初始化
├── path_manager.py          # 路径管理模块
├── check_manager.py         # 检查机制模块
├── operation_manager.py     # 操作接口模块
├── status_manager.py        # 状态管理模块
├── wim_manager.py          # 主管理器类
└── README.md               # 说明文档
```

## 核心模块

### 1. PathManager (路径管理器)
- **功能**: 统一管理所有路径相关操作
- **主要方法**:
  - `get_mount_dir(build_dir)` - 获取统一挂载目录
  - `find_wim_files(build_dir)` - 查找所有WIM文件
  - `get_primary_wim(build_dir)` - 获取主要WIM文件

### 2. CheckManager (检查管理器)
- **功能**: 负责所有操作前的检查机制
- **主要方法**:
  - `pre_mount_checks(build_dir, wim_file_path)` - 挂载前检查
  - `pre_unmount_checks(build_dir)` - 卸载前检查
  - `pre_iso_checks(build_dir, config_manager)` - ISO创建前检查
  - `pre_usb_checks(build_dir, usb_path)` - USB制作前检查

### 3. OperationManager (操作管理器)
- **功能**: 负责所有WIM相关的操作执行
- **主要方法**:
  - `mount_wim(build_dir, wim_file_path)` - 挂载WIM
  - `unmount_wim(build_dir, commit)` - 卸载WIM
  - `create_iso(build_dir, iso_path)` - 创建ISO
  - `create_usb(build_dir, usb_path)` - 制作USB

### 4. StatusManager (状态管理器)
- **功能**: 管理所有状态查询功能
- **主要方法**:
  - `get_mount_status(build_dir)` - 获取挂载状态
  - `get_build_info(build_dir)` - 获取构建信息
  - `get_wim_summary(build_dir)` - 获取WIM摘要
  - `validate_build_structure(build_dir)` - 验证构建结构

### 5. UnifiedWIMManager (主管理器)
- **功能**: 整合所有子模块，提供统一接口
- **特性**:
  - 高级功能接口
  - 智能清理
  - 快速检查
  - 诊断信息

## 使用方法

### 基本使用

```python
from core.unified_manager import UnifiedWIMManager
from pathlib import Path

# 初始化管理器
wim_manager = UnifiedWIMManager(config_manager, adk_manager, parent_callback)

# 挂载WIM文件
build_dir = Path("path/to/build/dir")
success, message = wim_manager.mount_wim(build_dir)

# 创建ISO
success, message = wim_manager.create_iso(build_dir)

# 卸载WIM文件
success, message = wim_manager.unmount_wim(build_dir, commit=True)
```

### 高级功能

```python
# 快速挂载检查
check_result = wim_manager.quick_mount_check(build_dir)

# 智能清理
cleanup_result = wim_manager.smart_cleanup(build_dir)

# 获取诊断信息
diagnostics = wim_manager.get_diagnostics(build_dir)

# 验证构建结构
validation = wim_manager.validate_build_structure(build_dir)
```

## 主要特性

### 1. 统一路径管理
- 固定挂载目录: `build_dir/mount`
- 智能WIM文件查找
- 优先级排序 (boot.wim > winpe.wim > 其他)

### 2. 完整检查机制
- 挂载前5项检查 (目录、文件、大小、权限、空间)
- 卸载前3项检查 (状态、锁定、进程)
- ISO创建前6项检查 (挂载、文件、权限、空间)
- USB制作前4项检查 (设备、类型、空间)

### 3. 统一日志系统
- 完全使用 `utils.logger` 模块
- 支持终端、系统日志、文件日志、构建日志
- 集成构建会话管理
- 详细的命令记录和错误处理

### 4. 智能错误处理
- 多级检查机制
- 自动修复功能
- 详细的错误信息
- 异常安全处理

## 配置要求

### 依赖模块
- `utils.logger` - 日志系统
- `pathlib` - 路径处理
- `typing` - 类型提示

### 可选依赖
- `psutil` - 系统信息获取
- `win32api` - Windows API (用于USB设备检测)

## 错误处理

所有操作都返回 `(success: bool, message: str)` 元组：

```python
success, message = wim_manager.mount_wim(build_dir)
if success:
    print("操作成功:", message)
else:
    print("操作失败:", message)
```

## 日志记录

管理器使用统一的日志系统，支持多种输出：

```python
# 日志会自动输出到:
# 1. 终端控制台
# 2. 系统日志
# 3. 文件日志
# 4. 构建日志 (如果启用构建会话)
```

## 扩展性

模块化设计便于扩展：

1. **添加新的检查项**: 在 `CheckManager` 中添加新方法
2. **添加新的操作**: 在 `OperationManager` 中添加新方法
3. **添加新的状态查询**: 在 `StatusManager` 中添加新方法
4. **添加新的高级功能**: 在 `UnifiedWIMManager` 中添加新方法

## 最佳实践

1. **使用统一接口**: 优先使用 `UnifiedWIMManager` 的方法
2. **检查返回值**: 始终检查操作的返回值
3. **处理异常**: 使用 try-except 包装关键操作
4. **日志记录**: 利用内置的日志系统进行调试
5. **资源清理**: 使用 `smart_cleanup` 进行清理

## 故障排除

### 常见问题

1. **挂载失败**: 检查管理员权限和磁盘空间
2. **卸载失败**: 检查文件锁定和DISM进程
3. **ISO创建失败**: 检查Media目录完整性和输出权限
4. **USB制作失败**: 检查设备类型和可用空间

### 调试方法

```python
# 获取详细诊断信息
diagnostics = wim_manager.get_diagnostics(build_dir)
print(diagnostics)

# 验证构建结构
validation = wim_manager.validate_build_structure(build_dir)
print(validation)

# 获取系统状态
system_status = wim_manager.get_system_status()
print(system_status)
```

## 版本信息

- **版本**: 1.0.0
- **兼容性**: Python 3.7+
- **平台**: Windows (主要支持)
- **依赖**: WinPE ADK, DISM工具
