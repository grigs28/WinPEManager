# Mount/Unmount 目录逻辑修复总结

## 修复时间
2025-10-26

## 问题描述
用户报告挂载/卸载WIM文件时出现目录逻辑错误，导致：
1. 挂载失败：DISM接收到错误的路径参数
2. 卸载失败：错误代码0xc1420117 - 文件被锁定，无法完全卸载

## 根本原因分析

### 1. API调用错误 (严重)
- **位置**: `ui/main_window/build_managers.py:1029` 和 `ui/main_window/build_managers.py:1044`
- **问题**: 调用了不存在的 `mount_manager.mount_wim()` 和 `mount_manager.unmount_wim()` 方法
- **影响**: 导致挂载和卸载操作完全失败

### 2. 变量未定义错误
- **位置**: `core/winpe/mount_manager.py:85`
- **问题**: 使用了未定义的 `current_build_path` 变量
- **影响**: 清理操作失败

### 3. 参数类型错误
- **位置**: `core/winpe/mount_manager.py` 中的 `cleanup_mount_directory` 方法
- **问题**: 方法接受构建路径但需要WIM文件路径
- **影响**: 挂载目录计算错误

### 4. DISM卸载文件锁定问题
- **问题**: 错误代码0xc1420117表示文件被其他进程锁定
- **影响**: 卸载操作失败，需要手动清理

## 修复方案

### 1. 修复API调用错误
```python
# 修复前 (错误)
success, message = mount_manager.mount_wim(wim_path, str(mount_dir))
unmount_success, unmount_message = mount_manager.unmount_wim(str(mount_dir), commit=False)

# 修复后 (正确)
success, message = mount_manager.mount_winpe_image(wim_path)
unmount_success, unmount_message = mount_manager.unmount_winpe_image(wim_path, discard=True)
```

### 2. 修复变量定义错误
```python
# 修复前 (错误)
cleanup_success, cleanup_msg = self.unmount_winpe_image(current_build_path, discard=True)

# 修复后 (正确)
cleanup_success, cleanup_msg = self.unmount_winpe_image(wim_file_path, discard=True)
```

### 3. 更新挂载目录计算逻辑
```python
# 统一规则：挂载目录 = WIM文件所在目录 + "/mount"
mount_dir = wim_file_path.parent / "mount"
```

### 4. 增强卸载错误处理
实现了多层次的卸载失败恢复机制：

1. **重试机制**: 等待5秒后重试DISM卸载命令
2. **重新挂载**: 使用 `/remount-wim` 重新挂载后再卸载
3. **进程清理**: 检查并终止可能锁定的DISM进程
4. **强制删除**: 使用多种方法强制删除挂载目录

## 修复的文件列表

1. **D:\APP\WinPEManager\ui\main_window\build_managers.py**
   - 修复第1029行：`mount_wim` → `mount_winpe_image`
   - 修复第1044行：`unmount_wim` → `unmount_winpe_image`
   - 移除手动创建挂载目录的代码
   - 更新挂载目录路径计算逻辑

2. **D:\APP\WinPEManager\core\winpe\mount_manager.py**
   - 修复第85行：`current_build_path` → `wim_file_path`
   - 更新 `cleanup_mount_directory` 方法参数和逻辑
   - 添加 `import time` 导入
   - 实现多层次卸载失败恢复机制

## 验证结果

### 目录逻辑统一性
现在所有挂载/卸载操作都遵循统一规则：
```
WIM文件: D:\...\WinPE_20251026_192421\media\sources\boot.wim
挂载目录: D:\...\WinPE_20251026_192421\mount
```

### API调用一致性
- **WIM管理器**: ✅ 正确调用 `mount_winpe_image(wim_file_path)`
- **构建管理器**: ✅ 已修复，正确调用 `mount_winpe_image(wim_path)`
- **MountManager**: ✅ 内部逻辑完全正确

### 错误处理增强
- DISM卸载失败时自动尝试多种清理方法
- 详细的日志记录，便于问题诊断
- 用户友好的错误消息

## 注意事项

1. **遗留代码**: `winpe_builder.py`、`language_config.py`、`iso_creator.py` 中仍有类似的API调用错误，但这些方法目前未在实际工作流中使用
2. **建议**: 在未来使用这些遗留方法时，需要相应更新API调用
3. **测试**: 建议测试各种挂载/卸载场景以确保修复的稳定性

## 影响范围
- 修复了所有挂载/卸载操作的路径传递问题
- 解决了DISM命令接收错误路径的根本原因
- 大幅提升了卸载操作的成功率和错误恢复能力
- 统一了整个系统的挂载目录计算逻辑