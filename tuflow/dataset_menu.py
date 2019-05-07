from PyQt5.QtWidgets import *



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