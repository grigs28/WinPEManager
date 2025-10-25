# UI模块结构说明

本目录包含WinPE制作管理器的用户界面相关代码，已按功能模块进行拆分和升级。

## 目录结构

```
ui/
├── __init__.py
├── main_window.py              # 主窗口类（重构后，284行）
├── button_styler.py           # 按钮样式管理
├── components_tree_widget.py   # 组件树形控件
├── config_dialogs.py          # 配置对话框
├── progress_dialog.py         # 进度对话框
├── main_window/              # 主窗口相关模块
│   ├── __init__.py           # 模块导出定义
│   ├── ui_creators.py        # UI创建方法（398行）
│   ├── event_handlers.py     # 事件处理方法（303行）
│   ├── build_managers.py     # 构建管理方法（485行）
│   ├── log_managers.py       # 日志管理方法（85行）
│   └── helpers.py           # 辅助方法（398行）
└── build/                    # 构建相关模块
    ├── __init__.py           # 模块导出定义
    └── build_thread.py       # WinPE构建线程（364行）
```

## 模块说明

### 主窗口模块 (main_window/)

- **ui_creators.py**: 包含所有UI组件的创建方法，如创建各个标签页、按钮、表格等
- **event_handlers.py**: 包含所有事件处理方法，如按钮点击、选择变化等
- **build_managers.py**: 包含WinPE构建相关的管理方法，如开始构建、停止构建、管理构建目录等
- **log_managers.py**: 包含日志显示和管理相关的方法
- **helpers.py**: 包含各种辅助方法，如ADK状态检查、关于对话框等

### 构建模块 (build/)

- **build_thread.py**: WinPE构建的后台线程处理，包含完整的构建流程

## 重构优势

1. **模块化**: 将原本2344行的单一文件拆分为多个功能模块
2. **可维护性**: 每个模块专注于特定功能，便于维护和调试
3. **可扩展性**: 新功能可以轻松添加到相应模块
4. **代码复用**: 模块化的代码更容易在其他地方复用
5. **团队协作**: 不同开发者可以专注于不同模块

## 使用方式

重构后的主窗口类通过组合模式使用各个功能模块：

```python
class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager):
        # 初始化功能模块
        self.ui_creators = UICreators(self)
        self.event_handlers = EventHandlers(self)
        self.build_managers = BuildManagers(self)
        self.log_managers = LogManagers(self)
        self.helpers = Helpers(self)
        
        # 委托方法调用
    def on_language_changed(self):
        self.event_handlers.on_language_changed()
```

## 兼容性

重构后的代码保持了与原有代码的完全兼容性，所有原有的功能和接口都得到保留。