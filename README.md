# WinPE制作管理程序

一个基于PyQt5的图形化Windows PE环境创建和管理工具，提供直观的界面来定制和构建个性化的WinPE系统。

## 主要功能

### 🏗️ 核心功能
- **图形化界面**：基于PyQt5的现代化中文界面
- **ADK集成**：自动检测和配置Windows ADK环境
- **组件管理**：可视化选择和管理WinPE组件
- **驱动集成**：支持自定义驱动程序包集成
- **构建工作流**：完整的WinPE构建和定制流程
- **实时进度**：构建过程进度显示和日志记录

### 🛠️ 高级特性
- **多构建支持**：支持多种WinPE配置模板
- **脚本定制**：支持自定义启动脚本和配置
- **配置管理**：JSON格式的配置导入导出
- **版本控制**：内置版本管理和更新日志
- **图标主题**：随机图标选择机制
- **编码支持**：完善的中文和多语言编码处理

## 项目架构

### 技术栈
- **前端界面**：PyQt5 (>=5.15.0)
- **后端逻辑**：Python 3.7+
- **系统集成**：Windows ADK/DISM API
- **配置管理**：JSON + 自定义ConfigManager
- **日志系统**：Python logging模块

### 核心模块

#### 业务逻辑层 (`core/`)
- **`adk_manager.py`**：Windows ADK检测和管理
- **`winpe_builder.py`**：WinPE构建引擎和流程控制
- **`config_manager.py`**：配置文件管理和持久化
- **`version_manager.py`**：语义化版本控制
- **`changelog_manager.py`**：变更日志管理
- **`simple_icon.py`**：图标管理和随机选择
- **`winpe_packages.py`**：WinPE组件包管理

#### 用户界面层 (`ui/`)
- **`main_window.py`**：主窗口和界面协调器
- **`components_tree_widget.py`**：组件选择树形控件
- **`config_dialogs.py`**：配置对话框集合
- **`progress_dialog.py`**：构建进度显示
- **`button_styler.py`**：3D按钮样式系统

#### 工具层 (`utils/`)
- **`logger.py`**：统一日志配置
- **`encoding.py`**：编码处理工具

## 安装和运行

### 系统要求
- **操作系统**：Windows 10/11 (x64)
- **Python**：3.7或更高版本
- **Windows ADK**：Windows Assessment and Deployment Kit
- **WinPE加载项**：ADK的WinPE组件

### 依赖安装
```bash
# 安装Python依赖
pip install -r requirements.txt
```

### 运行方式

#### 方式1：启动脚本（推荐）
```bash
python run.py
```
启动脚本会自动检查Python版本和依赖，提供自动安装选项。

#### 方式2：直接运行
```bash
python main.py
```

#### 方式3：Windows批处理
```bash
start.bat
```

## 使用流程

1. **环境检测**：程序启动时自动检测ADK安装状态
2. **项目配置**：选择WinPE模板、目标架构等
3. **组件选择**：通过树形界面选择需要的WinPE组件
4. **驱动管理**：添加需要集成的硬件驱动
5. **脚本定制**：配置启动脚本和自定义命令
6. **构建执行**：一键构建完整的WinPE环境
7. **导出输出**：生成ISO文件或可启动U盘

## 配置系统

### 配置文件结构
```
config/
├── default_config.json    # 默认配置
├── winpe_config.json      # 用户配置
└── templates/             # 预定义模板
    ├── minimal.json       # 最小化配置
    └── full_featured.json # 完整功能配置
```

### 支持的配置项
- WinPE版本和架构选择
- 组件包和语言包配置
- 驱动程序集成路径
- 自定义脚本和启动项
- 构建输出格式和位置

## 开发和构建

### 开发环境设置
```bash
# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt
```

### 测试运行
```bash
# 运行单元测试
python -m pytest tests/

# 运行特定测试
python -m pytest tests/test_version_manager.py

# 测试覆盖率
python -m pytest --cov=core tests/
```

### 代码质量目标
- **测试覆盖率**：核心模块≥80%，总体≥75%
- **编码规范**：PEP8 Python编码标准
- **文档**：完整的代码注释和API文档

## 项目目录

```
WinPEManager/
├── main.py                    # 主程序入口点
├── run.py                     # 启动脚本（含依赖检查）
├── start.bat                  # Windows批处理启动器
├── requirements.txt           # Python依赖包列表
├── core/                      # 核心业务逻辑
├── ui/                        # 用户界面组件
├── utils/                     # 通用工具模块
├── config/                    # 配置文件和模板
├── scripts/                   # WinPE自定义脚本
├── templates/                 # WinPE配置模板
├── ico/                       # 应用程序图标库
├── drivers/                   # 驱动程序存储
├── output/                    # 构建输出目录
└── logs/                      # 应用程序日志
```

## 许可证

本项目采用开源许可证，具体许可证信息请参考LICENSE文件。

## 贡献指南

欢迎提交Issue和Pull Request来改进项目。在提交代码前，请确保：

1. 代码通过所有现有测试
2. 新功能包含相应的测试用例
3. 遵循项目的编码规范
4. 提交信息清晰描述变更内容

## 技术支持

如遇到问题或需要技术支持，请：
1. 检查Windows ADK和WinPE加载项是否正确安装
2. 查看logs目录下的日志文件
3. 确认Python环境和依赖包状态
4. 提交详细的错误信息和系统环境