import inspect


class BaseViewModel(object):
    def to_dict(self):
        return dict(inspect.getmembers(self))


class BaseListViewModel(object):
    def __init__(self):
        self.items = []

    def to_dict(self):
        return [item.to_dict() for item in self.items]
