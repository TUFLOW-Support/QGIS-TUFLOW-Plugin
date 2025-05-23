"""
Module to fill the gap for QGIS versions that don't yet have Python 3.9+

Copies routines largely from the convert_tuflow_model_gis_format suite and modifies where required to
make compatible. These routines are just too useful sometimes to re-write in the plugin (so only do this as
required).

Hopefully this will not grow too big and can be deprecated (and removed) sometime in the near future (fingers crossed).
"""

import os
import re
import shutil
import sqlite3
try:
    from pathlib import Path
except ImportError:
    from pathlib_ import Path_ as Path

from osgeo import ogr, gdal, osr

from qgis.core import Qgis
from qgis.PyQt.QtCore import QVariant, QMetaType, Qt, QEvent, QItemSelectionModel, QEventLoop, QRegularExpression
from qgis.PyQt.QtWidgets import (QSizePolicy, QFrame, QAbstractItemView, QListView, QComboBox, QSlider, QToolButton,
                                 QStyle, QDateTimeEdit, QFormLayout, QDialogButtonBox, QMessageBox, QHeaderView,
                                 QDialog, QAbstractScrollArea, QAbstractSpinBox, QFileDialog, QTabWidget,
                                 QLayout)
from qgis.PyQt.QtGui import QIcon, QPalette, QFont, QImage, QKeySequence, QPainter
from qgis.PyQt.QtNetwork import QNetworkRequest

try:
    from PyQt6.QtCore import QMetaType
    is_qt6 = True
except ImportError:
    is_qt6 = False


GIS_SHP = 'Esri Shapefile'
GIS_MIF = 'Mapinfo File'
GIS_GPKG = 'GPKG'
GRID_ASC = 'AAIGrid'
GRID_FLT = 'EHdr'
GRID_GPKG = 'GPKG'
GRID_TIF = 'GTiff'
GRID_NC = 'netCDF'

