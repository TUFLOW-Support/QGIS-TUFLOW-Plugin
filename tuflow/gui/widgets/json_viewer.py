from __future__ import annotations

import json
from typing import Any

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QToolBar,
    QAction,
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QAbstractItemView,
    QHeaderView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QMenu,
)


# ── Column indices ────────────────────────────────────────────────────────────
_COL_KEY   = 0   # key / index
_COL_VALUE = 1   # leaf value (editable)
_COL_TYPE  = 2   # type label (string / number / bool / null / object / array)

# UserRole stores the type name; UserRole+1 flags an item as modified
_ROLE_TYPE     = Qt.ItemDataRole.UserRole
_ROLE_MODIFIED = Qt.ItemDataRole.UserRole + 1

# ── Type labels ───────────────────────────────────────────────────────────────
_LEAF_TYPES   = ["string", "number", "boolean", "null"]
_BRANCH_TYPES = ["object", "array"]

# Colour hints per type for a quick visual scan
_TYPE_COLORS: dict[str, QColor] = {
    "string":  QColor("#1a7f37"),
    "number":  QColor("#0550ae"),
    "boolean": QColor("#8250df"),
    "null":    QColor("#6e7781"),
    "object":  QColor("#953800"),
    "array":   QColor("#953800"),
}


# ── Serialisation helpers ─────────────────────────────────────────────────────

def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=None)


def _loads(text: str) -> Any:
    return json.loads(text)


# ── Tree ↔ Python object conversion ──────────────────────────────────────────

def _python_to_tree(
    parent: QTreeWidgetItem,
    key: str,
    value: Any,
) -> QTreeWidgetItem:
    """Recursively build a QTreeWidgetItem subtree from a Python value."""
    item = QTreeWidgetItem(parent)
    item.setText(_COL_KEY, str(key))
    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)

    if isinstance(value, dict):
        item.setText(_COL_TYPE, "object")
        item.setData(_COL_TYPE, _ROLE_TYPE, "object")
        item.setText(_COL_VALUE, "")
        for k, v in value.items():
            _python_to_tree(item, k, v)
    elif isinstance(value, list):
        item.setText(_COL_TYPE, "array")
        item.setData(_COL_TYPE, _ROLE_TYPE, "array")
        item.setText(_COL_VALUE, "")
        for i, v in enumerate(value):
            _python_to_tree(item, str(i), v)
    else:
        type_name = _type_name_of(value)
        item.setText(_COL_TYPE, type_name)
        item.setData(_COL_TYPE, _ROLE_TYPE, type_name)
        item.setText(_COL_VALUE, _value_display(value))

    _apply_type_colour(item)
    return item


