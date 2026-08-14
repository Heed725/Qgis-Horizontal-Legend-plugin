# -*- coding: utf-8 -*-
"""QGIS Horizontal Legend plugin package."""


def classFactory(iface):
    """Load the plugin class from plugin.py."""
    from .plugin import HorizontalLegendPlugin
    return HorizontalLegendPlugin(iface)
