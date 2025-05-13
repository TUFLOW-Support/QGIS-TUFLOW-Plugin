from qgis.PyQt.QtWidgets import *
from .spinbox_action import SingleSpinBoxAction

from .compatibility_routines import is_qt6



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
			else:
				action.setChecked(False)


class DepthAveragedItem():

	def __init__(self, method, params, resultType, action):
		self.method = method
		if type(params) is list:
			self.params = params
		else:
			self.params = [params]
		self.resultType = resultType
		self.action = action


class DatasetMenuDepAv(DatasetMenu):

	def __init__(self, title, parent=None):
		DatasetMenu.__init__(self, title, parent)
		self.defaultItem = None

	def addActionToSubMenus(self, action):
		for a in self.actions():
			if is_qt6:
				p = a.parent()
			else:
				p = a.parentWidget()
			if isinstance(p, DatasetMenu):
				for a2 in p.actions():
					if isinstance(a2, SingleSpinBoxAction):
						a2.cboAddItem(action.iconText())

	def clearAllSubMenus(self):
		for a in self.actions():
			if is_qt6:
				p = a.parent()
			else:
				p = a.parentWidget()
			if isinstance(p, DatasetMenu):
				for a2 in p.actions():
					if isinstance(a2, SingleSpinBoxAction):
						a2.cboClear()

	def updateDefaultItem(self, item):
		self.defaultItem = item
		for a in self.actions():
			if not a.isChecked():
				if is_qt6:
					p = a.parent()
				else:
					p = a.parentWidget()
				if isinstance(p, DatasetMenu):
					for a2 in p.actions():
						if isinstance(a2, SingleSpinBoxAction):
							if a2.bCheckBox and a2.isChecked():
								pass
							else:
								a2.cboSetValue(item)

	def clearCheckedActions(self):
		for a in self.actions():
			a.setChecked(False)
			if is_qt6:
				p = a.parent()
			else:
				p = a.parentWidget()
			if isinstance(p, DatasetMenu):
				i = 0
				for a2 in p.actions():
					if isinstance(a2, SingleSpinBoxAction):
						a2.setChecked(False)
						if i > 0:
							self.removeAction(a2)
						else:
							i += 1

	def checkedActions(self, *args, **kwargs):
		allDetails = kwargs['all_details'] if 'all_details' in kwargs else False
		actions = []
		for a in self.actions():
			if a.isChecked():
				counter = 0
				if is_qt6:
					p = a.parent()
				else:
					p = a.parentWidget()
				if isinstance(p, DatasetMenu):
					for a2 in p.actions():
						if isinstance(a2, SingleSpinBoxAction):
							if a2.isChecked():
								am = '{0}_{1}_'.format(a.text(), counter) if allDetails else ''
								counter += 1
								actions.append('{0}{1}'.format(am, a2.cboCurrentItem()))
		return actions

	def setCheckedActions(self, items):
		ams = [x.method for x in items]  # depth average methods
		pms = [x.params for x in items]  # depth average parameters
		rts = [x.resultType for x in items]  # depth average result types
		act = [x.action for x in items]
		self.clearCheckedActions()
		for a in self.actions():
			if a.text() in ams:
				a.setChecked(True)
				if is_qt6:
					p = a.parent()
				else:
					p = a.parentWidget()
				if isinstance(p, DatasetMenu):
					counter = 0
					for i, am in enumerate(ams):
						if am == a.text():
							if counter == 0 or not p.actions():
								if isinstance(p.actions()[0], SingleSpinBoxAction):
									a2 = p.actions()[0]
								else:
									a2 = act[i]
									lastAction = p.actions()[-2]  # insert before separator
									p.insertAction(lastAction, a2)
							else:
								a2 = act[i]
								lastAction = p.actions()[-2]  # insert before separator
								p.insertAction(lastAction, a2)
							a2.setChecked(True)
							a2.setValues(pms[i])
							a2.cboSetValue(rts[i])
							counter += 1

	def checkedActionsParamsToText(self):
		actions = []
		for a in self.actions():
			if a.isChecked():
				if is_qt6:
					p = a.parent()
				else:
					p = a.parentWidget()
				if isinstance(p, DatasetMenu):
					for a2 in p.actions():
						if isinstance(a2, SingleSpinBoxAction):
							if a2.isChecked():
								actions.append(a2.paramToText())
		return actions

	def resultTypes(self):
		resultTypes = []
		for a in self.actions():
			if is_qt6:
				p = a.parent()
			else:
				p = a.parentWidget()
			if isinstance(p, DatasetMenu):
				for a2 in p.actions():
					if isinstance(a2, SingleSpinBoxAction):
						for i in range(a2.cbo.count()):
							itemText = a2.cbo.itemText(i)
							if itemText not in resultTypes:
								resultTypes.append(itemText)

		return resultTypes