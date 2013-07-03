# these are actually offsets into the coordinate mappings.
Horizontal = 1
Vertical = 2

class LayoutError(Exception):
	pass

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
				raise LayoutError("Unmatched panes in the same group!")

			if last_orientation:
				if orientation != last_orientation:
					raise LayoutError("Unexpected flip in orientation!")
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
				raise LayoutError("Grouping stalled! At: %s" % (groups,))

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
				for child in self._depth_walk(next):
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

	def _split_pane_obj(self, pane, orientation):
		"""
		Splits a pane evenly in two by the orientation given.
		Returns the index of the newly created pane.
		"""
		group = pane.parent

		if not group:
			# if we're splitting the root pane when there's no
			# other panes, we just make a simple split structure.
			if orientation == Horizontal:
				first = DisplayPane(self, (0.0, 0.0, 0.5, 1.0))
				second = DisplayPane(self, (0.5, 0.0, 1.0, 1.0))
			else:
				first = DisplayPane(self, (0.0, 0.0, 1.0, 0.5))
				second = DisplayPane(self, (0.0, 0.5, 1.0, 1.0))
			split = DisplayGroup(self, [first, second])
			self.cells = [first, second]
			self.groups = split
			return 1

		pane_idx = group.panes.index(pane)
		if orientation == Horizontal:
			orig, pane.right = pane.right, pane.left + (pane.right - pane.left) / 2
			new_pane = DisplayPane(self, (pane.right, pane.top, orig, pane.bottom))
		else:
			orig, pane.bottom = pane.bottom, pane.top + (pane.bottom - pane.top) / 2
			new_pane = DisplayPane(self, (pane.left, pane.bottom, pane.right, orig))

		# always append to the end to avoid disrupting existing paneids
		self.cells.append(new_pane) 

		# Just insert it to the current group if orientations match,
		# otherwise make a new split group.
		if group.orientation == orientation:
			new_pane.parent = group
			group.panes[pane_idx+1:pane_idx+1] = [new_pane]
		else:
			split = DisplayGroup(self, [pane, new_pane])
			split.parent = group
			group.panes[pane_idx:pane_idx+1] = [split]

		return len(self.cells)-1

	def split_pane(self, number, orientation):
		return self._split_pane_obj(self.cells[number], orientation)

	def find_left(self, number, wrap=False):
		cell = self.cells[number]
		# Find a DisplayCell with its right edge set to this
		# cell's left edge and a vertical center between
		# this cell's top and bottom.
		bars = [cell.left]
		if wrap: bars.append(1.0)

		for bar in bars:
			for idx, other in enumerate(self.cells):
				mid = other.top + (other.bottom - other.top) / 2
				if other.right == bar and mid >= cell.top and mid <= cell.bottom:
					return idx

	def find_right(self, number, wrap=False):
		cell = self.cells[number]
		# Find a DisplayCell with its left edge set to this
		# cell's right edge and a vertical center between
		# this cell's top and bottom.
		bars = [cell.right]
		if wrap: bars.append(0.0)

		for bar in bars:
			for idx, other in enumerate(self.cells):
				mid = other.top + (other.bottom - other.top) / 2
				if other.left == bar and mid >= cell.top and mid <= cell.bottom:
					return idx

	def find_above(self, number, wrap=False):
		cell = self.cells[number]
		# Find a DisplayCell with its bottom edge set to this
		# cell's top edge and a horizontal center between
		# this cell's left and right.
		bars = [cell.top]
		if wrap: bars.append(1.0)

		for bar in bars:
			for idx, other in enumerate(self.cells):
				mid = other.left + (other.right - other.left) / 2
				if other.bottom == bar and mid >= cell.left and mid <= cell.right:
					return idx

	def find_below(self, number, wrap=False):
		cell = self.cells[number]
		# Find a DisplayCell with its bottom edge set to this
		# cell's top edge and a horizontal center between
		# this cell's left and right.
		bars = [cell.bottom]
		if wrap: bars.append(0.0)

		for bar in bars:
			for idx, other in enumerate(self.cells):
				mid = other.left + (other.right - other.left) / 2
				if other.top == bar and mid >= cell.left and mid <= cell.right:
					return idx

	def _move_horizontal_split(self, cell, by):
		if cell.parent and cell.parent.orientation == Horizontal:
			# since we're demanding a change to the size on
			# an edge perpendicular to this split, do it on the parent
			# instead.
			return self._move_horizontal_split(cell.parent, by)

		prev, next = self._get_adjacent(cell)
		if not next:
			# move up to the cell before it so we actually
			# have a bar to move.
			cell = prev
			prev, next = self._get_adjacent(cell)

		old_top = next.top
		new_top = next.top + by
		if (new_top > (cell.top + abs(by)) and 
		   new_top < (next.bottom - abs(by))):
			for sub in self._depth_walk(cell): 
				if sub.bottom == old_top: sub.bottom = new_top
			for sub in self._depth_walk(next):
				if sub.top == old_top: sub.top = new_top

	def move_horizontal_split(self, number, by):
		cell = self.cells[number]
		return self._move_horizontal_split(cell, by)

	def _move_vertical_split(self, cell, by):
		if cell.parent and cell.parent.orientation == Vertical:
			# since we're demanding a change to the size on
			# an edge perpendicular to this split, do it on the parent
			# instead.
			return self._move_vertical_split(cell.parent, by)

		prev, next = self._get_adjacent(cell)
		if not next:
			# move up to the cell before it so we actually
			# have a bar to move.
			cell = prev
			prev, next = self._get_adjacent(cell)

		old_left = next.left
		new_left = next.left + by
		if (new_left > (cell.left + abs(by)) and 
		   new_left < (next.right - abs(by))):
			for sub in self._depth_walk(cell): 
				if sub.right == old_left: sub.right = new_left
			for sub in self._depth_walk(next):
				if sub.left == old_left: sub.left = new_left

	def move_vertical_split(self, number, by):
		cell = self.cells[number]
		return self._move_vertical_split(cell, by)

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

if __name__ == '__main__':
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
	print(layout)
	print(layout.make_sublime_layout())
	print()

	layout.delete_pane(3)
	print(layout)
	print(layout.make_sublime_layout())
	print()

	layout.delete_pane(0)
	print(layout)
	print(layout.make_sublime_layout())
	print()
	layout2 = {'cells': [[0,0,1,1]], 'cols': [0.0,1.0], 'rows': [0.0,1.0]}

	layout2 = Layout(layout2)
	print(layout2)
	print(layout2.make_sublime_layout())
	print()

	layout2.split_pane(0, Vertical)
	print(layout2)
	print(layout2.make_sublime_layout())
	print()

	layout2.split_pane(1, Vertical)
	print(layout2)
	print(layout2.make_sublime_layout())
	print()

	layout2.split_pane(0, Horizontal)
	print(layout2)
	print(layout2.make_sublime_layout())
	print()
