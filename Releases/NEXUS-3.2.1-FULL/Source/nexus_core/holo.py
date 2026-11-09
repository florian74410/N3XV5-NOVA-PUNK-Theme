"""Holo lifecycle: demand-only view computation, one active at a time."""
class HoloController:
    def __init__(self): self.active = None; self._views = {}
    def register(self, plugin, factory): self._views[plugin] = factory
    def open(self, plugin, raw_snapshot):
        if plugin not in self._views: raise KeyError(plugin)
        if self.active and self.active[0] == plugin: self.close(); return None
        self.close()
        view = self._views[plugin](raw_snapshot)
        self.active = (plugin, view)
        return view
    def close(self):
        if self.active:
            view = self.active[1]
            if hasattr(view, 'close'): view.close()
            self.active = None
