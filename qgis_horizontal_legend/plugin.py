# -*- coding: utf-8 -*-
"""Horizontal Legend plugin for QGIS Print Layout.

The plugin adds a toolbar/menu action to every QGIS Print Layout designer. It
operates on the selected QgsLayoutItemLegend and arranges legend content across
columns to create a compact horizontal legend.
"""

from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QInputDialog
from qgis.core import QgsLayoutItemLegend, QgsProject

import os
import weakref


class HorizontalLegendPlugin:
    """QGIS plugin entry point."""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.icon_path = os.path.join(self.plugin_dir, "icon.svg")
        self.main_action = None
        self._designer_actions = weakref.WeakKeyDictionary()

    def tr(self, message):
        return QCoreApplication.translate("HorizontalLegend", message)

    def initGui(self):
        """Register the main QGIS action and listen for Print Layout windows."""
        self.main_action = QAction(
            QIcon(self.icon_path),
            self.tr("Horizontal Legend"),
            self.iface.mainWindow(),
        )
        self.main_action.setToolTip(
            self.tr("Create a horizontal legend from the selected Print Layout legend")
        )
        self.main_action.triggered.connect(self.run_from_active_designer)

        self.iface.addPluginToMenu(self.tr("&Horizontal Legend"), self.main_action)
        self.iface.addToolBarIcon(self.main_action)

        # QGIS emits this whenever a Print Layout / report designer is opened.
        try:
            self.iface.layoutDesignerOpened.connect(self._on_layout_designer_opened)
        except Exception:
            pass

        # Add the action to designers which may already be open.
        try:
            for designer in self.iface.openLayoutDesigners():
                self._install_in_designer(designer)
        except Exception:
            pass

    def unload(self):
        """Remove plugin actions cleanly."""
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
        """Return the designer's QMainWindow across QGIS minor API differences."""
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
        """Add the plugin icon/action to a Print Layout designer."""
        if designer is None or designer in self._designer_actions:
            return

        window = self._designer_window(designer)
        if window is None:
            return

        action = QAction(QIcon(self.icon_path), self.tr("Horizontal Legend"), window)
        action.setObjectName("HorizontalLegendLayoutAction")
        action.setToolTip(
            self.tr("Arrange the selected legend horizontally across columns")
        )
        action.triggered.connect(lambda _checked=False, d=designer: self.run(d))

        # Add to a layout toolbar when possible. Different QGIS releases expose
        # different toolbar object names, so try the common ones first.
        toolbar = None
        for name in (
            "mLayoutToolbar",
            "mToolsToolbar",
            "mActionsToolbar",
            "LayoutToolbar",
            "ToolsToolbar",
        ):
            try:
                toolbar = window.findChild(type(self.iface.mainWindow().findChild(object)), name)
            except Exception:
                toolbar = None
            if toolbar and hasattr(toolbar, "addAction"):
                break

        # findChild typing above is not reliable in all bindings; fall back to
        # scanning QToolBar children without importing a QGIS-private class.
        if toolbar is None:
            try:
                from qgis.PyQt.QtWidgets import QToolBar
                toolbars = window.findChildren(QToolBar)
                toolbar = toolbars[0] if toolbars else None
            except Exception:
                toolbar = None

        if toolbar is not None:
            toolbar.addAction(action)

        # Also add to a menu so the command remains discoverable if a toolbar
        # configuration hides plugin actions.
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
                from qgis.PyQt.QtWidgets import QToolBar
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
        """Find the active/open Print Layout designer."""
        try:
            designers = self.iface.openLayoutDesigners()
        except Exception:
            designers = []

        if not designers:
            return None

        active_window = self.iface.mainWindow().activeWindow()
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
        """Return the selected legend item from the designer layout."""
        try:
            layout = designer.layout()
        except Exception:
            layout = None

        if layout is None:
            return None

        try:
            selected = layout.selectedLayoutItems()
        except Exception:
            selected = []

        for item in selected:
            if isinstance(item, QgsLayoutItemLegend):
                return item
        return None

    def _suggest_columns(self, legend):
        """Estimate a useful horizontal column count from the legend model."""
        try:
            model = legend.model()
            root = model.rootGroup()
            count = 0
            for layer_node in root.children():
                try:
                    layer = layer_node.layer()
                    if layer is None:
                        continue
                    nodes = model.layerLegendNodes(layer_node)
                    count += max(1, len(nodes))
                except Exception:
                    count += 1
            return max(1, min(count, 12))
        except Exception:
            return 4

    def run(self, designer):
        """Arrange the selected QgsLayoutItemLegend horizontally."""
        legend = self._selected_legend(designer)
        parent = self._designer_window(designer) or self.iface.mainWindow()

        if legend is None:
            QMessageBox.warning(
                parent,
                self.tr("Horizontal Legend"),
                self.tr(
                    "Select a Legend item in the Print Layout, then click the Horizontal Legend icon."
                ),
            )
            return

        suggested = self._suggest_columns(legend)
        columns, ok = QInputDialog.getInt(
            parent,
            self.tr("Horizontal Legend"),
            self.tr("Number of horizontal columns:"),
            suggested,
            1,
            50,
            1,
        )
        if not ok:
            return

        try:
            legend.beginCommand(self.tr("Create horizontal legend"))
        except Exception:
            pass

        try:
            legend.setColumnCount(columns)
            legend.setSplitLayer(True)
            legend.setEqualColumnWidth(False)

            # Compact defaults suited to horizontal legends. These are native
            # QgsLayoutItemLegend settings and remain editable in Item Properties.
            try:
                legend.setColumnSpace(3.0)
            except Exception:
                pass
            try:
                legend.setBoxSpace(1.0)
            except Exception:
                pass

            # Let QGIS resize the legend to its content after the column change.
            try:
                legend.adjustBoxSize()
            except Exception:
                pass

            legend.update()
            layout = legend.layout()
            if layout:
                layout.refresh()

            try:
                legend.endCommand()
            except Exception:
                pass

            QMessageBox.information(
                parent,
                self.tr("Horizontal Legend"),
                self.tr(
                    "Horizontal legend applied. You can fine-tune symbol, text, spacing, and column settings in Item Properties."
                ),
            )
        except Exception as exc:
            try:
                legend.cancelCommand()
            except Exception:
                pass
            QMessageBox.critical(
                parent,
                self.tr("Horizontal Legend"),
                self.tr("Could not update the legend:\n{}" ).format(str(exc)),
            )
