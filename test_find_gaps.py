# these are actually offsets into the coordinate mappings.
Horizontal = 0
Vertical = 1

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

		left = min(pane.left for pane in panes)
		top = min(pane.top for pane in panes)
		right = max(pane.right for pane in panes)
		bottom = max(pane.bottom for pane in panes)

		super(DisplayGroup, self).__init__(layout, (left,top,right,bottom))

	def __repr__(self):
		return "%s: [%s]" % (super(DisplayGroup, self).__repr__(),
			", ".join(pane.__repr__() for pane in self.panes))

class Layout(object):
	def __init__(self, layout):
		self.cells = [DisplayPane(self, pane, idx) for idx, pane in enumerate(layout['cells'])]
		self.rows = layout['rows']
		self.cols = layout['cols']
		self.groups = self.extract_groups(self.cells)

	def __repr__(self):
		return "%s: %s" % (self.__class__.__name__, self.groups.__repr__())

	def make_sublime_layout(self):
		return {
			'cells': [[cell.left, cell.top, cell.right, cell.bottom] for cell in self.cells],
			'rows': self.rows,
			'cols': self.cols,
		}

	def search_groups(self, groups, search, remain):
		newremain = []
		group = [search]
		for cell in remain:
			# TODO: Error on flip. Shouldn't ever happen.
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
			return self.search_groups(groups, newremain[0], newremain[1:])
		else:
			return groups

	def extract_groups(self, cells):
		groups = cells
		while 1:
			newgroups = self.search_groups([], groups[0], groups[1:])
			if len(newgroups) == 1:
				return newgroups[0]
			elif len(newgroups) == len(groups):
				raise "Grouping stalled! At: %s" % (groups,)

			groups = newgroups


#layout = {'cells': [[3, 0, 5, 1], [3, 1, 4, 2], [4, 1, 5, 2], [3, 2, 5, 4], [0, 3, 2, 4], [1, 0, 3, 3]], 'cols': [0.0, 0.25, 0.37291831879460746, 0.5, 0.75, 1.0], 'rows': [0.0, 0.25, 0.5, 0.6875706214689266, 1.0]}
#layout = {'cells': [[0, 0, 2, 1], [0, 1, 1, 2], [1, 1, 2, 2]], 'cols': [0.0, 0.5, 1.0], 'rows': [0.0, 0.5, 1.0]}
layout = {
	'cells': [
		[0, 0, 2, 1],
		[2, 0, 4, 2],
		[0, 1, 2, 2],

		[0, 2, 1, 3],
		[1, 2, 3, 3],
		[3, 2, 4, 3],
	],
	'cols': [0.0, 0.35, 0.5, 0.8, 1.0],
	'rows': [0.0, 0.25, 0.5, 1.0],
}

layout = Layout(layout)
print layout
print layout.make_sublime_layout()
