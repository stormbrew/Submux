import sublime, sublime_plugin
from Submux import sublime_layout

class SubmuxCommand(sublime_plugin.WindowCommand):
	def _layout(self):
		return sublime_layout.Layout(self.window.get_layout())

	def split_vertical(self):
		layout = self._layout()
		layout.split_pane(self.window.active_group(), sublime_layout.Vertical)
		return layout

	def split_horizontal(self):
		layout = self._layout()
		layout.split_pane(self.window.active_group(), sublime_layout.Horizontal)
		return layout

	def delete_current_pane(self):
		layout = self._layout()
		layout.delete_pane(self.window.active_group())
		return layout

class SplitVerticalCommand(SubmuxCommand):
	def run(self):
		self.window.set_layout(self.split_vertical().make_sublime_layout())

class SplitHorizontalCommand(SubmuxCommand):
	def run(self):
		self.window.set_layout(self.split_horizontal().make_sublime_layout())

class DeleteCurrentPaneCommand(SubmuxCommand):
	def run(self):
		self.window.set_layout(self.delete_current_pane().make_sublime_layout())
