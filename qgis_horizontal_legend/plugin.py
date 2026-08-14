# -*- coding: utf-8 -*-
"""Horizontal Legend plugin for QGIS Print Layout."""

import os
import weakref

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QApplication, QInputDialog, QMessageBox, QToolBar
from qgis.core import QgsLayoutItemLegend


class HorizontalLegendPlugin:
    """Add a horizontal-legend command to QGIS and Print Layout designers."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.icon_path = os.path.join(self.plugin_dir, "icon.svg")
        self.main_action = None
        self._designer_actions = weakref.WeakKeyDictionary()

    def tr(self, message):
        return QCoreApplication.translate("HorizontalLegend", message)

    def initGui(self):
        self.main_action = QAction(
            QIcon(self.icon_path), self.tr("Horizontal Legend"), self.iface.mainWindow()
        )
        self.main_action.setToolTip(
            self.tr("Create a horizontal legend from the selected Print Layout legend")
        )
        self.main_action.triggered.connect(self.run_from_active_designer)
        self.iface.addPluginToMenu(self.tr("&Horizontal Legend"), self.main_action)
        self.iface.addToolBarIcon(self.main_action)

        try:
            self.iface.layoutDesignerOpened.connect(self._on_layout_designer_opened)
        except Exception:
            pass

        try:
            for designer in self.iface.openLayoutDesigners():
                self._install_in_designer(designer)
        except Exception:
            pass

    def unload(self):
        try:
            self.iface.layoutDesignerOpened.disconnect(self._on_layout_designer_opened)
        except Exception:
            pass

        if self.main_action:
            self.iface.removePluginMenu(self.tr("&Horizontal Legend"), self.main_action)
            self.iface.removeToolBarIcon(self.main_action)
            self.main_action.deleteLater()
            self.main_action = None

        for designer, action in list(self._designer_actions.items()):
            self._remove_from_designer(designer, action)
        self._designer_actions.clear()

    def _on_layout_designer_opened(self, designer):
        self._install_in_designer(designer)

    def _designer_window(self, designer):
        """Return the QMainWindow backing a QgsLayoutDesignerInterface."""
        for attr in ("window", "designerWindow"):
            try:
                obj = getattr(designer, attr)
                window = obj() if callable(obj) else obj
                if window:
                    return window
            except Exception:
                continue
        return None

    def _install_in_designer(self, designer):
        """Put the Horizontal Legend icon inside the Print Layout UI."""
        if designer is None or designer in self._designer_actions:
            return

        window = self._designer_window(designer)
        if window is None:
            return

        action = QAction(QIcon(self.icon_path), self.tr("Horizontal Legend"), window)
        action.setObjectName("HorizontalLegendLayoutAction")
        action.setToolTip(self.tr("Arrange the selected legend horizontally"))
        action.triggered.connect(lambda _checked=False, d=designer: self.run(d))

        toolbar = None
        for name in (
            "mLayoutToolbar",
            "mToolsToolbar",
            "mActionsToolbar",
            "LayoutToolbar",
            "ToolsToolbar",
        ):
            toolbar = window.findChild(QToolBar, name)
            if toolbar is not None:
                break

        # Object names vary by QGIS release. If no preferred toolbar is found,
        # use the first visible layout toolbar so the icon still appears.
        if toolbar is None:
            toolbars = window.findChildren(QToolBar)
            visible = [tb for tb in toolbars if tb.isVisible()]
            toolbar = visible[0] if visible else (toolbars[0] if toolbars else None)

        if toolbar is not None:
            toolbar.addAction(action)

        # Also expose the same action through a dedicated Print Layout menu.
        try:
            menu_bar = window.menuBar()
            plugin_menu = None
            for candidate in menu_bar.actions():
                menu = candidate.menu()
                if menu and menu.objectName() == "HorizontalLegendMenu":
                    plugin_menu = menu
                    break
            if plugin_menu is None:
                plugin_menu = menu_bar.addMenu(self.tr("Horizontal Legend"))
                plugin_menu.setObjectName("HorizontalLegendMenu")
            plugin_menu.addAction(action)
        except Exception:
            pass

        self._designer_actions[designer] = action

    def _remove_from_designer(self, designer, action):
        window = self._designer_window(designer)
        if window is not None:
            try:
                for toolbar in window.findChildren(QToolBar):
                    toolbar.removeAction(action)
            except Exception:
                pass
            try:
                for menu_action in window.menuBar().actions():
                    menu = menu_action.menu()
                    if menu:
                        menu.removeAction(action)
            except Exception:
                pass
        try:
            action.deleteLater()
        except Exception:
            pass

    def _active_designer(self):
        try:
            designers = self.iface.openLayoutDesigners()
        except Exception:
            designers = []
        if not designers:
            return None

        active_window = QApplication.activeWindow()
        for designer in designers:
            if self._designer_window(designer) is active_window:
                return designer
        return designers[-1]

    def run_from_active_designer(self):
        designer = self._active_designer()
        if designer is None:
            QMessageBox.information(
                self.iface.mainWindow(),
                self.tr("Horizontal Legend"),
                self.tr("Open a Print Layout first, select a legend, then run Horizontal Legend."),
            )
            return
        self.run(designer)

    def _selected_legend(self, designer):
        try:
            layout = designer.layout()
            selected = layout.selectedLayoutItems() if layout else []
        except Exception:
            selected = []
        for item in selected:
            if isinstance(item, QgsLayoutItemLegend):
                return item
        return None

    def _suggest_columns(self, legend):
        """Estimate columns from the number of rendered legend nodes."""
        try:
            model = legend.model()
            root = model.rootGroup()
            count = 0
            for layer_node in root.children():
                try:
                    nodes = model.layerLegendNodes(layer_node)
                    count += max(1, len(nodes))
                except Exception:
                    count += 1
            return max(1, min(count, 12))
        except Exception:
            return 4

    def run(self, designer):
        legend = self._selected_legend(designer)
        parent = self._designer_window(designer) or self.iface.mainWindow()

        if legend is None:
            QMessageBox.warning(
                parent,
                self.tr("Horizontal Legend"),
                self.tr("Select a Legend item in the Print Layout, then click the Horizontal Legend icon."),
            )
            return

        columns, ok = QInputDialog.getInt(
            parent,
            self.tr("Horizontal Legend"),
            self.tr("Number of horizontal columns:"),
            self._suggest_columns(legend),
            1,
            50,
            1,
        )
        if not ok:
            return

        command_started = False
        try:
            legend.beginCommand(self.tr("Create horizontal legend"))
            command_started = True
        except Exception:
            pass

        try:
            legend.setColumnCount(columns)
            legend.setSplitLayer(True)
            legend.setEqualColumnWidth(False)
            legend.setColumnSpace(3.0)
            legend.setBoxSpace(1.0)

            try:
                legend.adjustBoxSize()
            except Exception:
                pass

            legend.update()
            try:
                designer.layout().refresh()
            except Exception:
                pass

            if command_started:
                legend.endCommand()

            QMessageBox.information(
                parent,
                self.tr("Horizontal Legend"),
                self.tr("Horizontal legend applied. Fine-tune spacing and symbols in Item Properties if needed."),
            )
        except Exception as exc:
            if command_started:
                try:
                    legend.cancelCommand()
                except Exception:
                    pass
            QMessageBox.critical(
                parent,
                self.tr("Horizontal Legend"),
                self.tr("Could not update the legend:\n{}").format(str(exc)),
            )
