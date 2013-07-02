import sublime, sublime_plugin
from Submux import sublime_layout

class SubmuxCommand(sublime_plugin.WindowCommand):
	def _layout(self):
		return sublime_layout.Layout(self.window.get_layout())

	def split(self, layout, direction, open):
		direction = getattr(sublime_layout, direction)
		cur_pane = self.window.active_group()
		cur_view = self.window.active_view()
		new_pane = layout.split_pane(cur_pane, direction)

		# if we're going to copy it we need to create a duplicated
		# view of the currenly active file first.
		if cur_view and open == 'copy':
			group, move_index = self.window.get_view_index(cur_view)
			self.window.run_command("clone_file")
			cur_view = self.window.active_view()
			# move it to the left so focus falls back to the original
			# window (thanks Origami)
			self.window.set_view_index(cur_view, group, move_index)

		self.window.set_layout(layout.make_sublime_layout())
		self.window.focus_group(new_pane)
		if open == 'new':
			self.window.new_file()
		elif cur_view and (open == 'copy' or open == 'move'):
			self.window.set_view_index(cur_view, new_pane, 0)
		elif open == 'anything':
			self.window.run_command("show_overlay", {"overlay":"goto", "show_files": "true"})
		elif open == 'project_symbol':
			self.window.run_command("goto_symbol_in_project")

	def delete_current_pane(self, layout):
		layout.delete_pane(self.window.active_group())
		self.window.set_layout(layout.make_sublime_layout())

	def switch(self, layout, direction, wrap=True):
		active = self.window.active_group()
		finder = getattr(layout, "find_" + direction)
		change = finder(active, wrap=wrap)
		self.window.focus_group(change)

	def run(self, **kargs):
		cmd = kargs['do']
		del kargs['do']
		layout_orig = self._layout() # wasteful perhaps, but helpful.
		layout = self._layout()
		try:
			return getattr(self, cmd)(layout, **kargs)
		except:
			print("An error occurred while running this command.")
			print("State before: %s\nState after:  %s" % (layout_orig, layout))
			raise