# PyQt5/PyQt6 enumerators
if is_qt6:
    # data types
    QT_STRING = QMetaType.Type.QString
    QT_INT = QMetaType.Type.Int
    QT_LONG = QMetaType.Type.Long
    QT_LONG_LONG = QMetaType.Type.LongLong
    QT_FLOAT = QMetaType.Type.Float
    QT_DOUBLE = QMetaType.Type.Double

    # colours
    QT_RED = Qt.GlobalColor.red
    QT_BLUE = Qt.GlobalColor.blue
    QT_GREEN = Qt.GlobalColor.green
    QT_BLACK = Qt.GlobalColor.black
    QT_WHITE = Qt.GlobalColor.white
    QT_DARK_GREEN = Qt.GlobalColor.darkGreen
    QT_TRANSPARENT = Qt.GlobalColor.transparent
    QT_MAGENTA = Qt.GlobalColor.magenta

    # text format
    QT_RICH_TEXT = Qt.TextFormat.RichText

    # check state
    QT_CHECKED = Qt.CheckState.Checked
    QT_UNCHECKED = Qt.CheckState.Unchecked
    QT_PARTIALLY_CHECKED = Qt.CheckState.PartiallyChecked

    # orientation
    QT_HORIZONTAL = Qt.Orientation.Horizontal
    QT_VERTICAL = Qt.Orientation.Vertical

    # mouse buttons
    QT_LEFT_BUTTON = Qt.MouseButton.LeftButton
    QT_RIGHT_BUTTON = Qt.MouseButton.RightButton

    # alignment
    QT_ALIGN_LEFT = Qt.AlignmentFlag.AlignLeft
    QT_ALIGN_RIGHT = Qt.AlignmentFlag.AlignRight
    QT_ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    QT_ALIGN_TOP = Qt.AlignmentFlag.AlignTop
    QT_ALIGN_BOTTOM = Qt.AlignmentFlag.AlignBottom
    QT_ALIGN_V_CENTER = Qt.AlignmentFlag.AlignVCenter
    QT_ALIGN_H_CENTER = Qt.AlignmentFlag.AlignHCenter
    QT_ALIGN_ABSOLUTE = Qt.AlignmentFlag.AlignAbsolute
    QT_ALIGN_LEADING = Qt.AlignmentFlag.AlignLeading
    QT_ALIGN_TRAILING = Qt.AlignmentFlag.AlignTrailing

    # item data role
    QT_ITEM_DATA_EDIT_ROLE = Qt.ItemDataRole.EditRole
    QT_ITEM_DATA_DISPLAY_ROLE = Qt.ItemDataRole.DisplayRole
    QT_ITEM_DATA_DECORATION_ROLE = Qt.ItemDataRole.DecorationRole
    QT_ITEM_DATA_TOOL_TIP_ROLE = Qt.ItemDataRole.ToolTipRole
    QT_ITEM_DATA_STATUS_TIP_ROLE = Qt.ItemDataRole.StatusTipRole
    QT_ITEM_DATA_WHATS_THIS_ROLE = Qt.ItemDataRole.WhatsThisRole
    QT_ITEM_DATA_SIZE_HINT_ROLE = Qt.ItemDataRole.SizeHintRole
    QT_ITEM_DATA_FONT_ROLE = Qt.ItemDataRole.FontRole
    QT_ITEM_DATA_TEXT_ALIGNMENT_ROLE = Qt.ItemDataRole.TextAlignmentRole
    QT_ITEM_DATA_BACKGROUND_ROLE = Qt.ItemDataRole.BackgroundRole
    QT_ITEM_DATA_FOREGROUND_ROLE = Qt.ItemDataRole.ForegroundRole
    QT_ITEM_DATA_CHECK_STATE_ROLE = Qt.ItemDataRole.CheckStateRole
    QT_ITEM_DATA_INITIAL_SORT_ORDER_ROLE = Qt.ItemDataRole.InitialSortOrderRole
    QT_ITEM_DATA_ACCESSIBLE_TEXT_ROLE = Qt.ItemDataRole.AccessibleTextRole
    QT_ITEM_DATA_ACCESSIBLE_DESCRIPTION_ROLE = Qt.ItemDataRole.AccessibleDescriptionRole
    QT_ITEM_DATA_USER_ROLE = Qt.ItemDataRole.UserRole

    # item flags
    QT_ITEM_FLAG_NO_ITEM_FLAGS = Qt.ItemFlag.NoItemFlags
    QT_ITEM_FLAG_ITEM_IS_SELECTABLE = Qt.ItemFlag.ItemIsSelectable
    QT_ITEM_FLAG_ITEM_IS_EDITABLE = Qt.ItemFlag.ItemIsEditable
    QT_ITEM_FLAG_ITEM_IS_DRAG_ENABLED = Qt.ItemFlag.ItemIsDragEnabled
    QT_ITEM_FLAG_ITEM_IS_DROP_ENABLED = Qt.ItemFlag.ItemIsDropEnabled
    QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE = Qt.ItemFlag.ItemIsUserCheckable
    QT_ITEM_FLAG_ITEM_IS_ENABLED = Qt.ItemFlag.ItemIsEnabled
    QT_ITEM_FLAG_ITEM_IS_AUTO_TRISTATE = Qt.ItemFlag.ItemIsAutoTristate
    QT_ITEM_FLAG_ITEM_NEVER_HAS_CHILDREN = Qt.ItemFlag.ItemNeverHasChildren
    QT_ITEM_FLAG_ITEM_IS_USER_TRISTATE = Qt.ItemFlag.ItemIsUserTristate

    # layout direction
    QT_LAYOUT_DIRECTION_LEFT_TO_RIGHT = Qt.LayoutDirection.LeftToRight
    QT_LAYOUT_DIRECTION_RIGHT_TO_LEFT = Qt.LayoutDirection.RightToLeft
    QT_LAYOUT_DIRECTION_AUTO = Qt.LayoutDirection.LayoutDirectionAuto

    QT_LAYOUT_SET_FIXED_SIZE = QLayout.SizeConstraint.SetFixedSize

    # keys
    QT_KEY_RETURN = Qt.Key.Key_Return
    QT_KEY_ESCAPE = Qt.Key.Key_Escape
    QT_KEY_C = Qt.Key.Key_C
    QT_KEY_V = Qt.Key.Key_V
    QT_KEY_F = Qt.Key.Key_F
    QT_KEY_F3 = Qt.Key.Key_F3

    # keyboard modifiers
    QT_KEY_NO_MODIFIER = Qt.KeyboardModifier.NoModifier
    QT_KEY_MODIFIER_SHIFT = Qt.KeyboardModifier.ShiftModifier
    QT_KEY_MODIFIER_CONTROL = Qt.KeyboardModifier.ControlModifier
    QT_KEY_MODIFIER_ALT = Qt.KeyboardModifier.AltModifier

    # qkeysequence
    QT_KEY_SEQUENCE_COPY = QKeySequence.StandardKey.Copy
    QT_KEY_SEQUENCE_PASTE = QKeySequence.StandardKey.Paste
    QT_KEY_SEQUENCE_CUT = QKeySequence.StandardKey.Cut

    # context menu
    QT_CUSTOM_CONTEXT_MENU = Qt.ContextMenuPolicy.CustomContextMenu
    QT_NO_CONTEXT_MENU = Qt.ContextMenuPolicy.NoContextMenu

    # cursor
    QT_CURSOR_ARROW = Qt.CursorShape.ArrowCursor
    QT_CURSOR_UP_ARROW = Qt.CursorShape.UpArrowCursor
    QT_CURSOR_CROSS = Qt.CursorShape.CrossCursor
    QT_CURSOR_SIZE_VER = Qt.CursorShape.SizeVerCursor
    QT_CURSOR_SIZE_HOR = Qt.CursorShape.SizeHorCursor
    QT_CURSOR_SIZE_DIAG_B = Qt.CursorShape.SizeBDiagCursor
    QT_CURSOR_SIZE_DIAG_F = Qt.CursorShape.SizeFDiagCursor
    QT_CURSOR_SIZE_ALL = Qt.CursorShape.SizeAllCursor
    QT_CURSOR_WAIT = Qt.CursorShape.WaitCursor

    # case sensitivity
    QT_CASE_INSENSITIVE = Qt.CaseSensitivity.CaseInsensitive
    QT_CASE_SENSITIVE = Qt.CaseSensitivity.CaseSensitive
    QT_PATTERN_CASE_INSENSITIVE = QRegularExpression.PatternOption.CaseInsensitiveOption

    # match flags
    QT_MATCH_EXACTLY = Qt.MatchFlag.MatchExactly
    QT_MATCH_FIXED_STRING = Qt.MatchFlag.MatchFixedString
    QT_MATCH_CONTAINS = Qt.MatchFlag.MatchContains
    QT_MATCH_STARTS_WITH = Qt.MatchFlag.MatchStartsWith
    QT_MATCH_ENDS_WITH = Qt.MatchFlag.MatchEndsWith
    QT_MATCH_CASE_SENSITIVE = Qt.MatchFlag.MatchCaseSensitive
    QT_MATCH_REGULAR_EXPRESSION = Qt.MatchFlag.MatchRegularExpression
    QT_MATCH_WILDCARD = Qt.MatchFlag.MatchWildcard
    QT_MATCH_WRAP = Qt.MatchFlag.MatchWrap
    QT_MATCH_RECURSIVE = Qt.MatchFlag.MatchRecursive

    # dock widget area
    QT_DOCK_WIDGET_AREA_LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
    QT_DOCK_WIDGET_AREA_RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
    QT_DOCK_WIDGET_AREA_TOP = Qt.DockWidgetArea.TopDockWidgetArea
    QT_DOCK_WIDGET_AREA_BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
    QT_DOCK_WIDGET_AREA_ALL = Qt.DockWidgetArea.AllDockWidgetAreas
    QT_DOCK_WIDGET_AREA_NONE = Qt.DockWidgetArea.NoDockWidgetArea

    # window modality
    QT_WINDOW_MODALITY_NON_MODAL = Qt.WindowModality.NonModal
    QT_WINDOW_MODALITY_MODAL = Qt.WindowModality.WindowModal
    QT_WINDOW_MODALITY_APPLICATION_MODAL = Qt.WindowModality.ApplicationModal

    # brush style
    QT_STYLE_NO_BRUSH = Qt.BrushStyle.NoBrush
    QT_STYLE_SOLID_BRUSH = Qt.BrushStyle.SolidPattern

    # line style
    QT_DASH_LINE = Qt.PenStyle.DashLine
    QT_SOLID_LINE = Qt.PenStyle.SolidLine

    # pen style
    QT_STYLE_NO_PEN = Qt.PenStyle.NoPen
    QT_STYLE_SOLID_PEN = Qt.PenStyle.SolidLine
    QT_STYLE_DASHED_PEN = Qt.PenStyle.DashLine
    QT_STYLE_DOTTED_PEN = Qt.PenStyle.DotLine
    QT_STYLE_DASH_DOTTED_PEN = Qt.PenStyle.DashDotLine
    QT_STYLE_DASH_DOTTED_DOT_PEN = Qt.PenStyle.DashDotDotLine

    # scroll bar policy
    QT_SCROLL_BAR_AS_NEEDED = Qt.ScrollBarPolicy.ScrollBarAsNeeded
    QT_SCROLL_BAR_ALWAYS_ON = Qt.ScrollBarPolicy.ScrollBarAlwaysOn
    QT_SCROLL_BAR_ALWAYS_OFF = Qt.ScrollBarPolicy.ScrollBarAlwaysOff

    # focus policy
    QT_NO_FOCUS = Qt.FocusPolicy.NoFocus
    QT_TAB_FOCUS = Qt.FocusPolicy.TabFocus
    QT_CLICK_FOCUS = Qt.FocusPolicy.ClickFocus
    QT_STRONG_FOCUS = Qt.FocusPolicy.StrongFocus
    QT_WHEEL_FOCUS = Qt.FocusPolicy.WheelFocus

    # arrow type
    QT_ARROW_TYPE_NO_ARROW = Qt.ArrowType.NoArrow
    QT_ARROW_TYPE_UP_ARROW = Qt.ArrowType.UpArrow
    QT_ARROW_TYPE_DOWN_ARROW = Qt.ArrowType.DownArrow
    QT_ARROW_TYPE_LEFT_ARROW = Qt.ArrowType.LeftArrow
    QT_ARROW_TYPE_RIGHT_ARROW = Qt.ArrowType.RightArrow

    # elide mode
    QT_ELIDE_LEFT = Qt.TextElideMode.ElideLeft
    QT_ELIDE_RIGHT = Qt.TextElideMode.ElideRight
    QT_ELIDE_MIDDLE = Qt.TextElideMode.ElideMiddle
    QT_ELIDE_NONE = Qt.TextElideMode.ElideNone

    # bg mode
    QT_BG_TRANSPARENT = Qt.BGMode.TransparentMode
    QT_BG_OPAQUE = Qt.BGMode.OpaqueMode

    # window type
    QT_WINDOW_TYPE = Qt.WindowType.Window
    QT_DIALOG_TYPE = Qt.WindowType.Dialog

    # widget attribute
    QT_WA_DELETE_ON_CLOSE = Qt.WidgetAttribute.WA_DeleteOnClose

    # qsizepolicy
    QT_SIZE_POLICY_FIXED = QSizePolicy.Policy.Fixed
    QT_SIZE_POLICY_MINIMUM_EXPANDING = QSizePolicy.Policy.MinimumExpanding
    QT_SIZE_POLICY_EXPANDING = QSizePolicy.Policy.Expanding
    QT_SIZE_POLICY_MAXIMUM = QSizePolicy.Policy.Maximum
    QT_SIZE_POLICY_MINIMUM = QSizePolicy.Policy.Minimum
    QT_SIZE_POLICY_PREFERRED = QSizePolicy.Policy.Preferred

    # qframe
    QT_FRAME_NO_FRAME = QFrame.Shape.NoFrame
    QT_FRAME_BOX = QFrame.Shape.Box
    QT_FRAME_PANEL = QFrame.Shape.Panel
    QT_FRAME_STYLED_PANEL = QFrame.Shape.StyledPanel
    QT_FRAME_HLINE = QFrame.Shape.HLine
    QT_FRAME_VLINE = QFrame.Shape.VLine
    QT_FRAME_WIN_PANEL = QFrame.Shape.WinPanel
    QT_FRAME_PLAIN = QFrame.Shadow.Plain
    QT_FRAME_RAISED = QFrame.Shadow.Raised
    QT_FRAME_SUNKEN = QFrame.Shadow.Sunken

    # qicon
    QT_ICON_NORMAL = QIcon.Mode.Normal
    QT_ICON_ACTIVE = QIcon.Mode.Active
    QT_ICON_SELECTED = QIcon.Mode.Selected
    QT_ICON_DISABLED = QIcon.Mode.Disabled
    QT_ICON_ON = QIcon.State.On
    QT_ICON_OFF = QIcon.State.Off

    # qabstractitemview
    QT_ABSTRACT_ITEM_VIEW_NO_DRAG_DROP = QAbstractItemView.DragDropMode.NoDragDrop
    QT_ABSTRACT_ITEM_VIEW_DRAG_ONLY = QAbstractItemView.DragDropMode.DragOnly
    QT_ABSTRACT_ITEM_VIEW_DROP_ONLY = QAbstractItemView.DragDropMode.DropOnly
    QT_ABSTRACT_ITEM_VIEW_DRAG_DROP = QAbstractItemView.DragDropMode.DragDrop
    QT_ABSTRACT_ITEM_VIEW_INTERNAL_MOVE = QAbstractItemView.DragDropMode.InternalMove
    QT_ABSTRACT_ITEM_VIEW_NO_EDIT_TRIGGERS = QAbstractItemView.EditTrigger.NoEditTriggers
    QT_ABSTRACT_ITEM_VIEW_DOUBLE_CLICK = QAbstractItemView.EditTrigger.DoubleClicked
    QT_ABSTRACT_ITEM_VIEW_CURRENT_CHANGED = QAbstractItemView.EditTrigger.CurrentChanged
    QT_ABSTRACT_ITEM_VIEW_SELECTED_CLICKED = QAbstractItemView.EditTrigger.SelectedClicked
    QT_ABSTRACT_ITEM_VIEW_ALL_EDIT_TRIGGERS = QAbstractItemView.EditTrigger.AllEditTriggers
    QT_ABSTRACT_ITEM_VIEW_ENSURE_VISIBLE = QAbstractItemView.ScrollHint.EnsureVisible
    QT_ABSTRACT_ITEM_VIEW_POSITION_AT_TOP = QAbstractItemView.ScrollHint.PositionAtTop
    QT_ABSTRACT_ITEM_VIEW_POSITION_AT_BOTTOM = QAbstractItemView.ScrollHint.PositionAtBottom
    QT_ABSTRACT_ITEM_VIEW_POSITION_AT_CENTER = QAbstractItemView.ScrollHint.PositionAtCenter
    QT_ABSTRACT_ITEM_VIEW_SCROLL_PER_ITEM = QAbstractItemView.ScrollMode.ScrollPerItem
    QT_ABSTRACT_ITEM_VIEW_SCROLL_PER_PIXEL = QAbstractItemView.ScrollMode.ScrollPerPixel
    QT_ABSTRACT_ITEM_VIEW_SELECT_ITEMS = QAbstractItemView.SelectionBehavior.SelectItems
    QT_ABSTRACT_ITEM_VIEW_SELECT_ROWS = QAbstractItemView.SelectionBehavior.SelectRows
    QT_ABSTRACT_ITEM_VIEW_SELECT_COLUMNS = QAbstractItemView.SelectionBehavior.SelectColumns
    QT_ABSTRACT_ITEM_VIEW_SINGLE_SELECTION = QAbstractItemView.SelectionMode.SingleSelection
    QT_ABSTRACT_ITEM_VIEW_MULTI_SELECTION = QAbstractItemView.SelectionMode.MultiSelection
    QT_ABSTRACT_ITEM_VIEW_NO_SELECTION = QAbstractItemView.SelectionMode.NoSelection
    QT_ABSTRACT_ITEM_VIEW_CONTIGUOUS_SELECTION = QAbstractItemView.SelectionMode.ContiguousSelection
    QT_ABSTRACT_ITEM_VIEW_EXTENDED_SELECTION = QAbstractItemView.SelectionMode.ExtendedSelection

    # qheaderview
    QT_HEADER_VIEW_INTERACTIVE = QHeaderView.ResizeMode.Interactive
    QT_HEADER_VIEW_FIXED = QHeaderView.ResizeMode.Fixed
    QT_HEADER_VIEW_STRETCH = QHeaderView.ResizeMode.Stretch
    QT_HEADER_VIEW_RESIZE_TO_CONTENT = QHeaderView.ResizeMode.ResizeToContents
    QT_HEADER_VIEW_CUSTOM = QHeaderView.ResizeMode.Custom

    # qlistview
    QT_LIST_VIEW_LEFT_TO_RIGHT = QListView.Flow.LeftToRight
    QT_LIST_VIEW_TOP_TO_BOTTOM = QListView.Flow.TopToBottom
    QT_LIST_VIEW_SINGLE_PASS = QListView.LayoutMode.SinglePass
    QT_LIST_VIEW_BATCHED = QListView.LayoutMode.Batched
    QT_LIST_VIEW_STATIC = QListView.Movement.Static
    QT_LIST_VIEW_FREE = QListView.Movement.Free
    QT_LIST_VIEW_SNAP = QListView.Movement.Snap
    QT_LIST_VIEW_FIXED = QListView.ResizeMode.Fixed
    QT_LIST_VIEW_ADJUST = QListView.ResizeMode.Adjust
    QT_LIST_VIEW_LIST_MODE = QListView.ViewMode.ListMode
    QT_LIST_VIEW_ICON_MODE = QListView.ViewMode.IconMode

    # qcombobox
    QT_COMBOBOX_NO_INSERT = QComboBox.InsertPolicy.NoInsert
    QT_COMBOBOX_INSERT_AT_TOP = QComboBox.InsertPolicy.InsertAtTop
    QT_COMBOBOX_INSERT_AT_BOTTOM = QComboBox.InsertPolicy.InsertAtBottom
    QT_COMBOBOX_INSERT_AT_CURRENT = QComboBox.InsertPolicy.InsertAtCurrent
    QT_COMBOBOX_INSERT_AFTER_CURRENT = QComboBox.InsertPolicy.InsertAfterCurrent
    QT_COMBOBOX_INSERT_BEFORE_CURRENT = QComboBox.InsertPolicy.InsertBeforeCurrent
    QT_COMBOBOX_INSERT_ALPHABETICALLY = QComboBox.InsertPolicy.InsertAlphabetically
    QT_COMBOBOX_ADJUST_TO_CONTENTS = QComboBox.SizeAdjustPolicy.AdjustToContents
    QT_COMBOBOX_ADJUST_TO_CONTENTS_ON_FIRST_SHOW = QComboBox.SizeAdjustPolicy.AdjustToContentsOnFirstShow
    QT_COMBOBOX_ADJUST_TO_MINIMUM_CONTENTS_LENGTH_WITH_ICON = QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon

    # qevent
    QT_EVENT_MOUSE_BUTTON_RELEASE = QEvent.Type.MouseButtonRelease
    QT_EVENT_MOUSE_BUTTON_PRESS = QEvent.Type.MouseButtonPress
    QT_EVENT_KEY_PRESS = QEvent.Type.KeyPress
    QT_EVENT_KEY_RELEASE = QEvent.Type.KeyRelease
    QT_EVENT_TOOL_TIP = QEvent.Type.ToolTip

    # qslider
    QT_SLIDER_TO_TICKS = QSlider.TickPosition.NoTicks
    QT_SLIDER_TICKS_BOTH_SIDES = QSlider.TickPosition.TicksBothSides
    QT_SLIDER_TICKS_LEFT = QSlider.TickPosition.TicksLeft
    QT_SLIDER_TICKS_RIGHT = QSlider.TickPosition.TicksRight
    QT_SLIDER_TICKS_ABOVE = QSlider.TickPosition.TicksAbove
    QT_SLIDER_TICKS_BELOW = QSlider.TickPosition.TicksBelow

    # qtoolbutton
    QT_TOOLBUTTON_DELAYED_POPUP = QToolButton.ToolButtonPopupMode.DelayedPopup
    QT_TOOLBUTTON_MENU_BUTTON_POPUP = QToolButton.ToolButtonPopupMode.MenuButtonPopup
    QT_TOOLBUTTIN_INSTANT_POPUP = QToolButton.ToolButtonPopupMode.InstantPopup

    # timespec
    QT_TIMESPEC_LOCAL_TIME = Qt.TimeSpec.LocalTime
    QT_TIMESPEC_UTC = Qt.TimeSpec.UTC
    QT_TIMESPEC_OFFSET_FROM_UTC = Qt.TimeSpec.OffsetFromUTC

    # qitemselectionmodel
    QT_ITEM_SELECTION_NO_UPDATE = QItemSelectionModel.SelectionFlag.NoUpdate
    QT_ITEM_SELECTION_CLEAR = QItemSelectionModel.SelectionFlag.Clear
    QT_ITEM_SELECTION_SELECT = QItemSelectionModel.SelectionFlag.Select
    QT_ITEM_SELECTION_DESELECT = QItemSelectionModel.SelectionFlag.Deselect
    QT_ITEM_SELECTION_TOGGLE = QItemSelectionModel.SelectionFlag.Toggle
    QT_ITEM_SELECTION_CURRENT = QItemSelectionModel.SelectionFlag.Current
    QT_ITEM_SELECTION_ROWS = QItemSelectionModel.SelectionFlag.Rows
    QT_ITEM_SELECTION_COLUMNS = QItemSelectionModel.SelectionFlag.Columns
    QT_ITEM_SELECTION_SELECT_CURRENT = QItemSelectionModel.SelectionFlag.SelectCurrent
    QT_ITEM_SELECTION_TOGGLE_CURRENT = QItemSelectionModel.SelectionFlag.ToggleCurrent
    QT_ITEM_SELECTION_CLEAR_AND_SELECT = QItemSelectionModel.SelectionFlag.ClearAndSelect

    # QStyle
    QT_STYLE_CC_SLIDER = QStyle.ComplexControl.CC_Slider
    QT_STYLE_SP_DIR_OPEN_ICON = QStyle.StandardPixmap.SP_DirOpenIcon
    QT_STYLE_STATE_SELECTED = QStyle.StateFlag.State_Selected
    QT_STYLE_SC_SLIDER_HANDLE = QStyle.SubControl.SC_SliderHandle

    # qdatetimeedit
    QT_DATE_TIME_EDIT_NO_SECTION = QDateTimeEdit.Section.NoSection
    QT_DATE_TIME_EDIT_AM_PM_SECTION = QDateTimeEdit.Section.AmPmSection
    QT_DATE_TIME_EDIT_MSEC_SECTION = QDateTimeEdit.Section.MSecSection
    QT_DATE_TIME_EDIT_SECOND_SECTION = QDateTimeEdit.Section.SecondSection
    QT_DATE_TIME_EDIT_MINUTE_SECTION = QDateTimeEdit.Section.MinuteSection
    QT_DATE_TIME_EDIT_HOUR_SECTION = QDateTimeEdit.Section.HourSection
    QT_DATE_TIME_EDIT_DAY_SECTION = QDateTimeEdit.Section.DaySection
    QT_DATE_TIME_EDIT_MONTH_SECTION = QDateTimeEdit.Section.MonthSection
    QT_DATE_TIME_EDIT_YEAR_SECTION = QDateTimeEdit.Section.YearSection

    # qformlayout
    QT_FORM_LAYOUT_FIELDS_STAY_AT_SIZE_HINT = QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
    QT_FORM_LAYOUT_EXPANDING_FIELDS_GROW = QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
    QT_FORM_LAYOUT_ALL_NON_FIXED_FIELDS_GROW = QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
    QT_FORM_LAYOUT_LABEL_ROLE = QFormLayout.ItemRole.LabelRole
    QT_FORM_LAYOUT_FIELD_ROLE = QFormLayout.ItemRole.FieldRole
    QT_FORM_LAYOUT_SPANNING_ROLE = QFormLayout.ItemRole.SpanningRole
    QT_FORM_LAYOUT_DONT_WRAP_ROWS = QFormLayout.RowWrapPolicy.DontWrapRows
    QT_FORM_LAYOUT_WRAP_LONG_ROWS = QFormLayout.RowWrapPolicy.WrapLongRows
    QT_FORM_LAYOUT_WRAP_ALL_ROWS = QFormLayout.RowWrapPolicy.WrapAllRows

    # qdialog
    QT_DIALOG_ACCEPTED = QDialog.DialogCode.Accepted
    QT_DIALOG_REJECTED = QDialog.DialogCode.Rejected

    # qdialogbuttonbox
    QT_BUTTON_BOX_WIN_LAYOUT = QDialogButtonBox.ButtonLayout.WinLayout
    QT_BUTTON_BOX_MAC_LAYOUT = QDialogButtonBox.ButtonLayout.MacLayout
    QT_BUTTON_BOX_KDE_LAYOUT = QDialogButtonBox.ButtonLayout.KdeLayout
    QT_BUTTON_BOX_GNOME_LAYOUT = QDialogButtonBox.ButtonLayout.GnomeLayout
    QT_BUTTON_BOX_ANDROID_LAYOUT = QDialogButtonBox.ButtonLayout.AndroidLayout
    QT_BUTTON_BOX_INVALID_ROLE = QDialogButtonBox.ButtonRole.InvalidRole
    QT_BUTTON_BOX_ACCEPT_ROLE = QDialogButtonBox.ButtonRole.AcceptRole
    QT_BUTTON_BOX_REJECT_ROLE = QDialogButtonBox.ButtonRole.RejectRole
    QT_BUTTON_BOX_DESTRUCTIVE_ROLE = QDialogButtonBox.ButtonRole.DestructiveRole
    QT_BUTTON_BOX_ACTION_ROLE = QDialogButtonBox.ButtonRole.ActionRole
    QT_BUTTON_BOX_HELP_ROLE = QDialogButtonBox.ButtonRole.HelpRole
    QT_BUTTON_BOX_YES_ROLE = QDialogButtonBox.ButtonRole.YesRole
    QT_BUTTON_BOX_NO_ROLE = QDialogButtonBox.ButtonRole.NoRole
    QT_BUTTON_BOX_APPLY_ROLE = QDialogButtonBox.ButtonRole.ApplyRole
    QT_BUTTON_BOX_RESET_ROLE = QDialogButtonBox.ButtonRole.ResetRole
    QT_BUTTON_BOX_OK = QDialogButtonBox.StandardButton.Ok
    QT_BUTTON_BOX_OPEN = QDialogButtonBox.StandardButton.Open
    QT_BUTTON_BOX_SAVE = QDialogButtonBox.StandardButton.Save
    QT_BUTTON_BOX_CANCEL = QDialogButtonBox.StandardButton.Cancel
    QT_BUTTON_BOX_CLOSE = QDialogButtonBox.StandardButton.Close
    QT_BUTTON_BOX_DISCARD = QDialogButtonBox.StandardButton.Discard
    QT_BUTTON_BOX_APPLY = QDialogButtonBox.StandardButton.Apply
    QT_BUTTON_BOX_RESET = QDialogButtonBox.StandardButton.Reset
    QT_BUTTON_BOX_RESTORE_DEFUALTS = QDialogButtonBox.StandardButton.RestoreDefaults
    QT_BUTTON_BOX_HELP = QDialogButtonBox.StandardButton.Help
    QT_BUTTON_BOX_SAVE_ALL = QDialogButtonBox.StandardButton.SaveAll
    QT_BUTTON_BOX_YES = QDialogButtonBox.StandardButton.Yes
    QT_BUTTON_BOX_YES_TO_ALL = QDialogButtonBox.StandardButton.YesToAll
    QT_BUTTON_BOX_NO = QDialogButtonBox.StandardButton.No
    QT_BUTTON_BOX_NO_TO_ALL = QDialogButtonBox.StandardButton.NoToAll
    QT_BUTTON_BOX_ABORT = QDialogButtonBox.StandardButton.Abort
    QT_BUTTON_BOX_RETRY = QDialogButtonBox.StandardButton.Retry
    QT_BUTTON_BOX_IGNORE = QDialogButtonBox.StandardButton.Ignore
    QT_BUTTON_BOX_NO_BUTTON = QDialogButtonBox.StandardButton.NoButton

    # qmessagebox
    QT_MESSAGE_BOX_INVALID_ROLE = QMessageBox.ButtonRole.InvalidRole
    QT_MESSAGE_BOX_ACCEPT_ROLE = QMessageBox.ButtonRole.AcceptRole
    QT_MESSAGE_BOX_REJECT_ROLE = QMessageBox.ButtonRole.RejectRole
    QT_MESSAGE_BOX_DESTRUCTIVE_ROLE = QMessageBox.ButtonRole.DestructiveRole
    QT_MESSAGE_BOX_ACTION_ROLE = QMessageBox.ButtonRole.ActionRole
    QT_MESSAGE_BOX_HELP_ROLE = QMessageBox.ButtonRole.HelpRole
    QT_MESSAGE_BOX_YES_ROLE = QMessageBox.ButtonRole.YesRole
    QT_MESSAGE_BOX_NO_ROLE = QMessageBox.ButtonRole.NoRole
    QT_MESSAGE_BOX_APPLY_ROLE = QMessageBox.ButtonRole.ApplyRole
    QT_MESSAGE_BOX_RESET_ROLE = QMessageBox.ButtonRole.ResetRole
    QT_MESSAGE_BOX_NO_ICON = QMessageBox.Icon.NoIcon
    QT_MESSAGE_BOX_QUESTION = QMessageBox.Icon.Question
    QT_MESSAGE_BOX_INFORMATION = QMessageBox.Icon.Information
    QT_MESSAGE_BOX_WARNING = QMessageBox.Icon.Warning
    QT_MESSAGE_BOX_CRITICAL = QMessageBox.Icon.Critical
    QT_MESSAGE_BOX_OK = QMessageBox.StandardButton.Ok
    QT_MESSAGE_BOX_OPEN = QMessageBox.StandardButton.Open
    QT_MESSAGE_BOX_SAVE = QMessageBox.StandardButton.Save
    QT_MESSAGE_BOX_CANCEL = QMessageBox.StandardButton.Cancel
    QT_MESSAGE_BOX_CLOSE = QMessageBox.StandardButton.Close
    QT_MESSAGE_BOX_DISCARD = QMessageBox.StandardButton.Discard
    QT_MESSAGE_BOX_APPLY = QMessageBox.StandardButton.Apply
    QT_MESSAGE_BOX_RESET = QMessageBox.StandardButton.Reset
    QT_MESSAGE_BOX_RESTORE_DEFUALTS = QMessageBox.StandardButton.RestoreDefaults
    QT_MESSAGE_BOX_HELP = QMessageBox.StandardButton.Help
    QT_MESSAGE_BOX_SAVE_ALL = QMessageBox.StandardButton.SaveAll
    QT_MESSAGE_BOX_YES = QMessageBox.StandardButton.Yes
    QT_MESSAGE_BOX_YES_TO_ALL = QMessageBox.StandardButton.YesToAll
    QT_MESSAGE_BOX_NO = QMessageBox.StandardButton.No
    QT_MESSAGE_BOX_NO_TO_ALL = QMessageBox.StandardButton.NoToAll
    QT_MESSAGE_BOX_ABORT = QMessageBox.StandardButton.Abort
    QT_MESSAGE_BOX_RETRY = QMessageBox.StandardButton.Retry
    QT_MESSAGE_BOX_IGNORE = QMessageBox.StandardButton.Ignore
    QT_MESSAGE_BOX_NO_BUTTON = QMessageBox.StandardButton.NoButton

    # qpalette
    QT_PALETTE_DISABLED = QPalette.ColorGroup.Disabled
    QT_PALETTE_ACTIVE = QPalette.ColorGroup.Active
    QT_PALETTE_INACTIVE = QPalette.ColorGroup.Inactive
    QT_PALETTE_NORMAL = QPalette.ColorGroup.Normal
    QT_PALETTE_WINDOW_TEXT = QPalette.ColorRole.WindowText
    QT_PALETTE_WINDOW = QPalette.ColorRole.Window
    QT_PALETTE_BASE = QPalette.ColorRole.Base
    QT_PALETTE_ALTERNATE_BASE = QPalette.ColorRole.AlternateBase
    QT_PALETTE_TOOLTIP_BASE = QPalette.ColorRole.ToolTipBase
    QT_PALETTE_TOOLTIP_TEXT = QPalette.ColorRole.ToolTipText
    QT_PALETTE_PLACEHOLDER_TEXT = QPalette.ColorRole.PlaceholderText
    QT_PALETTE_TEXT = QPalette.ColorRole.Text
    QT_PALETTE_BUTTON = QPalette.ColorRole.Button
    QT_PALETTE_BUTTON_TEXT = QPalette.ColorRole.ButtonText
    QT_PALETTE_BRIGHT_TEXT = QPalette.ColorRole.BrightText
    QT_PALETTE_LIGHT = QPalette.ColorRole.Light
    QT_PALETTE_MID_LIGHT = QPalette.ColorRole.Midlight
    QT_PALETTE_DARK = QPalette.ColorRole.Dark
    QT_PALETTE_MID = QPalette.ColorRole.Mid
    QT_PALETTE_SHADOW = QPalette.ColorRole.Shadow
    QT_PALETTE_HIGHLIGHT = QPalette.ColorRole.Highlight
    QT_PALETTE_HIGHLIGHTED_TEXT = QPalette.ColorRole.HighlightedText
    QT_PALETTE_LINK = QPalette.ColorRole.Link
    QT_PALETTE_LINK_VISITED = QPalette.ColorRole.LinkVisited
    QT_PALETTE_NO_ROLE = QPalette.ColorRole.NoRole

    # qfont
    QT_FONT_MIXED_CASE = QFont.Capitalization.MixedCase
    QT_FONT_ALL_UPPER = QFont.Capitalization.AllUppercase
    QT_FONT_ALL_LOWER = QFont.Capitalization.AllLowercase
    QT_FONT_SMALL_CAPS = QFont.Capitalization.SmallCaps
    QT_FONT_CAPITALIZE = QFont.Capitalization.Capitalize
    QT_FONT_PREFER_DEFAULT_HINTING = QFont.HintingPreference.PreferDefaultHinting
    QT_FONT_PREFER_NO_HINTING = QFont.HintingPreference.PreferNoHinting
    QT_FONT_PREFER_VERTICAL_HINTING = QFont.HintingPreference.PreferVerticalHinting
    QT_FONT_PREFER_FULL_HINTING = QFont.HintingPreference.PreferFullHinting
    QT_FONT_PERCENTAGE_SPACING = QFont.SpacingType.PercentageSpacing
    QT_FONT_ABSOLUTE_SPACING = QFont.SpacingType.AbsoluteSpacing
    QT_FONT_ANY_STRETCH = QFont.Stretch.AnyStretch
    QT_FONT_ULTRA_CONDENSED = QFont.Stretch.UltraCondensed
    QT_FONT_EXTRA_CONDENSED = QFont.Stretch.ExtraCondensed
    QT_FONT_CONDENSED = QFont.Stretch.Condensed
    QT_FONT_SEMI_CONDENSED = QFont.Stretch.SemiCondensed
    QT_FONT_UNSTRETCHED = QFont.Stretch.Unstretched
    QT_FONT_SEMI_EXPANDED = QFont.Stretch.SemiExpanded
    QT_FONT_EXPANDED = QFont.Stretch.Expanded
    QT_FONT_EXTRA_EXPANDED = QFont.Stretch.ExtraExpanded
    QT_FONT_ULTRA_EXPANDED = QFont.Stretch.UltraExpanded
    QT_FONT_STYLE_NORMAL = QFont.Style.StyleNormal
    QT_FONT_STYLE_ITALIC = QFont.Style.StyleItalic
    QT_FONT_STYLE_OBLIQUE = QFont.Style.StyleOblique
    QT_FONT_ANY_STYLE = QFont.StyleHint.AnyStyle
    QT_FONT_SANS_SERIF = QFont.StyleHint.SansSerif
    QT_FONT_HELVETICA = QFont.StyleHint.Helvetica
    QT_FONT_SERIF = QFont.StyleHint.Serif
    QT_FONT_TIMES = QFont.StyleHint.Times
    QT_FONT_TYPEWRITER = QFont.StyleHint.TypeWriter
    QT_FONT_COURIER = QFont.StyleHint.Courier
    QT_FONT_OLD_ENGLISH = QFont.StyleHint.OldEnglish
    QT_FONT_DECORATIVE = QFont.StyleHint.Decorative
    QT_FONT_MONOSPACE = QFont.StyleHint.Monospace
    QT_FONT_FANTASY = QFont.StyleHint.Fantasy
    QT_FONT_CURSIVE = QFont.StyleHint.Cursive
    QT_FONT_SYSTEM = QFont.StyleHint.System
    QT_FONT_PREFER_DEFAULT = QFont.StyleStrategy.PreferDefault
    QT_FONT_PREFER_BITMAP = QFont.StyleStrategy.PreferBitmap
    QT_FONT_PREFER_DEVICE = QFont.StyleStrategy.PreferDevice
    QT_FONT_PREFER_OUTLINE = QFont.StyleStrategy.PreferOutline
    QT_FONT_FORCE_OUTLINE = QFont.StyleStrategy.ForceOutline
    QT_FONT_NO_ANTIALIAS = QFont.StyleStrategy.NoAntialias
    QT_FONT_NO_SUBPIXEL_ANTIALIAS = QFont.StyleStrategy.NoSubpixelAntialias
    QT_FONT_PREFER_ANTIALIAS = QFont.StyleStrategy.PreferAntialias
    QT_FONT_NO_FONT_MERGING = QFont.StyleStrategy.NoFontMerging
    QT_FONT_PREFER_NO_SHAPING = QFont.StyleStrategy.PreferNoShaping
    QT_FONT_PREFER_MATCH = QFont.StyleStrategy.PreferMatch
    QT_FONT_PREFER_QUALITY = QFont.StyleStrategy.PreferQuality
    QT_FONT_THIN = QFont.Weight.Thin
    QT_FONT_EXTRA_LIGHT = QFont.Weight.ExtraLight
    QT_FONT_LIGHT = QFont.Weight.Light
    QT_FONT_NORMAL = QFont.Weight.Normal
    QT_FONT_MEDIUM = QFont.Weight.Medium
    QT_FONT_DEMI_BOLD = QFont.Weight.DemiBold
    QT_FONT_BOLD = QFont.Weight.Bold
    QT_FONT_EXTRA_BOLD = QFont.Weight.ExtraBold
    QT_FONT_BLACK = QFont.Weight.Black

    # qimage
    QT_IMAGE_FORMAT_ARGB32 = QImage.Format.Format_ARGB32

    # qeventloop
    QT_EVENT_LOOP_EXCLUDE_USER_INPUT_EVENTS = QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents

    # qnetworkrequest
    QT_NETWORK_REQUEST_HTTP_STATUS_CODE_ATTRIBUTE = QNetworkRequest.Attribute.HttpStatusCodeAttribute

    # qabstractscrollarea
    QT_ABSTRACT_SCROLL_AREA_ADJUST_IGNORED = QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored
    QT_ABSTRACT_SCROLL_AREA_ADJUST_TO_CONTENTS_ON_FIRST_SHOW = QAbstractScrollArea.SizeAdjustPolicy.AdjustToContentsOnFirstShow
    QT_ABSTRACT_SCROLL_AREA_ADJUST_TO_CONTENTS = QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents

    # qabstractspinbox
    QT_ABSTRACT_SPIN_BOX_UP_DOWN_ARROWS = QAbstractSpinBox.ButtonSymbols.UpDownArrows
    QT_ABSTRACT_SPIN_BOX_PLUS_MINUS = QAbstractSpinBox.ButtonSymbols.PlusMinus
    QT_ABSTRACT_SPIN_BOX_NO_BUTTONS = QAbstractSpinBox.ButtonSymbols.NoButtons
    QT_ABSTRACT_SPIN_BOX_CORRECT_TO_PREV_VALUE = QAbstractSpinBox.CorrectionMode.CorrectToPreviousValue
    QT_ABSTRACT_SPIN_BOX_CORRECT_TO_NEAREST_VALUE = QAbstractSpinBox.CorrectionMode.CorrectToNearestValue
    QT_ABSTRACT_SPIN_BOX_STEP_NONE = QAbstractSpinBox.StepEnabledFlag.StepNone
    QT_ABSTRACT_SPIN_BOX_STEP_UP_ENABLED = QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
    QT_ABSTRACT_SPIN_BOX_STEP_DOWN_ENABLED = QAbstractSpinBox.StepEnabledFlag.StepDownEnabled
    QT_ABSTRACT_SPIN_BOX_DEFAULT_STEP_TYPE = QAbstractSpinBox.StepType.DefaultStepType
    QT_ABSTRACT_SPIN_BOX_ADAPTIVE_DECIMAL_STEP_TYPE = QAbstractSpinBox.StepType.AdaptiveDecimalStepType

    # qfiledialog
    QT_FILE_DIALOG_DONT_CONFIRM_OVERWRITE = QFileDialog.Option.DontConfirmOverwrite
    QT_FILE_DIALOG_ACCEPT_OPEN = QFileDialog.AcceptMode.AcceptOpen
    QT_FILE_DIALOG_ACCEPT_SAVE = QFileDialog.AcceptMode.AcceptSave
    QT_FILE_DIALOG_ANY_FILE = QFileDialog.FileMode.AnyFile
    QT_FILE_DIALOG_EXISTONG_FILES = QFileDialog.FileMode.ExistingFiles
    QT_FILE_DIALOG_EXISTING_FILE = QFileDialog.FileMode.ExistingFile
    QT_FILE_DIALOG_DIRECTORY = QFileDialog.FileMode.Directory
    QT_FILE_DIALOG_DETAIL = QFileDialog.ViewMode.Detail
    QT_FILE_DIALOG_SHOW_DIRS_ONLY = QFileDialog.Option.ShowDirsOnly

    QT_WA_STYLED_BACKGROUND = Qt.WidgetAttribute.WA_StyledBackground

    QT_TOP_RIGHT_CORNER = Qt.Corner.TopRightCorner
    QT_BOTTOM_RIGHT_CORNER = Qt.Corner.BottomRightCorner
    QT_BOTTOM_LEFT_CORNER = Qt.Corner.BottomLeftCorner
    QT_TOP_LEFT_CORNER = Qt.Corner.TopLeftCorner

    # qtabwidget
    QT_TAB_WIDGET_ROUNDED = QTabWidget.TabShape.Rounded
    QT_TAB_WIDGET_TRIANGULAR = QTabWidget.TabShape.Triangular

    # qpainter
    QT_PAINTER_ANTIALIASING = QPainter.RenderHint.Antialiasing

    QT_KEEP_ASPECT_RATIO = Qt.AspectRatioMode.KeepAspectRatio
