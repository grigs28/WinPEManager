#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinPE可选组件树形控件
提供树形结构的可选组件界面，支持选择和悬停提示
"""

from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QHeaderView, QToolTip, QAbstractItemView, QSizePolicy
)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QPainter

from core.winpe_packages import WinPEPackages


class ComponentsTreeWidget(QTreeWidget):
    """WinPE可选组件树形控件"""

    # 自定义信号
    component_selection_changed = pyqtSignal(dict)  # 组件选择变化信号

    def __init__(self, parent=None):
        super().__init__(parent)

        self.winpe_packages = WinPEPackages()
        self.category_items = {}  # 分类项目
        self.component_items = {}  # 组件项目

        self.init_ui()
        self.build_tree()

    def init_ui(self):
        """初始化界面"""
        # 设置大小策略，让控件能够占满空间
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 设置列
        self.setHeaderLabels(["可选组件", "状态", "描述"])

        # 设置列宽
        header = self.header()
        header.setStretchLastSection(True)
        header.resizeSection(0, 200)
        header.resizeSection(1, 80)

        # 设置样式
        self.setAlternatingRowColors(True)
        self.setIndentation(20)
        self.setSortingEnabled(False)  # 禁用排序，保持树形结构
        self.setRootIsDecorated(True)  # 显示树形结构装饰

        # 设置选择行为
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)

        # 连接信号
        self.itemChanged.connect(self.on_item_changed)
        self.itemEntered.connect(self.on_item_entered)

        # 启用鼠标跟踪以支持悬停提示
        self.setMouseTracking(True)

        # 设置字体
        font = QFont()
        font.setPointSize(9)
        self.setFont(font)

    def build_tree(self):
        """构建树形结构"""
        self.clear()
        self.category_items.clear()
        self.component_items.clear()

        # 获取分类和组件
        component_tree = self.winpe_packages.get_component_tree()

        # 创建主分类节点（支持分层结构）
        for main_category, sub_categories in component_tree.items():
            main_item = QTreeWidgetItem(self)
            main_item.setText(0, f"{main_category}")
            main_item.setText(2, self.get_main_category_description(main_category))

            # 设置主分类图标和样式
            main_item.setIcon(0, self.get_main_category_icon(main_category))
            font = main_item.font(0)
            font.setBold(True)
            font.setPointSize(10)
            main_item.setFont(0, font)

            # 设置主分类背景色
            main_item.setBackground(0, QColor(240, 240, 240))
            main_item.setBackground(1, QColor(240, 240, 240))
            main_item.setBackground(2, QColor(240, 240, 240))

            self.category_items[main_category] = main_item

            # 如果是分层结构，创建子分类
            if isinstance(sub_categories, dict):
                for sub_category, components in sub_categories.items():
                    sub_item = QTreeWidgetItem(main_item)
                    sub_item.setText(0, f"  {sub_category}")
                    sub_item.setText(2, f"{sub_category} - {len(components)} 个组件")

                    # 设置子分类样式
                    sub_item.setIcon(0, self.get_sub_category_icon(sub_category))
                    font = sub_item.font(0)
                    font.setBold(False)
                    font.setPointSize(9)
                    sub_item.setFont(0, font)

                    # 设置子分类背景色
                    sub_item.setBackground(0, QColor(248, 248, 248))
                    sub_item.setBackground(1, QColor(248, 248, 248))
                    sub_item.setBackground(2, QColor(248, 248, 248))

                    # 添加组件到子分类
                    for package_name in components:
                        component = self.winpe_packages.get_component_by_package_name(package_name)
                        if component:
                            self.add_component_item(sub_item, component)
            else:
                # 如果是扁平结构，直接添加组件
                for package_name in sub_categories:
                    component = self.winpe_packages.get_component_by_package_name(package_name)
                    if component:
                        self.add_component_item(main_item, component)

        # 展开所有分类
        self.expandAll()

    def add_component_item(self, parent_item, component):
        """添加组件项目"""
        item = QTreeWidgetItem(parent_item)

        # 设置组件信息
        item.setText(0, f"{component.icon} {component.name}")
        item.setText(1, "未选中")
        item.setText(2, component.description)

        # 设置复选框
        item.setCheckState(0, Qt.Unchecked)

        # 设置工具提示
        item.setToolTip(0, component.tooltip)
        item.setToolTip(1, component.tooltip)
        item.setToolTip(2, component.tooltip)

        # 存储组件对象
        item.setData(0, Qt.UserRole, component)

        self.component_items[component.package_name] = item

    def get_category_icon(self, category):
        """获取分类图标"""
        # 使用简单的颜色块作为分类图标
        colors = {
            "基础平台": "#4CAF50",
            "脚本与自动化": "#2196F3",
            ".NET Framework": "#9C27B0",
            "恢复环境": "#FF9800",
            "网络连接": "#00BCD4",
            "诊断工具": "#795548",
            "安全防护": "#F44336",
            "数据访问": "#607D8B",
            "服务器支持": "#3F51B5",
            "硬件支持": "#FF5722",
            "其他组件": "#9E9E9E"
        }

        color = colors.get(category, "#9E9E9E")
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)

        # 绘制简单的彩色圆点
        from PyQt5.QtGui import QPainter, QBrush, QColor
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        brush = QBrush(QColor(color))
        painter.setBrush(brush)
        painter.drawEllipse(2, 2, 12, 12)
        painter.end()

        return QIcon(pixmap)

    def on_item_changed(self, item, column):
        """项目变化处理"""
        if column == 0 and item.data(0, Qt.UserRole):
            component = item.data(0, Qt.UserRole)
            is_checked = item.checkState(0) == Qt.Checked

            # 更新状态文本
            item.setText(1, "已选中" if is_checked else "未选中")

            # 更新选中状态的背景色
            if is_checked:
                # 设置选中状态的背景色为浅绿色
                from PyQt5.QtGui import QColor
                light_green = QColor(144, 238, 144)  # 浅绿色
                for col in range(3):
                    item.setBackground(col, light_green)
            else:
                # 清除背景色
                for col in range(3):
                    item.setBackground(col, Qt.white)

            # 如果是分类节点，处理子节点的选择
            if not item.data(0, Qt.UserRole):  # 这是分类节点
                for i in range(item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, Qt.Checked if is_checked else Qt.Unchecked)

            # 处理依赖关系
            if is_checked:
                self.handle_dependencies(component, True)

            # 发送选择变化信号
            self.emit_selection_changed()

    def handle_dependencies(self, component, check_state):
        """处理依赖关系"""
        dependencies = component.dependencies

        for dep_package in dependencies:
            dep_item = self.component_items.get(dep_package)
            if dep_item:
                if check_state:
                    # 启用依赖项
                    dep_item.setCheckState(0, Qt.Checked)
                # 注意：取消选择时不自动取消依赖项，因为其他组件可能依赖它

    def on_item_entered(self, item, column):
        """鼠标悬停处理"""
        # 只在描述栏（第2列，索引为2）显示提示
        if column == 2:
            tooltip = item.toolTip(column)
            if tooltip:
                # 获取鼠标位置
                pos = self.mapToGlobal(self.viewport().mapFromParent(
                    self.visualItemRect(item).topLeft()
                ))
                pos.setY(pos.y() - 10)  # 向上偏移一点

                QToolTip.showText(pos, tooltip)

    def emit_selection_changed(self):
        """发送选择变化信号"""
        selected_components = self.get_selected_components()
        self.component_selection_changed.emit(selected_components)

    def get_selected_components(self) -> dict:
        """获取选中的组件"""
        selected = {}

        for package_name, item in self.component_items.items():
            if item.checkState(0) == Qt.Checked:
                component = item.data(0, Qt.UserRole)
                if component:
                    selected[package_name] = component

        return selected

    def select_components(self, package_names: list):
        """选择指定组件"""
        for package_name in package_names:
            item = self.component_items.get(package_name)
            if item:
                item.setCheckState(0, Qt.Checked)

    def unselect_components(self, package_names: list):
        """取消选择指定组件"""
        for package_name in package_names:
            item = self.component_items.get(package_name)
            if item:
                item.setCheckState(0, Qt.Unchecked)

    def select_recommended_components(self):
        """选择推荐组件"""
        recommended = self.winpe_packages.get_recommended_packages()
        self.select_components(recommended)

    def clear_selection(self):
        """清空选择"""
        for item in self.component_items.values():
            item.setCheckState(0, Qt.Unchecked)

    def search_components(self, keyword: str):
        """搜索组件"""
        # 展开所有项目以便搜索
        self.expandAll()

        # 遍历所有组件项目
        for package_name, item in self.component_items.items():
            component = item.data(0, Qt.UserRole)
            if component:
                # 检查是否匹配关键词
                match = (
                    keyword.lower() in component.name.lower() or
                    keyword.lower() in component.description.lower() or
                    keyword.lower() in component.package_name.lower()
                )

                # 高亮匹配的项目
                if match:
                    item.setBackground(0, Qt.yellow)
                    item.setBackground(1, Qt.yellow)
                    item.setBackground(2, Qt.yellow)
                    # 确保父节点展开
                    parent = item.parent()
                    if parent:
                        parent.setExpanded(True)
                else:
                    # 清除高亮
                    item.setBackground(0, Qt.white)
                    item.setBackground(1, Qt.white)
                    item.setBackground(2, Qt.white)

    def clear_search_highlight(self):
        """清除搜索高亮"""
        for item in self.component_items.values():
            item.setBackground(0, Qt.white)
            item.setBackground(1, Qt.white)
            item.setBackground(2, Qt.white)

    def get_main_category_description(self, main_category):
        """获取主分类描述"""
        descriptions = {
            "🔧 Microsoft官方组件": "Microsoft官方提供的WinPE可选组件，经过官方验证和支持",
            "📦 外部/第三方组件": "第三方开发的实用工具，常用于WinPE环境增强"
        }
        return descriptions.get(main_category, "组件分类")

    def get_main_category_icon(self, main_category):
        """获取主分类图标"""
        from PyQt5.QtGui import QPainter, QColor

        if "Microsoft官方组件" in main_category:
            color = "#4CAF50"  # 绿色代表官方
        elif "外部/第三方组件" in main_category:
            color = "#FF9800"  # 橙色代表第三方
        else:
            color = "#9E9E9E"  # 灰色代表其他

        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制圆形图标
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(2, 2, 12, 12)

        painter.end()
        return QIcon(pixmap)

    def get_sub_category_icon(self, sub_category):
        """获取子分类图标"""
        colors = {
            "文件管理工具": "#2196F3",
            "系统工具": "#4CAF50",
            "网络工具": "#00BCD4",
            "媒体工具": "#9C27B0",
            "基础平台": "#795548",
            "脚本与自动化": "#FF9800",
            ".NET Framework": "#9C27B0",
            "恢复环境": "#FF5722",
            "网络连接": "#00BCD4",
            "诊断工具": "#795548",
            "安全防护": "#F44336",
            "数据访问": "#607D8B",
            "服务器支持": "#3F51B5",
            "硬件支持": "#FF5722",
            "字体支持": "#795548"
        }

        color = colors.get(sub_category, "#9E9E9E")
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制方形图标
        painter.setBrush(QColor(color))
        painter.setPen(Qt.NoPen)
        painter.drawRect(1, 1, 10, 10)

        painter.end()
        return QIcon(pixmap)