def _type_name_of(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if value is None:
        return "null"
    return "string"


def _value_display(value: Any) -> str:
    """Human-readable string for a leaf value."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _display_to_python(text: str, type_name: str) -> Any:
    """Convert a display string back to a Python value given its type."""
    if type_name == "null":
        return None
    if type_name == "boolean":
        return text.strip().lower() in ("true", "1", "yes")
    if type_name == "number":
        try:
            v = float(text.strip())
            return int(v) if v == int(v) else v
        except ValueError:
            return 0
    return text  # string


def _tree_to_python(item: QTreeWidgetItem) -> Any:
    """Recursively convert a QTreeWidgetItem subtree to a Python value."""
    type_name = item.data(_COL_TYPE, _ROLE_TYPE) or "string"

    if type_name == "object":
        result = {}
        for i in range(item.childCount()):
            child = item.child(i)
            result[child.text(_COL_KEY)] = _tree_to_python(child)
        return result

    if type_name == "array":
        return [_tree_to_python(item.child(i)) for i in range(item.childCount())]

    return _display_to_python(item.text(_COL_VALUE), type_name)


def _apply_type_colour(item: QTreeWidgetItem) -> None:
    type_name = item.data(_COL_TYPE, _ROLE_TYPE) or "string"
    color = _TYPE_COLORS.get(type_name, QColor())
    item.setForeground(_COL_TYPE, color)
    item.setForeground(_COL_VALUE, color)


def _apply_modified_highlight(item: QTreeWidgetItem, colour: QColor) -> None:
    """Paint the background of all columns for a modified row."""
    for col in range(item.columnCount()):
        item.setBackground(col, colour)
    item.setData(_COL_KEY, _ROLE_MODIFIED, True)


def _clear_modified_highlight(item: QTreeWidgetItem) -> None:
    """Remove the modified background from a row."""
    for col in range(item.columnCount()):
        item.setBackground(col, QColor())  # transparent / default
    item.setData(_COL_KEY, _ROLE_MODIFIED, False)


def _convert_item_to_branch(item: QTreeWidgetItem, branch_type: str) -> None:
    """Convert any node (leaf or branch) to an object or array in-place.

    The item's key is preserved.  Any existing children are discarded
    (the caller should confirm with the user first if children exist).
    The value column is cleared and the type is updated to branch_type.
    """
    if branch_type not in _BRANCH_TYPES:
        raise AssertionError('branch_type no in _BRANCH_TYPES')
    # Remove all existing children
    for _ in range(item.childCount()):
        item.removeChild(item.child(0))
    item.setText(_COL_VALUE, "")
    item.setText(_COL_TYPE, branch_type)
    item.setData(_COL_TYPE, _ROLE_TYPE, branch_type)
    _apply_type_colour(item)
    item.setExpanded(True)


def _convert_item_to_leaf(item: QTreeWidgetItem, leaf_type: str) -> None:
    """Convert a branch node to a leaf in-place, discarding all children."""
    if leaf_type not in _LEAF_TYPES:
        raise AssertionError('leaf_type not in _LEAF_TYPES')
    for _ in range(item.childCount()):
        item.removeChild(item.child(0))
    item.setText(_COL_VALUE, "")
    item.setText(_COL_TYPE, leaf_type)
    item.setData(_COL_TYPE, _ROLE_TYPE, leaf_type)
    _apply_type_colour(item)


# ── Type-selector delegate for the Type column ────────────────────────────────

class _TypeDelegate(QStyledItemDelegate):
    """Shows a QComboBox in the Type column for leaf nodes."""

    def createEditor(self, parent, option: QStyleOptionViewItem, index):  # noqa: N802
        # Only allow editing leaf types (not object/array)
        current = index.data(Qt.ItemDataRole.DisplayRole) or ""
        if current in _BRANCH_TYPES:
            return None
        combo = QComboBox(parent)
        combo.addItems(_LEAF_TYPES)
        return combo

    def setEditorData(self, editor: QComboBox, index):  # noqa: N802
        current = index.data(Qt.ItemDataRole.DisplayRole) or "string"
        idx = editor.findText(current)
        if idx >= 0:
            editor.setCurrentIndex(idx)

    def setModelData(self, editor: QComboBox, model, index):  # noqa: N802
        value = editor.currentText()
        model.setData(index, value, Qt.ItemDataRole.DisplayRole)
        model.setData(index, value, _ROLE_TYPE)

        # QTreeWidget.itemFromIndex is available on the view, not the model
        tree_widget = self.parent()
        tree_item = tree_widget.itemFromIndex(index)
        if tree_item:
            _apply_type_colour(tree_item)
            # Reset the value column to a sensible default for the new type
            val_index = model.index(index.row(), _COL_VALUE, index.parent())
            current_text = val_index.data(Qt.ItemDataRole.DisplayRole) or ""
            model.setData(val_index, _value_display(_display_to_python(current_text, value)))
            # Notify the JsonWidget (grandparent of the delegate) so it can
            # apply the modified highlight if that feature is enabled.
            json_widget = tree_widget.parent()
            if isinstance(json_widget, JsonWidget):
                json_widget._on_item_modified(tree_item)


# ── Main widget ───────────────────────────────────────────────────────────────

class JsonWidget(QWidget):
    """JSON tree viewer/editor widget.

    Subclass and override :meth:`_extend_context_menu` to inject custom menu
    actions based on which node was right-clicked.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._highlight_changes = False
        self._highlight_colour  = QColor("#fff3cd")  # soft amber
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Toolbar — load file and expand/collapse only
        toolbar = QToolBar(self)
        toolbar.setIconSize(QSize(16, 16))

        self._act_expand   = QAction("⊞ Expand all", self)
        self._act_collapse = QAction("⊟ Collapse all", self)

        for act in (self._act_expand, self._act_collapse):
            toolbar.addAction(act)

        layout.addWidget(toolbar)

        # Tree
        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Key / Index", "Value", "Type"])
        self._tree.setAlternatingRowColors(True)
        self._tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self._tree.header().setStretchLastSection(True)
        self._tree.setMinimumHeight(350)
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 250)

        # Attach the type delegate to the Type column
        self._type_delegate = _TypeDelegate(self._tree)
        self._tree.setItemDelegateForColumn(_COL_TYPE, self._type_delegate)

        # Right-click context menu for structural conversions
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._on_context_menu)
        # Track inline edits for the modified-row highlight feature
        self._tree.itemChanged.connect(self._on_item_changed)

        layout.addWidget(self._tree)

        # Wire actions
        self._act_expand.triggered.connect(self._tree.expandAll)
        self._act_collapse.triggered.connect(self._tree.collapseAll)

        # Start with an empty object
        self.setValue("{}")

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def highlight_changes(self) -> bool:
        """Whether edited rows are highlighted to show they differ from default."""
        return self._highlight_changes

    @highlight_changes.setter
    def highlight_changes(self, enabled: bool) -> None:
        self._highlight_changes = enabled
        if not enabled:
            self._clear_all_modified()

    @property
    def highlight_colour(self) -> QColor:
        """Background colour used to mark a modified row (default: soft amber)."""
        return self._highlight_colour

    @highlight_colour.setter
    def highlight_colour(self, colour: QColor) -> None:
        self._highlight_colour = colour

    def value(self) -> str:
        """Return the current tree contents as a JSON string."""
        root = self._tree.invisibleRootItem()
        if root.childCount() == 0:
            return "null"
        if root.childCount() == 1:
            top = root.child(0)
            return _dumps(_tree_to_python(top))
        # Multiple top-level items: wrap in an object
        return _dumps(
            {root.child(i).text(_COL_KEY): _tree_to_python(root.child(i))
             for i in range(root.childCount())}
        )

    def setValue(
        self,
        json_text: str,
        *,
        retain_highlights: bool = False,
        highlight_new: bool = False,
    ) -> None:
        """Populate the tree from a JSON string, preserving collapsed state.

        Args:
            json_text:          JSON string to load.
            retain_highlights:  If ``True``, rows that were marked modified
                                before the rebuild are re-highlighted afterwards
                                (matched by key-path).  Defaults to ``False``.
            highlight_new:      If ``True``, every item created during this
                                rebuild is immediately highlighted as modified.
                                Defaults to ``False``.
        """
        collapsed = self._collapsed_paths()
        modified  = self._modified_paths() if retain_highlights else set()
        existing_paths = self._all_paths() if highlight_new else set()

        try:
            data = _loads(json_text)
        except (json.JSONDecodeError, TypeError):
            data = {}

        # Block signals for the entire rebuild to prevent re-entrant setValue
        # calls triggered by itemCollapsed/itemExpanded/itemChanged.
        self._tree.blockSignals(True)
        try:
            self._tree.clear()
            root = self._tree.invisibleRootItem()
            if isinstance(data, dict):
                for k, v in data.items():
                    _python_to_tree(root, k, v)
            elif isinstance(data, list):
                for i, v in enumerate(data):
                    _python_to_tree(root, str(i), v)
            else:
                _python_to_tree(root, "value", data)
            self._tree.expandAll()
            self._restore_collapsed(collapsed)
            if retain_highlights and modified:
                self._restore_modified(modified, self._highlight_colour)
            if highlight_new:
                self._highlight_new_items(existing_paths, self._highlight_colour)
        finally:
            self._tree.blockSignals(False)

    def valueAsDict(self) -> dict[str, Any]:
        try:
            val = _loads(self.value())
            return val
        except json.JSONDecodeError as e:
            from qgis.utils import iface
            if iface:
                iface.messageBar().pushWarning(
                f'JSON decode error', 'Error loading as json: {e}'
                )
            return {}

    def setValueFromDict(
            self, 
            val: dict[str, Any], 
            *, 
            retain_highlights: bool = False,
            highlight_new: bool = False
            ):
        try:
            string = _dumps(val)
            self.setValue(string, retain_highlights=retain_highlights, highlight_new=highlight_new)
        except json.JSONDecodeError as e:
            from qgis.utils import iface
            if iface:
                iface.messageBar().pushWarning(
                f'JSON decode error', 'Error convertint to json string: {e}'
                )

    # ── Handlers ──────────────────────────────────────────────────────────

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Called by itemChanged — mark the row as modified if feature is on."""
        self._on_item_modified(item)

    def _on_item_modified(self, item: QTreeWidgetItem) -> None:
        """Mark *item* as modified and apply the highlight colour if enabled."""
        if self._highlight_changes:
            _apply_modified_highlight(item, self._highlight_colour)
        value = item.text(_COL_VALUE)
        try:
            int(value)
            type_name = 'number'
        except (ValueError, TypeError):
            type_name = 'string'
        item.setText(_COL_TYPE, type_name)
        item.setData(_COL_TYPE, _ROLE_TYPE, type_name)

    def _clear_all_modified(self) -> None:
        """Remove modified highlights from every row in the tree."""
        def walk(node: QTreeWidgetItem) -> None:
            if node.data(_COL_KEY, _ROLE_MODIFIED):
                _clear_modified_highlight(node)
            for i in range(node.childCount()):
                walk(node.child(i))
        walk(self._tree.invisibleRootItem())

    def _on_context_menu(self, pos) -> None:
        """Right-click menu: add key/item, delete, and convert type."""
        item = self._tree.itemAt(pos)
        menu = QMenu(self._tree)
        global_pos = self._tree.viewport().mapToGlobal(pos)

        if item is not None:
            current_type = item.data(_COL_TYPE, _ROLE_TYPE) or "string"

            # Add child — shown only for the matching branch type
            if current_type == "object":
                menu.addAction("＋ Add key", lambda: self._add_key(item))
            elif current_type == "array":
                menu.addAction("＋ Add item", lambda: self._add_array_item(item))

            menu.addAction("🗑 Delete", lambda: self._delete_item(item))
            menu.addSeparator()

            # Convert to… submenu
            convert_menu = menu.addMenu("Convert to…")
            for branch_type in _BRANCH_TYPES:
                if current_type == branch_type:
                    continue
                act = convert_menu.addAction(branch_type.capitalize())
                act.triggered.connect(lambda checked=False, t=branch_type: self._do_convert(item, t))
            convert_menu.addSeparator()
            for leaf_type in _LEAF_TYPES:
                if current_type == leaf_type:
                    continue
                act = convert_menu.addAction(leaf_type.capitalize())
                act.triggered.connect(lambda checked=False, t=leaf_type: self._do_convert(item, t))

        else:
            # Clicked on empty space — offer top-level additions
            menu.addAction("＋ Add top-level key",  lambda: self._add_key(self._tree.invisibleRootItem()))
            menu.addAction("＋ Add top-level item", lambda: self._add_array_item(self._tree.invisibleRootItem()))

        self._extend_context_menu(menu, item, self._item_key_path(item))
        menu.exec(global_pos)

    # ── Extension hook ────────────────────────────────────────────────────

    def _extend_context_menu(
        self,
        menu: QMenu,
        item: QTreeWidgetItem | None,
        key_path: list[str],
    ) -> None:
        """Hook for subclasses to add custom context-menu actions.

        Called just before the menu is shown, after all built-in actions have
        been added.  Override this method — do **not** call ``menu.exec()``
        inside it.

        Args:
            menu:      The context menu being built.  Add actions to it
                       directly or via ``menu.addSeparator()`` /
                       ``menu.addMenu()``.
            item:      The ``QTreeWidgetItem`` that was right-clicked, or
                       ``None`` if the click landed on empty space.
            key_path:  Ordered list of key/index strings from the invisible
                       root down to *item*, e.g. ``["features", "0", "name"]``
                       for a grandchild.  Empty when *item* is ``None``.

        Example — add an action only on the top-level "features" array::

            def _extend_context_menu(self, menu, item, key_path):
                if key_path == ["features"]:
                    menu.addSeparator()
                    menu.addAction("Import feature", self._import_feature)
        """

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _item_key_path(item: QTreeWidgetItem | None) -> list[str]:
        """Return the list of keys from the root down to *item*.

        e.g. for root → "features" → 0 → "name"  returns  ["features", "0", "name"].
        Returns an empty list when *item* is ``None``.
        """
        if item is None:
            return []
        path: list[str] = []
        node: QTreeWidgetItem | None = item
        while node is not None:
            path.append(node.text(_COL_KEY))
            node = node.parent()
        path.reverse()
        return path

    def _add_key(self, parent_item: QTreeWidgetItem) -> None:
        """Add a new string-typed key under an object node."""
        key, ok = QInputDialog.getText(self, "Add key", "Key name:")
        if not ok or not key.strip():
            return
        child = QTreeWidgetItem(parent_item)
        child.setText(_COL_KEY, key.strip())
        child.setText(_COL_VALUE, "")
        child.setText(_COL_TYPE, "string")
        child.setData(_COL_TYPE, _ROLE_TYPE, "string")
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
        _apply_type_colour(child)
        parent_item.setExpanded(True)
        self._tree.scrollToItem(child)
        self._tree.setCurrentItem(child)

    def _add_array_item(self, parent_item: QTreeWidgetItem) -> None:
        """Append a new string-typed item to an array node."""
        idx = parent_item.childCount()
        child = QTreeWidgetItem(parent_item)
        child.setText(_COL_KEY, str(idx))
        child.setText(_COL_VALUE, "")
        child.setText(_COL_TYPE, "string")
        child.setData(_COL_TYPE, _ROLE_TYPE, "string")
        child.setFlags(child.flags() | Qt.ItemFlag.ItemIsEditable)
        _apply_type_colour(child)
        parent_item.setExpanded(True)
        self._tree.scrollToItem(child)
        self._tree.setCurrentItem(child)

    def _delete_item(self, item: QTreeWidgetItem) -> None:
        parent = item.parent() or self._tree.invisibleRootItem()
        parent.removeChild(item)
        self._renumber_array_indices()

    def _do_convert(self, item: QTreeWidgetItem, target_type: str) -> None:
        """Perform a type conversion with a confirmation guard if children exist."""
        if item.childCount() > 0:
            reply = QMessageBox.question(
                self,
                "Convert node",
                f"Converting to '{target_type}' will remove "
                f"{item.childCount()} child node(s). Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        if target_type in _BRANCH_TYPES:
            _convert_item_to_branch(item, target_type)
        else:
            _convert_item_to_leaf(item, target_type)
        self._on_item_modified(item)
        self._renumber_array_indices()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _all_paths(self) -> set[tuple[str, ...]]:
        """Return key-paths of every item currently in the tree."""
        paths: set[tuple[str, ...]] = set()

        def walk(item: QTreeWidgetItem) -> None:
            paths.add(tuple(self._item_key_path(item)))
            for i in range(item.childCount()):
                walk(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return paths

    def _highlight_new_items(
        self, existing_paths: set[tuple[str, ...]], colour: QColor
    ) -> None:
        """Highlight items whose key-paths were not in *existing_paths*."""
        def walk(item: QTreeWidgetItem) -> None:
            if tuple(self._item_key_path(item)) not in existing_paths:
                _apply_modified_highlight(item, colour)
            for i in range(item.childCount()):
                walk(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))

    def _collapsed_paths(self) -> set[tuple[str, ...]]:
        """Return the key-paths of all branch nodes that are currently collapsed."""
        collapsed: set[tuple[str, ...]] = set()

        def walk(item: QTreeWidgetItem) -> None:
            type_name = item.data(_COL_TYPE, _ROLE_TYPE)
            if type_name in _BRANCH_TYPES and not item.isExpanded():
                collapsed.add(tuple(self._item_key_path(item)))
            for i in range(item.childCount()):
                walk(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return collapsed

    def _restore_collapsed(self, collapsed: set[tuple[str, ...]]) -> None:
        """Collapse branch nodes whose key-paths appear in *collapsed*."""
        def walk(item: QTreeWidgetItem) -> None:
            if tuple(self._item_key_path(item)) in collapsed:
                item.setExpanded(False)
            for i in range(item.childCount()):
                walk(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))

    def _modified_paths(self) -> set[tuple[str, ...]]:
        """Return the key-paths of all rows currently marked as modified."""
        modified: set[tuple[str, ...]] = set()

        def walk(item: QTreeWidgetItem) -> None:
            if item.data(_COL_KEY, _ROLE_MODIFIED):
                modified.add(tuple(self._item_key_path(item)))
            for i in range(item.childCount()):
                walk(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))
        return modified

    def _restore_modified(
        self, modified: set[tuple[str, ...]], colour: QColor
    ) -> None:
        """Re-apply the modified highlight to rows whose paths are in *modified*."""
        def walk(item: QTreeWidgetItem) -> None:
            if tuple(self._item_key_path(item)) in modified:
                _apply_modified_highlight(item, colour)
            for i in range(item.childCount()):
                walk(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i))

    def _renumber_array_indices(self) -> None:
        """Keep array child indices consecutive after a structural change."""
        def walk(item: QTreeWidgetItem) -> None:
            if item.data(_COL_TYPE, _ROLE_TYPE) == "array":
                for i in range(item.childCount()):
                    item.child(i).setText(_COL_KEY, str(i))
            for i in range(item.childCount()):
                walk(item.child(i))
        walk(self._tree.invisibleRootItem())