else:
    # data types
    try:
        QT_STRING = QVariant.String if Qgis.QGIS_VERSION_INT < 33800 else QMetaType.QString
        QT_INT = QVariant.Int if Qgis.QGIS_VERSION_INT < 33800 else QMetaType.Int
        QT_LONG = QVariant.Long if Qgis.QGIS_VERSION_INT < 33800 else QMetaType.Long
        QT_LONG_LONG = QVariant.LongLong if Qgis.QGIS_VERSION_INT < 33800 else QMetaType.LongLong
        QT_FLOAT = QVariant.Float if Qgis.QGIS_VERSION_INT < 33800 else QMetaType.Float
        QT_DOUBLE = QVariant.Double if Qgis.QGIS_VERSION_INT < 33800 else QMetaType.Double
    except:
        QT_STRING = QMetaType.QString
        QT_INT = QMetaType.Int
        QT_LONG = QMetaType.Long
        QT_LONG_LONG = QMetaType.LongLong
        QT_FLOAT = QMetaType.Float
        QT_DOUBLE = QMetaType.Double

    # colours
    QT_RED = Qt.red
    QT_BLUE = Qt.blue
    QT_GREEN = Qt.green
    QT_BLACK = Qt.black
    QT_WHITE = Qt.white
    QT_DARK_GREEN = Qt.darkGreen
    QT_TRANSPARENT = Qt.transparent
    QT_MAGENTA = Qt.magenta

    # text format
    QT_RICH_TEXT = Qt.RichText

    # check state
    QT_CHECKED = Qt.Checked
    QT_UNCHECKED = Qt.Unchecked
    QT_PARTIALLY_CHECKED = Qt.PartiallyChecked

    # orientation
    QT_HORIZONTAL = Qt.Horizontal
    QT_VERTICAL = Qt.Vertical

    # mouse buttons
    QT_LEFT_BUTTON = Qt.LeftButton
    QT_RIGHT_BUTTON = Qt.RightButton

    # alignment
    QT_ALIGN_LEFT = Qt.AlignLeft
    QT_ALIGN_RIGHT = Qt.AlignRight
    QT_ALIGN_CENTER = Qt.AlignCenter
    QT_ALIGN_TOP = Qt.AlignTop
    QT_ALIGN_BOTTOM = Qt.AlignBottom
    QT_ALIGN_V_CENTER = Qt.AlignVCenter
    QT_ALIGN_H_CENTER = Qt.AlignHCenter
    QT_ALIGN_ABSOLUTE = Qt.AlignAbsolute
    QT_ALIGN_LEADING = Qt.AlignLeading
    QT_ALIGN_TRAILING = Qt.AlignTrailing

    # item data role
    QT_ITEM_DATA_EDIT_ROLE = Qt.EditRole
    QT_ITEM_DATA_DISPLAY_ROLE = Qt.DisplayRole
    QT_ITEM_DATA_DECORATION_ROLE = Qt.DecorationRole
    QT_ITEM_DATA_TOOL_TIP_ROLE = Qt.ToolTipRole
    QT_ITEM_DATA_STATUS_TIP_ROLE = Qt.StatusTipRole
    QT_ITEM_DATA_WHATS_THIS_ROLE = Qt.WhatsThisRole
    QT_ITEM_DATA_SIZE_HINT_ROLE = Qt.SizeHintRole
    QT_ITEM_DATA_FONT_ROLE = Qt.FontRole
    QT_ITEM_DATA_TEXT_ALIGNMENT_ROLE = Qt.TextAlignmentRole
    QT_ITEM_DATA_BACKGROUND_ROLE = Qt.BackgroundRole
    QT_ITEM_DATA_FOREGROUND_ROLE = Qt.ForegroundRole
    QT_ITEM_DATA_CHECK_STATE_ROLE = Qt.CheckStateRole
    QT_ITEM_DATA_INITIAL_SORT_ORDER_ROLE = Qt.InitialSortOrderRole
    QT_ITEM_DATA_ACCESSIBLE_TEXT_ROLE = Qt.AccessibleTextRole
    QT_ITEM_DATA_ACCESSIBLE_DESCRIPTION_ROLE = Qt.AccessibleDescriptionRole
    QT_ITEM_DATA_USER_ROLE = Qt.UserRole

    # item flags
    QT_ITEM_FLAG_NO_ITEM_FLAGS = Qt.NoItemFlags
    QT_ITEM_FLAG_ITEM_IS_SELECTABLE = Qt.ItemIsSelectable
    QT_ITEM_FLAG_ITEM_IS_EDITABLE = Qt.ItemIsEditable
    QT_ITEM_FLAG_ITEM_IS_DRAG_ENABLED = Qt.ItemIsDragEnabled
    QT_ITEM_FLAG_ITEM_IS_DROP_ENABLED = Qt.ItemIsDropEnabled
    QT_ITEM_FLAG_ITEM_IS_USER_CHECKABLE = Qt.ItemIsUserCheckable
    QT_ITEM_FLAG_ITEM_IS_ENABLED = Qt.ItemIsEnabled
    QT_ITEM_FLAG_ITEM_IS_AUTO_TRISTATE = Qt.ItemIsAutoTristate
    QT_ITEM_FLAG_ITEM_NEVER_HAS_CHILDREN = Qt.ItemNeverHasChildren
    QT_ITEM_FLAG_ITEM_IS_USER_TRISTATE = Qt.ItemIsUserTristate

    # layout direction
    QT_LAYOUT_DIRECTION_LEFT_TO_RIGHT = Qt.LeftToRight
    QT_LAYOUT_DIRECTION_RIGHT_TO_LEFT = Qt.RightToLeft
    QT_LAYOUT_DIRECTION_AUTO = Qt.LayoutDirectionAuto

    QT_LAYOUT_SET_FIXED_SIZE = QLayout.SetFixedSize

    # keys
    QT_KEY_RETURN = Qt.Key_Return
    QT_KEY_ESCAPE = Qt.Key_Escape
    QT_KEY_C = Qt.Key_C
    QT_KEY_V = Qt.Key_V
    QT_KEY_F = Qt.Key_F
    QT_KEY_F3 = Qt.Key_F3

    # keyboard modifiers
    QT_KEY_NO_MODIFIER = Qt.NoModifier
    QT_KEY_MODIFIER_SHIFT = Qt.ShiftModifier
    QT_KEY_MODIFIER_CONTROL = Qt.ControlModifier
    QT_KEY_MODIFIER_ALT = Qt.AltModifier

    # qkeysequence
    QT_KEY_SEQUENCE_COPY = QKeySequence.Copy
    QT_KEY_SEQUENCE_PASTE = QKeySequence.Paste
    QT_KEY_SEQUENCE_CUT = QKeySequence.Cut

    # context menu
    QT_CUSTOM_CONTEXT_MENU = Qt.CustomContextMenu
    QT_NO_CONTEXT_MENU = Qt.NoContextMenu

    # cursor
    QT_CURSOR_ARROW = Qt.ArrowCursor
    QT_CURSOR_UP_ARROW = Qt.UpArrowCursor
    QT_CURSOR_CROSS = Qt.CrossCursor
    QT_CURSOR_SIZE_VER = Qt.SizeVerCursor
    QT_CURSOR_SIZE_HOR = Qt.SizeHorCursor
    QT_CURSOR_SIZE_DIAG_B = Qt.SizeBDiagCursor
    QT_CURSOR_SIZE_DIAG_F = Qt.SizeFDiagCursor
    QT_CURSOR_SIZE_ALL = Qt.SizeAllCursor
    QT_CURSOR_WAIT = Qt.WaitCursor

    # case sensitivity
    QT_CASE_INSENSITIVE = Qt.CaseInsensitive
    QT_CASE_SENSITIVE = Qt.CaseSensitive
    QT_PATTERN_CASE_INSENSITIVE = Qt.CaseInsensitive

    # match flags
    QT_MATCH_EXACTLY = Qt.MatchExactly
    QT_MATCH_FIXED_STRING = Qt.MatchFixedString
    QT_MATCH_CONTAINS = Qt.MatchContains
    QT_MATCH_STARTS_WITH = Qt.MatchStartsWith
    QT_MATCH_ENDS_WITH = Qt.MatchEndsWith
    QT_MATCH_CASE_SENSITIVE = Qt.MatchCaseSensitive
    QT_MATCH_REGULAR_EXPRESSION = Qt.MatchRegularExpression
    QT_MATCH_WILDCARD = Qt.MatchWildcard
    QT_MATCH_WRAP = Qt.MatchWrap
    QT_MATCH_RECURSIVE = Qt.MatchRecursive

    # dock widget area
    QT_DOCK_WIDGET_AREA_LEFT = Qt.LeftDockWidgetArea
    QT_DOCK_WIDGET_AREA_RIGHT = Qt.RightDockWidgetArea
    QT_DOCK_WIDGET_AREA_TOP = Qt.TopDockWidgetArea
    QT_DOCK_WIDGET_AREA_BOTTOM = Qt.BottomDockWidgetArea
    QT_DOCK_WIDGET_AREA_ALL = Qt.AllDockWidgetAreas
    QT_DOCK_WIDGET_AREA_NONE = Qt.NoDockWidgetArea

    # window modality
    QT_WINDOW_MODALITY_NON_MODAL = Qt.NonModal
    QT_WINDOW_MODALITY_MODAL = Qt.WindowModal
    QT_WINDOW_MODALITY_APPLICATION_MODAL = Qt.ApplicationModal

    # brush style
    QT_STYLE_NO_BRUSH = Qt.NoBrush
    QT_STYLE_SOLID_BRUSH = Qt.SolidPattern

    # line style
    QT_DASH_LINE = Qt.DashLine
    QT_SOLID_LINE = Qt.SolidLine

    # pen style
    QT_STYLE_NO_PEN = Qt.NoPen
    QT_STYLE_SOLID_PEN = Qt.SolidLine
    QT_STYLE_DASHED_PEN = Qt.DashLine
    QT_STYLE_DOTTED_PEN = Qt.DotLine
    QT_STYLE_DASH_DOTTED_PEN = Qt.DashDotLine
    QT_STYLE_DASH_DOTTED_DOT_PEN = Qt.DashDotDotLine

    # scroll bar policy
    QT_SCROLL_BAR_AS_NEEDED = Qt.ScrollBarAsNeeded
    QT_SCROLL_BAR_ALWAYS_ON = Qt.ScrollBarAlwaysOn
    QT_SCROLL_BAR_ALWAYS_OFF = Qt.ScrollBarAlwaysOff

    # focus policy
    QT_NO_FOCUS = Qt.NoFocus
    QT_TAB_FOCUS = Qt.TabFocus
    QT_CLICK_FOCUS = Qt.ClickFocus
    QT_STRONG_FOCUS = Qt.StrongFocus
    QT_WHEEL_FOCUS = Qt.WheelFocus

    # arrow type
    QT_ARROW_TYPE_NO_ARROW = Qt.NoArrow
    QT_ARROW_TYPE_UP_ARROW = Qt.UpArrow
    QT_ARROW_TYPE_DOWN_ARROW = Qt.DownArrow
    QT_ARROW_TYPE_LEFT_ARROW = Qt.LeftArrow
    QT_ARROW_TYPE_RIGHT_ARROW = Qt.RightArrow

    # elide mode
    QT_ELIDE_LEFT = Qt.ElideLeft
    QT_ELIDE_RIGHT = Qt.ElideRight
    QT_ELIDE_MIDDLE = Qt.ElideMiddle
    QT_ELIDE_NONE = Qt.ElideNone

    # bg mode
    QT_BG_TRANSPARENT = Qt.TransparentMode
    QT_BG_OPAQUE = Qt.OpaqueMode

    # window type
    QT_WINDOW_TYPE = Qt.Window
    QT_DIALOG_TYPE = Qt.Dialog

    # widget attribute
    QT_WA_DELETE_ON_CLOSE = Qt.WA_DeleteOnClose

    # qsizepolicy
    QT_SIZE_POLICY_FIXED = QSizePolicy.Fixed
    QT_SIZE_POLICY_MINIMUM_EXPANDING = QSizePolicy.MinimumExpanding
    QT_SIZE_POLICY_EXPANDING = QSizePolicy.Expanding
    QT_SIZE_POLICY_MAXIMUM = QSizePolicy.Maximum
    QT_SIZE_POLICY_MINIMUM = QSizePolicy.Minimum
    QT_SIZE_POLICY_PREFERRED = QSizePolicy.Preferred

    # qframe
    QT_FRAME_NO_FRAME = QFrame.NoFrame
    QT_FRAME_BOX = QFrame.Box
    QT_FRAME_PANEL = QFrame.Panel
    QT_FRAME_STYLED_PANEL = QFrame.StyledPanel
    QT_FRAME_HLINE = QFrame.HLine
    QT_FRAME_VLINE = QFrame.VLine
    QT_FRAME_WIN_PANEL = QFrame.WinPanel
    QT_FRAME_PLAIN = QFrame.Plain
    QT_FRAME_RAISED = QFrame.Raised
    QT_FRAME_SUNKEN = QFrame.Sunken

    # qicon
    QT_ICON_NORMAL = QIcon.Normal
    QT_ICON_ACTIVE = QIcon.Active
    QT_ICON_SELECTED = QIcon.Selected
    QT_ICON_DISABLED = QIcon.Disabled
    QT_ICON_ON = QIcon.On
    QT_ICON_OFF = QIcon.Off

    # qabstractitemview
    QT_ABSTRACT_ITEM_VIEW_NO_DRAG_DROP = QAbstractItemView.NoDragDrop
    QT_ABSTRACT_ITEM_VIEW_DRAG_ONLY = QAbstractItemView.DragOnly
    QT_ABSTRACT_ITEM_VIEW_DROP_ONLY = QAbstractItemView.DropOnly
    QT_ABSTRACT_ITEM_VIEW_DRAG_DROP = QAbstractItemView.DragDrop
    QT_ABSTRACT_ITEM_VIEW_INTERNAL_MOVE = QAbstractItemView.InternalMove
    QT_ABSTRACT_ITEM_VIEW_NO_EDIT_TRIGGERS = QAbstractItemView.NoEditTriggers
    QT_ABSTRACT_ITEM_VIEW_DOUBLE_CLICK = QAbstractItemView.DoubleClicked
    QT_ABSTRACT_ITEM_VIEW_CURRENT_CHANGED = QAbstractItemView.CurrentChanged
    QT_ABSTRACT_ITEM_VIEW_SELECTED_CLICKED = QAbstractItemView.SelectedClicked
    QT_ABSTRACT_ITEM_VIEW_ALL_EDIT_TRIGGERS = QAbstractItemView.AllEditTriggers
    QT_ABSTRACT_ITEM_VIEW_ENSURE_VISIBLE = QAbstractItemView.EnsureVisible
    QT_ABSTRACT_ITEM_VIEW_POSITION_AT_TOP = QAbstractItemView.PositionAtTop
    QT_ABSTRACT_ITEM_VIEW_POSITION_AT_BOTTOM = QAbstractItemView.PositionAtBottom
    QT_ABSTRACT_ITEM_VIEW_POSITION_AT_CENTER = QAbstractItemView.PositionAtCenter
    QT_ABSTRACT_ITEM_VIEW_SCROLL_PER_ITEM = QAbstractItemView.ScrollPerItem
    QT_ABSTRACT_ITEM_VIEW_SCROLL_PER_PIXEL = QAbstractItemView.ScrollPerPixel
    QT_ABSTRACT_ITEM_VIEW_SELECT_ITEMS = QAbstractItemView.SelectItems
    QT_ABSTRACT_ITEM_VIEW_SELECT_ROWS = QAbstractItemView.SelectRows
    QT_ABSTRACT_ITEM_VIEW_SELECT_COLUMNS = QAbstractItemView.SelectColumns
    QT_ABSTRACT_ITEM_VIEW_SINGLE_SELECTION = QAbstractItemView.SingleSelection
    QT_ABSTRACT_ITEM_VIEW_MULTI_SELECTION = QAbstractItemView.MultiSelection
    QT_ABSTRACT_ITEM_VIEW_NO_SELECTION = QAbstractItemView.NoSelection
    QT_ABSTRACT_ITEM_VIEW_CONTIGUOUS_SELECTION = QAbstractItemView.ContiguousSelection
    QT_ABSTRACT_ITEM_VIEW_EXTENDED_SELECTION = QAbstractItemView.ExtendedSelection

    # qheaderview
    QT_HEADER_VIEW_INTERACTIVE = QHeaderView.Interactive
    QT_HEADER_VIEW_FIXED = QHeaderView.Fixed
    QT_HEADER_VIEW_STRETCH = QHeaderView.Stretch
    QT_HEADER_VIEW_RESIZE_TO_CONTENT = QHeaderView.ResizeToContents
    QT_HEADER_VIEW_CUSTOM = QHeaderView.Custom

    # qlistview
    QT_LIST_VIEW_LEFT_TO_RIGHT = QListView.LeftToRight
    QT_LIST_VIEW_TOP_TO_BOTTOM = QListView.TopToBottom
    QT_LIST_VIEW_SINGLE_PASS = QListView.SinglePass
    QT_LIST_VIEW_BATCHED = QListView.Batched
    QT_LIST_VIEW_STATIC = QListView.Static
    QT_LIST_VIEW_FREE = QListView.Free
    QT_LIST_VIEW_SNAP = QListView.Snap
    QT_LIST_VIEW_FIXED = QListView.Fixed
    QT_LIST_VIEW_ADJUST = QListView.Adjust
    QT_LIST_VIEW_LIST_MODE = QListView.ListMode
    QT_LIST_VIEW_ICON_MODE = QListView.IconMode

    # qcombobox
    QT_COMBOBOX_NO_INSERT = QComboBox.NoInsert
    QT_COMBOBOX_INSERT_AT_TOP = QComboBox.InsertAtTop
    QT_COMBOBOX_INSERT_AT_BOTTOM = QComboBox.InsertAtBottom
    QT_COMBOBOX_INSERT_AT_CURRENT = QComboBox.InsertAtCurrent
    QT_COMBOBOX_INSERT_AFTER_CURRENT = QComboBox.InsertAfterCurrent
    QT_COMBOBOX_INSERT_BEFORE_CURRENT = QComboBox.InsertBeforeCurrent
    QT_COMBOBOX_INSERT_ALPHABETICALLY = QComboBox.InsertAlphabetically
    QT_COMBOBOX_ADJUST_TO_CONTENTS = QComboBox.AdjustToContents
    QT_COMBOBOX_ADJUST_TO_CONTENTS_ON_FIRST_SHOW = QComboBox.AdjustToContentsOnFirstShow
    QT_COMBOBOX_ADJUST_TO_MINIMUM_CONTENTS_LENGTH_WITH_ICON = QComboBox.AdjustToMinimumContentsLengthWithIcon

    # qevent
    QT_EVENT_MOUSE_BUTTON_RELEASE = QEvent.MouseButtonRelease
    QT_EVENT_MOUSE_BUTTON_PRESS = QEvent.MouseButtonPress
    QT_EVENT_KEY_PRESS = QEvent.KeyPress
    QT_EVENT_KEY_RELEASE = QEvent.KeyRelease
    QT_EVENT_TOOL_TIP = QEvent.ToolTip

    # qslider
    QT_SLIDER_TO_TICKS = QSlider.NoTicks
    QT_SLIDER_TICKS_BOTH_SIDES = QSlider.TicksBothSides
    QT_SLIDER_TICKS_LEFT = QSlider.TicksLeft
    QT_SLIDER_TICKS_RIGHT = QSlider.TicksRight
    QT_SLIDER_TICKS_ABOVE = QSlider.TicksAbove
    QT_SLIDER_TICKS_BELOW = QSlider.TicksBelow

    # qtoolbutton
    QT_TOOLBUTTON_DELAYED_POPUP = QToolButton.DelayedPopup
    QT_TOOLBUTTON_MENU_BUTTON_POPUP = QToolButton.MenuButtonPopup
    QT_TOOLBUTTIN_INSTANT_POPUP = QToolButton.InstantPopup

    # timespec
    QT_TIMESPEC_LOCAL_TIME = Qt.LocalTime
    QT_TIMESPEC_UTC = Qt.UTC
    QT_TIMESPEC_OFFSET_FROM_UTC = Qt.OffsetFromUTC

    # qitemselectionmodel
    QT_ITEM_SELECTION_NO_UPDATE = QItemSelectionModel.NoUpdate
    QT_ITEM_SELECTION_CLEAR = QItemSelectionModel.Clear
    QT_ITEM_SELECTION_SELECT = QItemSelectionModel.Select
    QT_ITEM_SELECTION_DESELECT = QItemSelectionModel.Deselect
    QT_ITEM_SELECTION_TOGGLE = QItemSelectionModel.Toggle
    QT_ITEM_SELECTION_CURRENT = QItemSelectionModel.Current
    QT_ITEM_SELECTION_ROWS = QItemSelectionModel.Rows
    QT_ITEM_SELECTION_COLUMNS = QItemSelectionModel.Columns
    QT_ITEM_SELECTION_SELECT_CURRENT = QItemSelectionModel.SelectCurrent
    QT_ITEM_SELECTION_TOGGLE_CURRENT = QItemSelectionModel.ToggleCurrent
    QT_ITEM_SELECTION_CLEAR_AND_SELECT = QItemSelectionModel.ClearAndSelect

    # QStyle
    QT_STYLE_CC_SLIDER = QStyle.CC_Slider
    QT_STYLE_SP_DIR_OPEN_ICON = QStyle.SP_DirOpenIcon
    QT_STYLE_STATE_SELECTED = QStyle.State_Selected
    QT_STYLE_SC_SLIDER_HANDLE = QStyle.SC_SliderHandle

    # qdatetimeedit
    QT_DATE_TIME_EDIT_NO_SECTION = QDateTimeEdit.NoSection
    QT_DATE_TIME_EDIT_AM_PM_SECTION = QDateTimeEdit.AmPmSection
    QT_DATE_TIME_EDIT_MSEC_SECTION = QDateTimeEdit.MSecSection
    QT_DATE_TIME_EDIT_SECOND_SECTION = QDateTimeEdit.SecondSection
    QT_DATE_TIME_EDIT_MINUTE_SECTION = QDateTimeEdit.MinuteSection
    QT_DATE_TIME_EDIT_HOUR_SECTION = QDateTimeEdit.HourSection
    QT_DATE_TIME_EDIT_DAY_SECTION = QDateTimeEdit.DaySection
    QT_DATE_TIME_EDIT_MONTH_SECTION = QDateTimeEdit.MonthSection
    QT_DATE_TIME_EDIT_YEAR_SECTION = QDateTimeEdit.YearSection

    # qformlayout
    QT_FORM_LAYOUT_FIELDS_STAY_AT_SIZE_HINT = QFormLayout.FieldsStayAtSizeHint
    QT_FORM_LAYOUT_EXPANDING_FIELDS_GROW = QFormLayout.ExpandingFieldsGrow
    QT_FORM_LAYOUT_ALL_NON_FIXED_FIELDS_GROW = QFormLayout.AllNonFixedFieldsGrow
    QT_FORM_LAYOUT_LABEL_ROLE = QFormLayout.LabelRole
    QT_FORM_LAYOUT_FIELD_ROLE = QFormLayout.FieldRole
    QT_FORM_LAYOUT_SPANNING_ROLE = QFormLayout.SpanningRole
    QT_FORM_LAYOUT_DONT_WRAP_ROWS = QFormLayout.DontWrapRows
    QT_FORM_LAYOUT_WRAP_LONG_ROWS = QFormLayout.WrapLongRows
    QT_FORM_LAYOUT_WRAP_ALL_ROWS = QFormLayout.WrapAllRows

    # qdialog
    QT_DIALOG_ACCEPTED = QDialog.Accepted
    QT_DIALOG_REJECTED = QDialog.Rejected

    # qdialogbuttonbox
    QT_BUTTON_BOX_WIN_LAYOUT = QDialogButtonBox.WinLayout
    QT_BUTTON_BOX_MAC_LAYOUT = QDialogButtonBox.MacLayout
    QT_BUTTON_BOX_KDE_LAYOUT = QDialogButtonBox.KdeLayout
    QT_BUTTON_BOX_GNOME_LAYOUT = QDialogButtonBox.GnomeLayout
    QT_BUTTON_BOX_ANDROID_LAYOUT = QDialogButtonBox.AndroidLayout
    QT_BUTTON_BOX_INVALID_ROLE = QDialogButtonBox.InvalidRole
    QT_BUTTON_BOX_ACCEPT_ROLE = QDialogButtonBox.AcceptRole
    QT_BUTTON_BOX_REJECT_ROLE = QDialogButtonBox.RejectRole
    QT_BUTTON_BOX_DESTRUCTIVE_ROLE = QDialogButtonBox.DestructiveRole
    QT_BUTTON_BOX_ACTION_ROLE = QDialogButtonBox.ActionRole
    QT_BUTTON_BOX_HELP_ROLE = QDialogButtonBox.HelpRole
    QT_BUTTON_BOX_YES_ROLE = QDialogButtonBox.YesRole
    QT_BUTTON_BOX_NO_ROLE = QDialogButtonBox.NoRole
    QT_BUTTON_BOX_APPLY_ROLE = QDialogButtonBox.ApplyRole
    QT_BUTTON_BOX_RESET_ROLE = QDialogButtonBox.ResetRole
    QT_BUTTON_BOX_OK = QDialogButtonBox.Ok
    QT_BUTTON_BOX_OPEN = QDialogButtonBox.Open
    QT_BUTTON_BOX_SAVE = QDialogButtonBox.Save
    QT_BUTTON_BOX_CANCEL = QDialogButtonBox.Cancel
    QT_BUTTON_BOX_CLOSE = QDialogButtonBox.Close
    QT_BUTTON_BOX_DISCARD = QDialogButtonBox.Discard
    QT_BUTTON_BOX_APPLY = QDialogButtonBox.Apply
    QT_BUTTON_BOX_RESET = QDialogButtonBox.Reset
    QT_BUTTON_BOX_RESTORE_DEFUALTS = QDialogButtonBox.RestoreDefaults
    QT_BUTTON_BOX_HELP = QDialogButtonBox.Help
    QT_BUTTON_BOX_SAVE_ALL = QDialogButtonBox.SaveAll
    QT_BUTTON_BOX_YES = QDialogButtonBox.Yes
    QT_BUTTON_BOX_YES_TO_ALL = QDialogButtonBox.YesToAll
    QT_BUTTON_BOX_NO = QDialogButtonBox.No
    QT_BUTTON_BOX_NO_TO_ALL = QDialogButtonBox.NoToAll
    QT_BUTTON_BOX_ABORT = QDialogButtonBox.Abort
    QT_BUTTON_BOX_RETRY = QDialogButtonBox.Retry
    QT_BUTTON_BOX_IGNORE = QDialogButtonBox.Ignore
    QT_BUTTON_BOX_NO_BUTTON = QDialogButtonBox.NoButton

    # qmessagebox
    QT_MESSAGE_BOX_INVALID_ROLE = QMessageBox.InvalidRole
    QT_MESSAGE_BOX_ACCEPT_ROLE = QMessageBox.AcceptRole
    QT_MESSAGE_BOX_REJECT_ROLE = QMessageBox.RejectRole
    QT_MESSAGE_BOX_DESTRUCTIVE_ROLE = QMessageBox.DestructiveRole
    QT_MESSAGE_BOX_ACTION_ROLE = QMessageBox.ActionRole
    QT_MESSAGE_BOX_HELP_ROLE = QMessageBox.HelpRole
    QT_MESSAGE_BOX_YES_ROLE = QMessageBox.YesRole
    QT_MESSAGE_BOX_NO_ROLE = QMessageBox.NoRole
    QT_MESSAGE_BOX_APPLY_ROLE = QMessageBox.ApplyRole
    QT_MESSAGE_BOX_RESET_ROLE = QMessageBox.ResetRole
    QT_MESSAGE_BOX_NO_ICON = QMessageBox.NoIcon
    QT_MESSAGE_BOX_QUESTION = QMessageBox.Question
    QT_MESSAGE_BOX_INFORMATION = QMessageBox.Information
    QT_MESSAGE_BOX_WARNING = QMessageBox.Warning
    QT_MESSAGE_BOX_CRITICAL = QMessageBox.Critical
    QT_MESSAGE_BOX_OK = QMessageBox.Ok
    QT_MESSAGE_BOX_OPEN = QMessageBox.Open
    QT_MESSAGE_BOX_SAVE = QMessageBox.Save
    QT_MESSAGE_BOX_CANCEL = QMessageBox.Cancel
    QT_MESSAGE_BOX_CLOSE = QMessageBox.Close
    QT_MESSAGE_BOX_DISCARD = QMessageBox.Discard
    QT_MESSAGE_BOX_APPLY = QMessageBox.Apply
    QT_MESSAGE_BOX_RESET = QMessageBox.Reset
    QT_MESSAGE_BOX_RESTORE_DEFUALTS = QMessageBox.RestoreDefaults
    QT_MESSAGE_BOX_HELP = QMessageBox.Help
    QT_MESSAGE_BOX_SAVE_ALL = QMessageBox.SaveAll
    QT_MESSAGE_BOX_YES = QMessageBox.Yes
    QT_MESSAGE_BOX_YES_TO_ALL = QMessageBox.YesToAll
    QT_MESSAGE_BOX_NO = QMessageBox.No
    QT_MESSAGE_BOX_NO_TO_ALL = QMessageBox.NoToAll
    QT_MESSAGE_BOX_ABORT = QMessageBox.Abort
    QT_MESSAGE_BOX_RETRY = QMessageBox.Retry
    QT_MESSAGE_BOX_IGNORE = QMessageBox.Ignore
    QT_MESSAGE_BOX_NO_BUTTON = QMessageBox.NoButton

    # qpalette
    QT_PALETTE_DISABLED = QPalette.Disabled
    QT_PALETTE_ACTIVE = QPalette.Active
    QT_PALETTE_INACTIVE = QPalette.Inactive
    QT_PALETTE_NORMAL = QPalette.Normal
    QT_PALETTE_WINDOW_TEXT = QPalette.WindowText
    QT_PALETTE_WINDOW = QPalette.Window
    QT_PALETTE_BASE = QPalette.Base
    QT_PALETTE_ALTERNATE_BASE = QPalette.AlternateBase
    QT_PALETTE_TOOLTIP_BASE = QPalette.ToolTipBase
    QT_PALETTE_TOOLTIP_TEXT = QPalette.ToolTipText
    QT_PALETTE_PLACEHOLDER_TEXT = QPalette.PlaceholderText
    QT_PALETTE_BUTTON_TEXT = QPalette.ButtonText
    QT_PALETTE_TEXT = QPalette.Text
    QT_PALETTE_BUTTON = QPalette.Button
    QT_PALETTE_BRIGHT_TEXT = QPalette.BrightText
    QT_PALETTE_LIGHT = QPalette.Light
    QT_PALETTE_MID_LIGHT = QPalette.Midlight
    QT_PALETTE_DARK = QPalette.Dark
    QT_PALETTE_MID = QPalette.Mid
    QT_PALETTE_SHADOW = QPalette.Shadow
    QT_PALETTE_HIGHLIGHT = QPalette.Highlight
    QT_PALETTE_HIGHLIGHTED_TEXT = QPalette.HighlightedText
    QT_PALETTE_LINK = QPalette.Link
    QT_PALETTE_LINK_VISITED = QPalette.LinkVisited
    QT_PALETTE_NO_ROLE = QPalette.NoRole

    # qfont
    QT_FONT_MIXED_CASE = QFont.MixedCase
    QT_FONT_ALL_UPPER = QFont.AllUppercase
    QT_FONT_ALL_LOWER = QFont.AllLowercase
    QT_FONT_SMALL_CAPS = QFont.SmallCaps
    QT_FONT_CAPITALIZE = QFont.Capitalize
    QT_FONT_PREFER_DEFAULT_HINTING = QFont.PreferDefaultHinting
    QT_FONT_PREFER_NO_HINTING = QFont.PreferNoHinting
    QT_FONT_PREFER_VERTICAL_HINTING = QFont.PreferVerticalHinting
    QT_FONT_PREFER_FULL_HINTING = QFont.PreferFullHinting
    QT_FONT_PERCENTAGE_SPACING = QFont.PercentageSpacing
    QT_FONT_ABSOLUTE_SPACING = QFont.AbsoluteSpacing
    QT_FONT_ANY_STRETCH = QFont.AnyStretch
    QT_FONT_ULTRA_CONDENSED = QFont.UltraCondensed
    QT_FONT_EXTRA_CONDENSED = QFont.ExtraCondensed
    QT_FONT_CONDENSED = QFont.Condensed
    QT_FONT_SEMI_CONDENSED = QFont.SemiCondensed
    QT_FONT_UNSTRETCHED = QFont.Unstretched
    QT_FONT_SEMI_EXPANDED = QFont.SemiExpanded
    QT_FONT_EXPANDED = QFont.Expanded
    QT_FONT_EXTRA_EXPANDED = QFont.ExtraExpanded
    QT_FONT_ULTRA_EXPANDED = QFont.UltraExpanded
    QT_FONT_STYLE_NORMAL = QFont.StyleNormal
    QT_FONT_STYLE_ITALIC = QFont.StyleItalic
    QT_FONT_STYLE_OBLIQUE = QFont.StyleOblique
    QT_FONT_ANY_STYLE = QFont.AnyStyle
    QT_FONT_SANS_SERIF = QFont.SansSerif
    QT_FONT_HELVETICA = QFont.Helvetica
    QT_FONT_SERIF = QFont.Serif
    QT_FONT_TIMES = QFont.Times
    QT_FONT_TYPEWRITER = QFont.TypeWriter
    QT_FONT_COURIER = QFont.Courier
    QT_FONT_OLD_ENGLISH = QFont.OldEnglish
    QT_FONT_DECORATIVE = QFont.Decorative
    QT_FONT_MONOSPACE = QFont.Monospace
    QT_FONT_FANTASY = QFont.Fantasy
    QT_FONT_CURSIVE = QFont.Cursive
    QT_FONT_SYSTEM = QFont.System
    QT_FONT_PREFER_DEFAULT = QFont.PreferDefault
    QT_FONT_PREFER_BITMAP = QFont.PreferBitmap
    QT_FONT_PREFER_DEVICE = QFont.PreferDevice
    QT_FONT_PREFER_OUTLINE = QFont.PreferOutline
    QT_FONT_FORCE_OUTLINE = QFont.ForceOutline
    QT_FONT_NO_ANTIALIAS = QFont.NoAntialias
    QT_FONT_NO_SUBPIXEL_ANTIALIAS = QFont.NoSubpixelAntialias
    QT_FONT_PREFER_ANTIALIAS = QFont.PreferAntialias
    QT_FONT_NO_FONT_MERGING = QFont.NoFontMerging
    QT_FONT_PREFER_NO_SHAPING = QFont.PreferNoShaping
    QT_FONT_PREFER_MATCH = QFont.PreferMatch
    QT_FONT_PREFER_QUALITY = QFont.PreferQuality
    QT_FONT_THIN = QFont.Thin
    QT_FONT_EXTRA_LIGHT = QFont.ExtraLight
    QT_FONT_LIGHT = QFont.Light
    QT_FONT_NORMAL = QFont.Normal
    QT_FONT_MEDIUM = QFont.Medium
    QT_FONT_DEMI_BOLD = QFont.DemiBold
    QT_FONT_BOLD = QFont.Bold
    QT_FONT_EXTRA_BOLD = QFont.ExtraBold
    QT_FONT_BLACK = QFont.Black

    # qimage
    QT_IMAGE_FORMAT_ARGB32 = QImage.Format_ARGB32

    # qeventloop
    QT_EVENT_LOOP_EXCLUDE_USER_INPUT_EVENTS = QEventLoop.ExcludeUserInputEvents

    # qnetworkrequest
    QT_NETWORK_REQUEST_HTTP_STATUS_CODE_ATTRIBUTE = QNetworkRequest.HttpStatusCodeAttribute

    # qabstractscrollarea
    QT_ABSTRACT_SCROLL_AREA_ADJUST_IGNORED = QAbstractScrollArea.AdjustIgnored
    QT_ABSTRACT_SCROLL_AREA_ADJUST_TO_CONTENTS_ON_FIRST_SHOW = QAbstractScrollArea.AdjustToContentsOnFirstShow
    QT_ABSTRACT_SCROLL_AREA_ADJUST_TO_CONTENTS = QAbstractScrollArea.AdjustToContents

    # qabstractspinbox
    QT_ABSTRACT_SPIN_BOX_UP_DOWN_ARROWS = QAbstractSpinBox.UpDownArrows
    QT_ABSTRACT_SPIN_BOX_PLUS_MINUS = QAbstractSpinBox.PlusMinus
    QT_ABSTRACT_SPIN_BOX_NO_BUTTONS = QAbstractSpinBox.NoButtons
    QT_ABSTRACT_SPIN_BOX_CORRECT_TO_PREV_VALUE = QAbstractSpinBox.CorrectToPreviousValue
    QT_ABSTRACT_SPIN_BOX_CORRECT_TO_NEAREST_VALUE = QAbstractSpinBox.CorrectToNearestValue
    QT_ABSTRACT_SPIN_BOX_STEP_NONE = QAbstractSpinBox.StepNone
    QT_ABSTRACT_SPIN_BOX_STEP_UP_ENABLED = QAbstractSpinBox.StepUpEnabled
    QT_ABSTRACT_SPIN_BOX_STEP_DOWN_ENABLED = QAbstractSpinBox.StepDownEnabled
    QT_ABSTRACT_SPIN_BOX_DEFAULT_STEP_TYPE = QAbstractSpinBox.DefaultStepType
    QT_ABSTRACT_SPIN_BOX_ADAPTIVE_DECIMAL_STEP_TYPE = QAbstractSpinBox.AdaptiveDecimalStepType

    # qfiledialog
    QT_FILE_DIALOG_DONT_CONFIRM_OVERWRITE = QFileDialog.DontConfirmOverwrite
    QT_FILE_DIALOG_ACCEPT_OPEN = QFileDialog.AcceptOpen
    QT_FILE_DIALOG_ACCEPT_SAVE = QFileDialog.AcceptSave
    QT_FILE_DIALOG_ANY_FILE = QFileDialog.AnyFile
    QT_FILE_DIALOG_EXISTONG_FILES = QFileDialog.ExistingFiles
    QT_FILE_DIALOG_EXISTING_FILE = QFileDialog.ExistingFile
    QT_FILE_DIALOG_DIRECTORY = QFileDialog.Directory
    QT_FILE_DIALOG_DETAIL = QFileDialog.Detail
    QT_FILE_DIALOG_SHOW_DIRS_ONLY = QFileDialog.ShowDirsOnly

    QT_WA_STYLED_BACKGROUND = Qt.WA_StyledBackground

    QT_TOP_RIGHT_CORNER = Qt.Corner.TopRightCorner
    QT_BOTTOM_RIGHT_CORNER = Qt.Corner.BottomRightCorner
    QT_BOTTOM_LEFT_CORNER = Qt.Corner.BottomLeftCorner
    QT_TOP_LEFT_CORNER = Qt.Corner.TopLeftCorner

    # qtabwidget
    QT_TAB_WIDGET_ROUNDED = QTabWidget.Rounded
    QT_TAB_WIDGET_TRIANGULAR = QTabWidget.Triangular

    # qpainter
    QT_PAINTER_ANTIALIASING = QPainter.Antialiasing

    QT_KEEP_ASPECT_RATIO = Qt.KeepAspectRatio

