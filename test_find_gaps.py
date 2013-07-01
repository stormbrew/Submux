# these are actually offsets into the coordinate mappings.
Horizontal = 1
Vertical = 2

class DisplayCell(object):
	def __init__(self, layout, coords):
		self.layout = layout
		self.left, self.top, self.right, self.bottom = coords
		self.parent = None

	def set_parent(self, parent):
		self.parent = parent

	def by(self, orientation):
		if orientation == Horizontal:
			return (orientation, self.top, self.bottom)
		else:
			return (orientation, self.left, self.right)

	def __repr__(self):
		return "%s%s" % (self.__class__.__name__,
			repr((self.left, self.top, self.right, self.bottom))
			)

class DisplayPane(DisplayCell):
	pass

class DisplayGroup(DisplayCell):
	def __init__(self, layout, panes):
		self.panes = panes
		for pane in panes:
			pane.set_parent(self)

		self.orientation = self.find_orientation(self.panes)

		left = min(pane.left for pane in panes)
		top = min(pane.top for pane in panes)
		right = max(pane.right for pane in panes)
		bottom = max(pane.bottom for pane in panes)

		super(DisplayGroup, self).__init__(layout, (left,top,right,bottom))

	def __repr__(self):
		return "%s: %s[%s]" % (super(DisplayGroup, self).__repr__(),
			"Vertical" if self.orientation == Vertical else "Horizontal",
			", ".join(pane.__repr__() for pane in self.panes))

	@staticmethod
	def find_orientation(panes):
		last_orientation = None
		last = panes[0]
		for pane in panes[1:]:
			if pane.left == last.left and pane.right == last.right:
				orientation = Vertical
			elif pane.top == last.top and pane.bottom == last.bottom:
				orientation = Horizontal
			else:
				raise "Unmatched panes in the same group!"

			if last_orientation:
				if orientation != last_orientation:
					raise "Unexpected flip in orientation!"
			else:
				last_orientation = orientation

		return last_orientation


