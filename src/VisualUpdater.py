"""

User interface for configuring and running the HydroShare update utility

"""

import datetime
import os
import re
import smtplib
import sys
from functools import partial

__title__ = 'Visual H20 Utility'

# from VisualUpdater import HydroShareAccountDialog, VisualH20Window
import VisualUpdater

import VisualUpdater.VisualH20MainWindow
import VisualUpdater.HydroShareAccountDialog

from VisualUpdater.VisualH20MainWindow import VisualH2OWindow

import wx


if __name__ == "__main__":
    app = wx.App()
    frame = VisualH2OWindow(None, -1, __title__)
    app.MainLoop()
