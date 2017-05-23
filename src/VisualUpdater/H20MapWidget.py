from functools import partial

import wx
import wx.grid


class H20MapWidget(wx.grid.Grid):
    def __init__(self, parent, id=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, rows=3, columns=3):
        wx.grid.Grid.__init__(self, parent, id, pos=pos, size=size)

        self.CreateGrid(rows, columns)
        self.RowLabelSize = 0
        self.ColLabelSize = 20
        #
        # attr = wx.grid.GridCellAttr()
        # # attr.SetEditor(wx.grid.GridCellBoolEditor())
        # # attr.SetRenderer(wx.grid.GridCellBoolRenderer())
        # self.SetColAttr(1,attr)
        # self.SetColSize(1,20)

        # Grid
        self.EnableEditing(True)
        self.EnableGridLines(True)
        self.EnableDragGridSize(False)
        self.SetMargins(0, 0)

        # Columns
        self.EnableDragColMove(False)
        self.EnableDragColSize(True)
        self.SetColLabelSize(30)
        self.SetColLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        # Rows
        self.EnableDragRowSize(True)
        self.SetRowLabelSize(80)
        self.SetRowLabelAlignment(wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)

        for column in range(0, self.NumberCols):
            # self.SetColLabelValue("Label " + str(column))
            for row in range(0, self.NumberRows):

                attr = wx.grid.GridCellAttr()
                editor = wx.grid.GridCellChoiceEditor(['one', 'two', 'tree'], False)
                # editor.Ed
                attr.SetEditor(editor)
                attr.SetRenderer(wx.grid.GridCellEnumRenderer())
                # renderer = wx.grid.Render
                self.SetColAttr(column, attr)
                # self.Bind(wx.EVT_CHOICE, partial(self.toggleCheckBox, row=row, col=column), editor.GetControl())
                # self.mapping_grid.SetCellEditor(row, column, choice_editor)


        #
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_CELL_LEFT_CLICK, 1), self.onMouse)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_SELECT_CELL, 1), self.onCellSelected)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_CELL_CHANGED, 1), self.onCellModified)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_EDITOR_CREATED, 1), self.onEditorCreated)
        self.Bind(wx.PyEventBinder(wx.grid.wxEVT_GRID_EDITOR_HIDDEN, 1), self.onEditorCreated)

    def Recreate(self, new_grid):

        self.ClearGrid()

        if len(new_grid) == 0:
            return



    def onMouse(self,evt):
        cell_value = self.GetCellValue(evt.Row, evt.Col)
        table_value = self.GetTable().GetValue(evt.Row, evt.Col)
        # wx.CallLater(100, partial(self.toggleCheckBox, row=evt.Row, col=evt.Col))
        evt.Skip()

    def toggleCheckBox(self):
        # self.cb.Value = not self.cb.Value
        self.afterCheckBox()
        print "we apparently tried to toggle a box or something"

    def onCellSelected(self, evt):
        # if evt.Col == 1:
        print "onCellSelected"
        wx.CallAfter(self.EnableCellEditControl)
        evt.Skip()

    def onEditorCreated(self, evt):
        # self.cb = evt.Control
        # self.cb.WindowStyle |= wx.WANTS_CHARS
        # self.cb.WindowStyle |= wx.CB_DROPDOWN
        print "looking at editor created"

        if evt.Row >= 0 and evt.Col >= 0:
            control = self.GetCellEditor(evt.Row, evt.Col).GetControl() # type: wx.Choice
            if control is not None:
                print "ctrl: " + control.GetStringSelection()
                control.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
                control.Bind(wx.EVT_CHOICE, self.onCheckBox)
        evt.Skip()

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
        # self.afterCheckBox(evt.IsChecked())
        print "On checkbox, on prancer, on comet, on cupid!"
        print evt.GetSelection()
        print evt.GetStringSelection()

    def afterCheckBox(self, row=-1, col=-1):
        # print 'afterCheckBox',self.GridCursorRow,isChecked
        print "after checkbox"

        if row >= 0 and col >= 0:
            control = self.GetCellEditor(row, col).GetControl() # type: wx.Choice
            if control is not None:
                print "ctrl: " + control.GetStringSelection()
                # print table_value.GetStringSelection()

    def onCellModified(self, event):
        # print 'afterCheckBox',self.GridCursorRow,isChecked
        print "on cell modified"

        self.afterCheckBox(event.Row, event.Col)
        # control = event.G
        # if row > 0 and col > 0:
        # control = self.GetCellEditor(row, col).GetControl()  # type: wx.Choice
        # if control is not None:
        #     print "ctrl: " + control.GetStringSelection()
            # print table_value.GetStringSelection()
#
