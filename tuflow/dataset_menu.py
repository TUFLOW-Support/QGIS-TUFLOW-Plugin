from PyQt5.QtWidgets import *
from .spinbox_action import SingleSpinBoxAction



class DatasetMenu(QMenu):

	def __init__(self, title, parent=None):
		QMenu.__init__(self, title, parent)
		
	def mouseReleaseEvent(self, e):
		action = self.activeAction()
		if action is not None:
			if action.isEnabled():
				action.setEnabled(False)
				QMenu.mouseReleaseEvent(self, e)
				action.setEnabled(True)
				action.trigger()
			else:
				QMenu.mouseReleaseEvent(self, e)
		else:
			QMenu.mouseReleaseEvent(self, e)

	def checkedActions(self, *args, **kwargs):
		actions = []
		for action in self.actions():
			if action.isChecked():
				actions.append(action.text())
		return actions

	def setCheckedActions(self, items):
		for action in self.actions():
			if action.text() in items:
				action.setChecked(True)

class DatasetMenuDepAv(DatasetMenu):

	def __init__(self, title, parent=None):
		DatasetMenu.__init__(self, title, parent)
		self.defaultItem = None

	def addActionToSubMenus(self, action):
		for a in self.actions():
			if isinstance(a.parentWidget(), DatasetMenu):
				for a2 in a.parentWidget().actions():
					if isinstance(a2, SingleSpinBoxAction):
						a2.cboAddItem(action.iconText())

	def clearAllSubMenus(self):
		for a in self.actions():
			if isinstance(a.parentWidget(), DatasetMenu):
				for a2 in a.parentWidget().actions():
					if isinstance(a2, SingleSpinBoxAction):
						a2.cboClear()

	def updateDefaultItem(self, item):
		self.defaultItem = item
		for a in self.actions():
			if not a.isChecked():
				if isinstance(a.parentWidget(), DatasetMenu):
					for a2 in a.parentWidget().actions():
						if isinstance(a2, SingleSpinBoxAction):
							if a2.bCheckBox and a2.isChecked():
								pass
							else:
								a2.cboSetValue(item)

	def checkedActions(self, *args, **kwargs):
		allDetails = kwargs['all_details'] if 'all_details' in kwargs else False
		actions = []
		for a in self.actions():
			if a.isChecked():
				counter = 0
				if isinstance(a.parentWidget(), DatasetMenu):
					for a2 in a.parentWidget().actions():
						if isinstance(a2, SingleSpinBoxAction):
							if a2.isChecked():
								am = '{0}_{1}_'.format(a.text(), counter) if allDetails else ''
								counter += 1
								actions.append('{0}{1}'.format(am, a2.cboCurrentItem()))
		return actions

	def setCheckedActions(self, items):
		ams = [x.split("_")[0] for x in items]
		rts = [x.split("_")[2] for x in items]
		for a in self.actions():
			if a.text() in ams:
				for i in range(ams.count(a.text())):
					pass

	def checkedActionsParamsToText(self):
		actions = []
		for a in self.actions():
			if a.isChecked():
				if isinstance(a.parentWidget(), DatasetMenu):
					for a2 in a.parentWidget().actions():
						if isinstance(a2, SingleSpinBoxAction):
							if a2.isChecked():
								actions.append(a2.paramToText())
		return actions