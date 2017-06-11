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

exit(0)
class GaugeFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, 'Gauge Example', size=(350, 150))
        panel = wx.Panel(self, -1)
        self.fool = 0
        self.gspeed = 100
        self.gauge = wx.Gauge(panel, -1, 50, (20, 50), (250, 25))
        # self.timer = wx.Timer(self)
        # self.timer.Start(self.gspeed)
        self.gauge.Pulse()
        # self.Bind(wx.EVT_TIMER, self.TimerHandler)

    def __del__(self):
        self.timer.Stop()

    def TimerHandler(self, event):
        self.fool = self.fool + 1
        if self.fool == 20:
            self.fool = 0
            self.gspeed = self.gspeed - 20
            if self.gspeed <= 0:
                self.timer.Stop()
                self.ShowMessage()
                self.Close()
            else:
                self.timer.Start(self.gspeed)
        self.gauge.Pulse()

    def ShowMessage(self):
        wx.MessageBox('Loading Completed', 'Info', wx.OK | wx.ICON_INFORMATION)


app = wx.PySimpleApp()
GaugeFrame().Show()
app.MainLoop()