class Layout(object):
	def __init__(self, layout):
		self.cells = [DisplayPane(self, self._deref_splits(pane, layout['rows'], layout['cols'])) for pane in layout['cells']]

		self.groups = self._extract_groups(self.cells)

	def __repr__(self):
		return "%s: %s" % (self.__class__.__name__, self.groups.__repr__())

	@staticmethod
	def _deref_splits(raw_pane, rows, cols):
		return (
			cols[raw_pane[0]],
			rows[raw_pane[1]],
			cols[raw_pane[2]],
			rows[raw_pane[3]],
		)

	def _search_groups(self, groups, search, remain):
		newremain = []
		group = [search]
		for cell in remain:
			if search.by(Horizontal) == cell.by(Horizontal):
				group.append(cell)
			elif search.by(Vertical) == cell.by(Vertical):
				group.append(cell)
			else:
				newremain.append(cell)
		if len(group) > 1:
			groups.append(DisplayGroup(self, group))
		else:
			groups.append(search)

		if len(newremain) > 0:
			return self._search_groups(groups, newremain[0], newremain[1:])
		else:
			return groups

	def _extract_groups(self, cells):
		groups = cells
		while 1:
			newgroups = self._search_groups([], groups[0], groups[1:])
			if len(newgroups) == 1:
				return newgroups[0]
			elif len(newgroups) == len(groups):
				raise "Grouping stalled! At: %s" % (groups,)

			groups = newgroups

	@staticmethod
	def _make_splitid(cell, value, split_list):
		cur = cell
		while cur != None:
			group = cur.parent
			if (group, value) in split_list:
				return split_list.index((group, value))
			cur = group

		split_list.append((cell.parent, value))
		return len(split_list) - 1

	@staticmethod
	def _depth_walk(cell):
		nodes = [cell]
		while nodes:
			cell = nodes.pop()
			yield cell
			if isinstance(cell, DisplayGroup):
				nodes = cell.panes + nodes

	def _get_adjacent(self, pane):
		"""
		Returns a tuple of the two cells around
		the pane passed in. The one before, and the one after, 
		in whatever orientation the parent group is. If there isn't one
		before, the first will be None. If there isn't one
		after, the last will be None. If it's the only pane
		in the layout (or its group), both will be None.
		"""
		group = pane.parent

		if not group:
			return (None, None)

		panes = sorted(group.panes, key=lambda pane: (pane.left, pane.top))

		prev, cur = None, None
		for opane in panes:
			if cur:
				return (prev, opane)
			elif opane == pane:
				cur = opane
			else:
				prev = opane

		# if we're here there's nothing after.
		return (prev, None)

	def _delete_pane_obj(self, pane):
		group = pane.parent
		if not group: # don't delete if there are no more.
			return

		prev, next = self._get_adjacent(pane)
		if not prev and not next:
			self._delete_pane_obj(group) # delete this one instead
		elif prev:
			if group.orientation == Horizontal:
				for child in self._depth_walk(prev):
					if child.right == pane.left:
						child.right = pane.right
			else:
				for child in self._depth_walk(prev):
					if child.bottom == pane.top:
						child.bottom = pane.bottom
		else:
			if group.orientation == Horizontal:
				for child in self._depth_walk(next):
					if child.left == pane.right:
						child.left = pane.left
			else:
				for child in self._depth_walk(prev):
					if child.top == pane.bottom:
						child.top = pane.top

		group_idx = group.panes.index(pane)
		group.panes[group_idx:group_idx+1] = []

		# don't forget to normalize it if we've left
		# a group of one behind.
		while group and len(group.panes) == 1:
			npane = group.panes[0]
			if group.parent:
				group_idx = group.parent.panes.index(group)
				group.parent.panes[group_idx] = npane
			else:
				# if we're here we've deleted everything to the
				# root, just make this pane the root.
				self.groups = npane
			npane.parent = group.parent
			group = group.parent

		if pane in self.cells:
			cell_idx = self.cells.index(pane)
			self.cells[cell_idx:cell_idx+1] = []

	def delete_pane(self, number):
		return self._delete_pane_obj(self.cells[number])

	def make_sublime_layout(self):
		if len(self.cells) == 1:
			return {'cells': [[0,0,1,1]], 'rows': [0.0,1.0], 'cols': [0.0,1.0]}

		output_cells = []
		output_rows = []
		output_cols = []

		# Generate output_rows and output_cols first,
		# then sort them, then point the cells at them.
		# This is so the split bars come out in a sane
		# order that won't blow up sublime

		# We do a depth-first scan on the first pass because
		# we want panes to share edges with other
		# objects in their parent group(s).
		#import pdb; pdb.set_trace()
		for cell in self._depth_walk(self.groups):
			self._make_splitid(cell, cell.left, output_cols)
			self._make_splitid(cell, cell.top, output_rows)
			self._make_splitid(cell, cell.right, output_cols)
			self._make_splitid(cell, cell.bottom, output_rows)

		# put them in order
		output_cols[:] = sorted(output_cols, key=lambda split: split[1])
		output_rows[:] = sorted(output_rows, key=lambda split: split[1])

		# now build the cells list in the original cell order, which
		# has to be maintained.
		for cell in self.cells:
			output_cells.append([
				self._make_splitid(cell, cell.left, output_cols),
				self._make_splitid(cell, cell.top, output_rows),
				self._make_splitid(cell, cell.right, output_cols),
				self._make_splitid(cell, cell.bottom, output_rows),
			])

		return {
			'cells': output_cells,
			'rows': [row[1] for row in output_rows],
			'cols': [col[1] for col in output_cols],
		}


#layout = {'cells': [[3, 0, 5, 1], [3, 1, 4, 2], [4, 1, 5, 2], [3, 2, 5, 4], [0, 3, 2, 4], [1, 0, 3, 3]], 'cols': [0.0, 0.25, 0.37291831879460746, 0.5, 0.75, 1.0], 'rows': [0.0, 0.25, 0.5, 0.6875706214689266, 1.0]}
#layout = {'cells': [[0, 0, 2, 1], [0, 1, 1, 2], [1, 1, 2, 2]], 'cols': [0.0, 0.5, 1.0], 'rows': [0.0, 0.5, 1.0]}
layout = {
	'cells': [
		[0, 0, 2, 1],
		[2, 0, 4, 2],
		[4, 0, 5, 2],
		[0, 1, 2, 2],

		[0, 2, 1, 3],
		[1, 2, 3, 3],
		[3, 2, 5, 3],
	],
	'cols': [0.0, 0.35, 0.5, 0.8, 0.8, 1.0],
	'rows': [0.0, 0.25, 0.5, 1.0],
}

layout = Layout(layout)
print layout
print layout.make_sublime_layout()
print

layout.delete_pane(3)
print layout
print layout.make_sublime_layout()
print

layout.delete_pane(0)
print layout
print layout.make_sublime_layout()
print