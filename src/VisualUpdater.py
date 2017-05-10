"""

User interface for configuring and running the HydroShare update utility

"""

__title__ = 'Visual H20 Utility'

import wx
from VisualUpdater.VisualH20MainWindow import VisualH2OWindow

if __name__ == "__main__":
    app = wx.App()
    frame = VisualH2OWindow(None, -1, __title__)
    app.MainLoop()
