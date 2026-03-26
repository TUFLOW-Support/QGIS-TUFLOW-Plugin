from .menu_button import MenuButton


class BranchSelectorMenu(MenuButton):

    def set_count(self, count: int):
        current_count = len(self.menu.actions())
        if current_count == count:
            return
        if count <= 1:  # no need to show the menu if only one or zero branches
            self.clear()
            return
        if current_count < count:
            for i in range(current_count, count):
                j = current_count + i
                action = self.menu.addAction(f'Branch {j + 1}')
                action.setCheckable(True)
                action.setChecked(j == 0)
            return
        if current_count > count:
            for i in range(current_count - 1, count - 1, -1):
                j = current_count - 1 - i
                action = self.menu.actions()[i]
                self.menu.removeAction(action)
            # ensure one action is checked
            if not any(x.isChecked() for x in self.menu.actions()) and self.menu.actions():
                self.menu.actions()[0].setChecked(True)

    def is_checked(self, index: int) -> bool:
        actions = self.menu.actions()
        if not actions and index == 0:
            return True
        if 0 <= index < len(actions):
            return actions[index].isChecked()
        return False

    def selected_branches(self) -> list[int]:
        return [i for i, x in enumerate(self.menu.actions()) if x.isChecked()]