# end PyQt5/PyQt6 enumerators


class GPKG:
    """A class that helps with GPKGs."""

    def __init__(self, gpkg_path):
        self.gpkg_path = str(gpkg_path)

    def glob(self, pattern):
        """Do a glob search of the database for tables matching the pattern."""

        p = pattern.replace('*', '.*')
        for lyr in self.layers():
            if re.findall(p, lyr, flags=re.IGNORECASE):
                yield lyr

    def layers(self):
        """Return the GPKG layers in the database."""

        res = []

        if not os.path.exists(self.gpkg_path):
            return res

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()

        try:
            cur.execute(f"SELECT table_name FROM gpkg_contents;")
            res = [x[0] for x in cur.fetchall()]
        except Exception:
            pass
        finally:
            cur.close()

        return res

    def vector_layers(self):
        import sqlite3
        res = []

        if not os.path.exists(self.gpkg_path):
            return res

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()

        try:
            cur.execute(
                f'SELECT contents.table_name FROM gpkg_contents AS contents '
                f'  INNER JOIN gpkg_geometry_columns AS columns ON contents.table_name = columns.table_name '
                f' WHERE columns.geometry_type_name != "GEOMETRY";'
            )
            res = [x[0] for x in cur.fetchall()]
        except Exception:
            pass
        finally:
            cur.close()

        return res

    def raster_layers(self):
        import sqlite3
        res = []

        if not os.path.exists(self.gpkg_path):
            return res

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()

        try:
            cur.execute(
                f'SELECT table_name FROM gpkg_contents WHERE data_type = "2d-gridded-coverage";'
            )
            res = cur.fetchall()
            if res:
                res = [x[0] for x in res]
            else:
                res = []
        except Exception:
            pass
        finally:
            cur.close()

        return res

    def non_spatial_layers(self):
        import sqlite3
        res = []

        if not os.path.exists(self.gpkg_path):
            return res

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()

        try:
            cur.execute(
                f'SELECT contents.table_name FROM gpkg_contents AS contents '
                f'  INNER JOIN gpkg_geometry_columns AS columns ON contents.table_name = columns.table_name '
                f' WHERE columns.geometry_type_name = "GEOMETRY";'
            )
            res = [x[0] for x in cur.fetchall()]
        except Exception:
            pass
        finally:
            cur.close()

        return res

    def geometry_type(self, layer_name):
        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT geometry_type_name FROM gpkg_geometry_columns where table_name = '{layer_name}';")
            res = [x[0] for x in cur.fetchall()][0]
        except Exception:
            pass
        finally:
            res = ''
            cur.close()

        return res

    def __contains__(self, item):
        """Returns a bool on whether a certain layer is in the database."""

        if not os.path.exists(self.gpkg_path):
            return False

        conn = sqlite3.connect(self.gpkg_path)
        cur = conn.cursor()
        res = None
        try:
            cur.execute(f"SELECT table_name FROM gpkg_contents WHERE table_name='{item}';")
            res = [x[0] for x in cur.fetchall()]
        except:
            pass
        finally:
            cur.close()

        return bool(res)


