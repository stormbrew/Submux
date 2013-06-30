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
	def __init__(self, layout, coords, pane_id):
		super(DisplayPane, self).__init__(layout, coords)
		self.pane_id = pane_id

	def __repr__(self):
		return "%s%s" % (self.__class__.__name__,
			repr((((self.left, self.top, self.right, self.bottom)), self.pane_id))
			)

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
		self.cells = [DisplayPane(self, self._deref_splits(pane, layout['rows'], layout['cols']), idx) for idx, pane in enumerate(layout['cells'])]

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
