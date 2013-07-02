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
		cur_pane = self.window.active_group()
		cur_view = self.window.active_view()
		if not cur_view: # only delete the pane if it's empty.
			# and only if there's actually more than one pane.
			if len(layout.cells) > 1:
				# move the views up a pane id after the deleted pane, otherwise
				# they'll all shuffle around all over the place.
				for pane_id in range(cur_pane+1, len(layout.cells)):
					views = self.window.views_in_group(cur_pane)
					while views:
						view = views.pop()
						self.window.set_view_index(view, pane_id - 1, 0)

			layout.delete_pane(cur_pane)
			self.window.set_layout(layout.make_sublime_layout())
		else: # otherwise close the file
			self.window.run_command("close")

	def switch(self, layout, direction, open='none', wrap=True):
		active = self.window.active_group()
		finder = getattr(layout, "find_" + direction)
		change = finder(active, wrap=wrap)

		cur_view = self.window.active_view()
		if cur_view:
			if open == 'move':
				self.window.set_view_index(cur_view, change, 0)
			elif open == 'copy':
				group, move_index = self.window.get_view_index(cur_view)
				self.window.run_command("clone_file")
				self.window.set_view_index(cur_view, group, move_index)
				cur_view = self.window.active_view()
				self.window.set_view_index(cur_view, change, 0)

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