def gdal_error_handler(err_class: int, err_num: int, err_msg: str) -> None:
    """Custom python gdal error handler - if there is a failure, need to let GDAL finish first."""

    errtype = {
            gdal.CE_None:'None',
            gdal.CE_Debug:'Debug',
            gdal.CE_Warning:'Warning',
            gdal.CE_Failure:'Failure',
            gdal.CE_Fatal:'Fatal'
    }
    err_msg = err_msg.replace('\n',' ')
    err_class = errtype.get(err_class, 'None')
    if err_class.lower() == 'failure':
        global b_gdal_error
        b_gdal_error = True

    # skip these warning msgs
    if 'Normalized/laundered field name:' in err_msg:
        return
    if 'width 256 truncated to 254' in err_msg:
        return

    print('GDAL {0}'.format(err_class.upper()))
    print('{1} Number: {0}'.format(err_num, err_class))
    print('{1} Message: {0}'.format(err_msg, err_class))


def init_gdal_error_handler() -> None:
    """Initialise GDAL error handler"""

    global b_gdal_error
    b_gdal_error = False
    gdal.PushErrorHandler(gdal_error_handler)


def gdal_error() -> bool:
    """Returns a bool if there was a GDAL error or not"""

    global b_gdal_error
    try:
        return b_gdal_error
    except NameError:  # uninitialised
        init_gdal_error_handler()
        return gdal_error()


