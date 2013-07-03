import sublime, sublime_plugin
from Submux import sublime_layout

class SubmuxCommand(sublime_plugin.WindowCommand):
	def _layout(self):
		return sublime_layout.Layout(self.window.get_layout())

	def _estimate_line_em_percents(self, layout):
		"""
		Calculates how tall a line is, and how wide a character
		is in terms of its percentage of the view's height using 
		viewport_extent and the line height of a view and the layout positions of the view.
		"""
		views = self.window.views()
		if views:
			view = views[0]
			line_height = view.line_height()
			em = view.em_width()
			extent = view.viewport_extent()
			group, index = self.window.get_view_index(view)
			group = layout.cells[group]

			cell_percent_width = group.right - group.left
			cell_percent_height = group.bottom - group.top

			em_percent_width = cell_percent_width * em / extent[0]
			line_percent_height = cell_percent_height * line_height / extent[1]

			return (em_percent_width, line_percent_height)
		else:
			# if there's no view we have to just guess somehow.
			# go with 5%.
			return (0.05, 0.05)

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

	def resize(self, layout, direction, count = 3):
		active = self.window.active_group()
		em_width, line_height = self._estimate_line_em_percents(layout)
		if len(layout.cells) == 1:
			return
		elif direction == 'left':
			layout.move_vertical_split(active, -count * em_width)
		elif direction == 'right':
			layout.move_vertical_split(active, count * em_width)
		elif direction == 'up':
			layout.move_horizontal_split(active, -count * line_height)
		elif direction == 'down':
			layout.move_horizontal_split(active, count * line_height)

		self.window.set_layout(layout.make_sublime_layout())

		cur_view = self.window.active_view()
		if cur_view:
			cur_view.settings().set("submux_moving", True)
			moving_count = cur_view.settings().get("submux_moving_counter") or 0
			cur_view.settings().set("submux_moving_counter", moving_count + 1)

			def refresh_moving_status(view):
				moving_count = view.settings().get("submux_moving_counter") or 0
				moving_count = max(0, moving_count - 1)
				view.settings().set("submux_moving_counter", moving_count)
				if moving_count < 1:
					view.settings().set("submux_moving", False)

			sublime.set_timeout(lambda: refresh_moving_status(cur_view), 500)


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
