"""Native Qt three-layer rendering cache (for integration into HUD painters).

No dependency on PySide6 until a Qt UI actually instantiates this class.
"""
class GraphicsCache:
    def __init__(self):
        self._chassis = {}
        self._instruments = {}
        self._generation = 0
    def chassis(self, key, renderer):
        if key not in self._chassis: self._chassis[key] = renderer()
        return self._chassis[key]
    def instruments(self, plugin, key, renderer):
        old = self._instruments.get(plugin)
        if old is None or old[0] != key:
            self._instruments[plugin] = (key, renderer())
        return self._instruments[plugin][1]
    def clear(self):
        self._chassis.clear(); self._instruments.clear(); self._generation += 1
    def stats(self):
        return {'chassis_entries': len(self._chassis),
                'instrument_entries': len(self._instruments),
                'generation': self._generation}