def get_database_name(file):
    """Strip the file reference into database name >> layer name."""

    if re.findall(r'\s+>>\s+', str(file)):
        return re.split(r'\s+>>\s+', str(file), 1)
    else:
        if Path(file).suffix.upper() == '.PRJ':
            file = Path(file).with_suffix('.shp')
        return [str(file), Path(file).stem]


def is_multi_part(feat=None, lyr=None):
    MULTIPART = [ogr.wkbMultiPoint, ogr.wkbMultiLineString, ogr.wkbMultiPolygon]
    if feat is not None and feat.geometry() is not None:
        return ogr_basic_geom_type(feat.geometry().GetGeometryType(), False) in MULTIPART

    if lyr is not None:
        return bool([f for f in lyr if ogr_basic_geom_type(f.geometry().GetGeometryType(), False) in MULTIPART])

    return False


def ogr_format(file, no_ext_is_mif=False, no_ext_is_gpkg=False):
    """Returns the OGR driver name based on the extension of the file reference."""

    db, layer = get_database_name(file)
    if Path(db).suffix.upper() in ['.SHP', '.PRJ']:
        return GIS_SHP
    if Path(db).suffix.upper() in ['.MIF', '.MID']:
        return GIS_MIF
    if Path(db).suffix.upper() == '.GPKG':
        return GIS_GPKG
    if Path(db).suffix.upper() == '' and no_ext_is_mif:
        return GIS_MIF
    if Path(db).suffix.upper() == '' and no_ext_is_gpkg:
        return GIS_GPKG

    if not Path(db).suffix.upper():
        raise Exception(f'Error: Unable to determine Vector format from blank file extension: {db}')

    raise Exception(f'Error: Vector format not supported by TUFLOW: {Path(db).suffix}')


