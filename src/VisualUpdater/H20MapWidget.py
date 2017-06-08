from functools import partial

import wx
import wx.grid


class H20MapWidget(wx.grid.Grid):
    def __init__(self, parent, id=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, rows=3):
        wx.grid.Grid.__init__(self, parent, id, pos=pos, size=size)

        self.CreateGrid(rows, 3)
        self.RowLabelSize = 0
        self.ColLabelSize = 20
        self.HydroShareChoices = ['Select a destination resource']
        self.SeriesNames = []

        # Grid
        self.EnableEditing(True)
        self.EnableGridLines(True)
        self.EnableDragGridSize(False)
        self.AlwaysShowScrollbars(False, True)
        self.ShowScrollbars(False, True)
        self.SetMargins(0, 0)

        # Columns
        self.EnableDragColMove(False)
        self.EnableDragColSize(True)
        self.SetColLabelSize(25)
        self.SetColLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        # Rows
        self.EnableDragRowSize(True)
        self.SetRowLabelSize(1)
        self.SetRowLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        self.SetColLabelValue(0, 'Use')
        self.SetColLabelValue(1, 'Generated CSV Filename')
        self.SetColLabelValue(2, 'Destination HydroShare Resource')

        attr_choice = wx.grid.GridCellAttr()
        editor = wx.grid.GridCellBoolEditor()
        attr_choice.SetEditor(editor)
        attr_choice.SetRenderer(wx.grid.GridCellBoolRenderer())
        self.SetColAttr(0, attr_choice)

        attr_choice = wx.grid.GridCellAttr()
        editor = wx.grid.GridCellChoiceEditor(self.HydroShareChoices, False)

        attr_choice.SetEditor(editor)
        attr_choice.SetRenderer(wx.grid.GridCellEnumRenderer())
        self.SetColAttr(2, attr_choice)

        self.SetColSize(0, 30)
        self.SetColSize(1, 350)
        self.SetColSize(2, 500)

        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_CELL_LEFT_CLICK, 1), self.onMouse)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_SELECT_CELL, 1), self.onCellSelected)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_CELL_CHANGED, 1), self.onCellModified)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_EDITOR_CREATED, 1), self.onEditorCreated)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_EDITOR_HIDDEN, 1), self.onEditorCreated)

    def setSeries(self, series_names):
        self.SeriesNames = series_names
        self._update_table()

    def _update_table(self):
        rows_added = 0
        if len(self.SeriesNames) > self.NumberRows:
            rows_added = len(self.SeriesNames) - self.NumberRows
            self.AppendRows(rows_added)
        elif len(self.SeriesNames) < self.NumberRows:
            self.DeleteRows(0, self.NumberRows - len(self.SeriesNames))
        for i in range(0, len(self.SeriesNames)):
            self.SetCellValue(i, 1, self.SeriesNames[i])

            if len(self.SeriesNames) - rows_added > 0:
                editor = self.GetCellEditor(i, 0)
                if editor.Control is not None:
                    check_item = editor.Control # type: wx.CheckBox
                    check_item.Value = True

                editor = self.GetCellEditor(i, 2)
                if editor.Control is not None:
                    choice_item = editor.Control # type: wx.Choice
                    choice_item.SetItems(self.HydroShareChoices)
                    choice_item.Select(0)


    def setHydroShareChoices(self, resource_names):
        self.HydroShareChoices = sorted(resource_names)
        self._update_table()

    def onMouse(self,evt):
        if evt.Col == 0:
            wx.CallLater(100, self.toggleCheckBox)
        evt.Skip()

    def toggleCheckBox(self):
        self.cb.Value = not self.cb.Value
        self.afterCheckBox(self.cb.Value)

    def onCellSelected(self,evt):
        if evt.Col == 0:
            wx.CallAfter(self.EnableCellEditControl)
        evt.Skip()

    def onEditorCreated(self,evt):
        try:
            if evt.Col == 0:
                self.cb = evt.Control
                self.cb.WindowStyle |= wx.WANTS_CHARS
                self.cb.Bind(wx.EVT_KEY_DOWN,self.onKeyDown)
                self.cb.Bind(wx.EVT_CHECKBOX,self.onCheckBox)
        except:
            print "Attempted to set a checkbox that isn't a checkbox"

    def onKeyDown(self,evt):
        if evt.KeyCode == wx.WXK_UP:
            if self.GridCursorRow > 0:
                self.DisableCellEditControl()
                self.MoveCursorUp(False)
        elif evt.KeyCode == wx.WXK_DOWN:
            if self.GridCursorRow < (self.NumberRows-1):
                self.DisableCellEditControl()
                self.MoveCursorDown(False)
        elif evt.KeyCode == wx.WXK_LEFT:
            if self.GridCursorCol > 0:
                self.DisableCellEditControl()
                self.MoveCursorLeft(False)
        elif evt.KeyCode == wx.WXK_RIGHT:
            if self.GridCursorCol < (self.NumberCols-1):
                self.DisableCellEditControl()
                self.MoveCursorRight(False)
        else:
            evt.Skip()

    def onCheckBox(self,evt):
        self.afterCheckBox(evt.IsChecked())

    def afterCheckBox(self,isChecked):
        print 'afterCheckBox',self.GridCursorRow,isChecked

    def onCellModified(self, event):
        print 'Cell value has been modified'
        event.Skip()