def ogr_format_2_ext(ogr_format):
    """Convert OGR driver name to a file extension."""

    if ogr_format == GIS_SHP:
        return '.shp'
    if ogr_format == GIS_MIF:
        return '.mif'
    if ogr_format == GIS_GPKG:
        return '.gpkg'


def ogr_basic_geom_type(geom_type, force_single_part=True):
    """Convert OGR geometry type to a basic type e.g. PointM -> Point"""

    while geom_type - 1000 > 0:
        geom_type -= 1000

    if force_single_part:
        if geom_type == ogr.wkbMultiPoint:
            geom_type = ogr.wkbPoint
        elif geom_type == ogr.wkbMultiLineString:
            geom_type = ogr.wkbLineString
        elif geom_type == ogr.wkbMultiPolygon:
            geom_type = ogr.wkbPolygon

    return geom_type


def gis_manual_delete(file, fmt):
    """Manually delete a GIS file - can be required if GIS file is corrupt -> OGR won't delete it then."""

    file = Path(file)
    if fmt == GIS_MIF:
        for file in file.parent.re(rf'{re.escape(file.stem)}\.(mif|mid)', flags=re.IGNORECASE):
            file.unlink()
    elif fmt == GIS_SHP:
        for file in file.parent.re(rf'{re.escape(file.stem)}\.(shp|prj|dbf|shx|sbn|sbx)', flags=re.IGNORECASE):
            file.unlink()


def copy_field_defn(field_defn):
    """Copy field defn to new object."""

    new_field_defn = ogr.FieldDefn()
    new_field_defn.SetName(field_defn.GetName())
    new_field_defn.SetType(field_defn.GetType())
    new_field_defn.SetSubType(field_defn.GetSubType())
    new_field_defn.SetJustify(field_defn.GetJustify())
    new_field_defn.SetWidth(field_defn.GetWidth())
    new_field_defn.SetPrecision(field_defn.GetPrecision())
    new_field_defn.SetNullable(field_defn.IsNullable())
    new_field_defn.SetUnique(field_defn.IsUnique())
    new_field_defn.SetDefault(field_defn.GetDefault())
    new_field_defn.SetDomainName(field_defn.GetDomainName())

    return new_field_defn


def sanitise_field_defn(field_defn, fmt):
    """
    For MIF output only.
    MIF doesn't support all OGR field types, so convert fields to a simpler format that is compatible in MIF.
    """

    SHP_MAX_FIELD_NAME_LEN = 10

    if fmt == GIS_MIF:
        if field_defn.type in [ogr.OFTInteger64, ogr.OFTIntegerList, ogr.OFTInteger64List]:
            field_defn.type = ogr.OFTInteger
        elif field_defn.type in [ogr.OFTRealList]:
            field_defn.type = ogr.OFTReal
        elif field_defn.type in [ogr.OFTStringList, ogr.OFTWideString, ogr.OFTWideStringList]:
            field_defn.type = ogr.OFTString

    if fmt == GIS_SHP:
        if len(field_defn.name) > SHP_MAX_FIELD_NAME_LEN:
            field_defn.name = field_defn.name[:SHP_MAX_FIELD_NAME_LEN]

    return field_defn


def suffix_2_geom_type(suffix):
    """Convert OGR geometry type to TUFLOW suffix."""

    if suffix == '_P':
        return ogr.wkbPoint
    if suffix == '_L':
        return ogr.wkbLineString
    if suffix == '_R':
        return ogr.wkbPolygon


def tuflow_type_requires_feature_iter(layername):
    """
    Returns the indexes of fields that could require a file copy e.g. for 1d_xs.

    This will require manual feature iteration and copy in the OGR copy routine.
    """

    req_iter_types = {
        r'^1d_nwk[eb]?_': [10],
        r'^1d_pit_': [3],
        r'^1d_(xs|tab|xz|bg|lc|cs|hw)_': [0],
        r'^1d_na_': [0]
    }

    for pattern, indexes in req_iter_types.items():
        if re.findall(pattern, layername, flags=re.IGNORECASE):
            return indexes

    return []


def globify(infile, wildcards):
    """Converts TUFLOW wildcards (variable names, scenario/event names) to '*' for glob pattern."""

    infile = str(infile)
    if wildcards is None:
        return infile

    for wc in wildcards:
        infile = re.sub(wc, '*', infile, flags=re.IGNORECASE)
    if re.findall(r'\*\*(?![\\/])', infile):
        infile = re.sub(re.escape(r'**'), '*', infile)

    return infile


def copy_file(parent_file, rel_path, output_parent, wildcards):
    """Copy file routine that will also expand glob patterns."""

    file_dest = None
    rel_path_ = globify(rel_path, wildcards)
    copy_count = None
    try:
        if output_parent is not None:
            for copy_count, file_src in enumerate(parent_file.parent.glob(rel_path_)):
                file_src = file_src.resolve()
                rp = os.path.relpath(file_src, parent_file.parent)
                file_dest = (output_parent.parent / rp).resolve()
                file_dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file_src, file_dest)
    except Exception as e:
        raise Exception(f'Error: {e}')

    if copy_count is not None:
        return file_dest
    else:
        return None


def copy_file2(file_src, file_dest):
    """More basic copy file routine with a different signature. Does not expand glob."""

    try:
        file_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file_src, file_dest)
    except Exception as e:
        raise Exception(f'Error: {e}')


def ogr_copy(src_file, dest_file, geom=None, settings=None, **kwargs):
    """
    Copy vector file from one format to another (or the same format).

    If converting from a MIF file, geom should be specified to indicate which geometry type to copy across.

    Some TUFLOW layers (1d_nwk, 1d_tab) contain references to files, these will also be copied and references
    updated if required (output layer can be in a different folder if it's going to a centralised database).
    """

    db_in, lyrname_in = get_database_name(src_file)
    db_out, lyrname_out = get_database_name(dest_file)

    prj_only = False
    sr = None
    if Path(db_in).suffix.upper() == '.PRJ' and not Path(db_in).with_suffix('.shp').exists() and Path(db_out).suffix.upper() == '.SHP':
        if settings and settings.force_projection:
            sr = osr.SpatialReference()
            sr.ImportFromWkt(settings.projection_wkt)
            if not Path(db_out).parent.exists():
                Path(db_out).parent.mkdir(parents=True)
            ds = ogr.GetDriverByName('ESRI Shapefile').CreateDataSource(str(Path(db_out).with_suffix('.shp')))
            if ds is None or gdal_error():
                raise Exception(f'Error: Failed to open: {db_out}')
            lyr = ds.CreateLayer(Path(db_in).stem, sr, ogr.wkbPoint)
            if lyr is None or gdal_error():
                raise Exception(f'Error: Failed to create layer: {Path(db_in).stem}')
            ds, lyr = None, None
        else:
            copy_file2(Path(db_in), Path(db_out).with_suffix('.prj'))
        return
    elif Path(db_in).suffix.upper() == '.PRJ' and not Path(db_in).with_suffix('.shp').exists():
        if settings and settings.force_projection:
            sr = osr.SpatialReference()
            sr.ImportFromWkt(settings.projection_wkt)
        else:
            with open(db_in, 'r') as f:
                try:
                    sr = osr.SpatialReference(f.readline())
                except Exception as e:
                    raise Exception(f'Error reading spatial reference.\n{e}')
        prj_only = True
    elif Path(db_in).suffix.upper() == '.PRJ':
        db_in = str(Path(db_in).with_suffix('.shp'))
    elif Path(db_in).suffix.upper() == '.MID':
        db_in = str(Path(db_in).with_suffix('.mif'))

    lyr_in = None
    fmt_in = ogr_format(db_in)
    if not prj_only:
        driver_in = ogr.GetDriverByName(fmt_in)
        datasource_in = driver_in.Open(db_in)
        if gdal_error():
            if settings is not None:
                settings.errors = True
            raise Exception(f'Error: Failed to open {db_in}')
        lyr_in = datasource_in.GetLayer(lyrname_in)
        if gdal_error():
            if settings is not None:
                settings.errors = True
            raise Exception(f'Error: Failed to open layer {lyrname_in}')

    fmt_out = ogr_format(db_out)
    driver_out = ogr.GetDriverByName(fmt_out)
    if Path(db_out).exists() and fmt_out == GIS_GPKG:
        datasource_out = driver_out.Open(db_out, 1)
    elif Path(db_out).exists():
        datasource_out = driver_out.Open(db_out, 1)
        if datasource_out is not None:
            datasource_out.DeleteLayer(0)
        elif fmt_out == GIS_MIF:
            try:
                err = driver_out.DeleteDataSource(db_out)
                if err != ogr.OGRERR_NONE:
                    gis_manual_delete(db_out, fmt_out)
            except Exception as e:
                if settings is not None:
                    settings.errors = True
                raise Exception(f'Error: Could not overwrite existing file: {db_out}')
            datasource_out = driver_out.CreateDataSource(db_out)
    else:
        Path(db_out).parent.mkdir(parents=True, exist_ok=True)
        datasource_out = driver_out.CreateDataSource(db_out)
    if gdal_error():
        if settings is not None:
            settings.errors = True
        raise Exception(f'Error: Failed to open: {db_out}')

    options = ['OVERWRITE=YES'] if fmt_out == GIS_GPKG else []
    geom_type = 0
    if lyr_in is not None:
        geom_type = geom if geom is not None else lyr_in.GetGeomType()
    elif prj_only:
        geom_type = ogr.wkbPoint

    file_indexes = tuflow_type_requires_feature_iter(lyrname_in)  # is there a file reference in the features
    wildcards = settings.wildcards if settings else []

    # if fmt_out == GIS_MIF or fmt_in == GIS_MIF or prj_only or file_indexes or is_multi_part(lyr=lyr_in):
    if settings is not None and settings.force_projection:
        sr = osr.SpatialReference()
        sr.ImportFromWkt(settings.projection_wkt)
    elif sr is None and lyr_in is not None:
        sr = lyr_in.GetSpatialRef()
    lyr_out = datasource_out.CreateLayer(lyrname_out, sr, geom_type, options)
    if gdal_error():
        if settings is not None:
            settings.errors = True
        raise Exception(f'Error: Failed to create layer {lyrname_out}')
    if prj_only:
        fielDefn = ogr.FieldDefn('ID', ogr.OFTString)
        lyr_out.CreateField(fielDefn)
    else:
        layer_defn = lyr_in.GetLayerDefn()
        for i in range(0, layer_defn.GetFieldCount()):
            fieldDefn = copy_field_defn(layer_defn.GetFieldDefn(i))
            fieldDefn = sanitise_field_defn(fieldDefn, fmt_out)
            lyr_out.CreateField(fieldDefn)
        if fmt_out == GIS_GPKG:
            datasource_out.StartTransaction()
        for feat in lyr_in:
            if geom and ogr_basic_geom_type(feat.geometry().GetGeometryType()) != geom_type:
                continue

            if is_multi_part(feat) and not kwargs.get('explode_multipart') == False:  # double negative, but the default is to explode
                geom_parts = [x for x in feat.GetGeometryRef()]
            else:
                geom_parts = [feat.GetGeometryRef()]

            for gp in geom_parts:
                new_feat = ogr.Feature(lyr_out.GetLayerDefn())
                panMap = list(range(feat.GetFieldCount()))
                new_feat.SetFromWithMap(feat, True, panMap)
                new_feat.SetGeometry(gp)

                if not kwargs.get('copy_associated_files') == False:  # double negative, but default should be to copy
                    for i in file_indexes:  # check if there's a file that needs to be copied e.g. 1d_xs.csv
                        if feat[i]:
                            if '|' in feat[i]:
                                op, file = [x.strip() for x in feat[i].split('|', 1)]
                            else:
                                op, file = None, feat[i]
                            dest_file = (Path(db_out).parent / file).resolve()
                            dest_file2 = Path(dest_file)
                            if settings:
                                rel_path = os.path.relpath((Path(db_in).parent / file).resolve(), settings.root_folder)
                                dest_file2 = (settings.output_folder / rel_path).resolve()
                            if dest_file == dest_file2:
                                copy_file(Path(db_in), file, Path(db_out), wildcards)
                            else:  # this means that we are using a grouped database that will screw up copy - req correction
                                rel_path = os.path.relpath(db_in, settings.root_folder)
                                fake_db_out = (Path(settings.output_folder) / rel_path).resolve()
                                copy_file(Path(db_in), file, fake_db_out, wildcards)
                                if op is None:
                                    new_feat[i] = os.path.relpath(dest_file2, Path(db_out).parent)
                                else:
                                    new_feat[i] = f'{op} | {os.path.relpath(dest_file2, Path(db_out).parent)}'

                lyr_out.CreateFeature(new_feat)

        if fmt_out == GIS_GPKG:
            datasource_out.CommitTransaction()

    datasource_out, lyr_out = None, None
    datasource_in, lyr_in = None, None