import unittest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from healthbar.holo import HoloLabel

class HoloContrastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_glyphs_have_opaque_dark_outline_and_light_interior_without_a_backplate(self):
        label=HoloLabel('24.5 ms')
        label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        label.setStyleSheet('color:#ffffff;background:transparent;font-size:20px;font-weight:700;')
        label.resize(160,40);label.show();self.app.processEvents()
        image=label.grab().toImage()
        pixels=[image.pixelColor(x,y) for x in range(image.width()) for y in range(image.height())]
        self.assertGreater(sum(c.alpha()==255 and c.lightness()<30 for c in pixels),50)
        self.assertGreater(sum(c.alpha()==255 and c.lightness()>220 for c in pixels),50)
        self.assertEqual(image.pixelColor(150,20).alpha(),0)
        label.close()

    def test_background_follows_every_theme_and_keeps_partial_opacity(self):
        from healthbar.ui_kit import set_theme, holo_background
        colors=[]
        for theme in ('blue-neon','green-matrix','red-blood'):
            set_theme(theme);color=holo_background()
            self.assertEqual(color.alpha(),217)
            self.assertLess(color.lightness(),32)
            colors.append(color.name())
        self.assertEqual(len(set(colors)),3)
        set_theme('blue-neon')

    def test_theme_does_not_turn_values_or_labels_green(self):
        from healthbar.ui_kit import set_theme, stylesheet
        style='QLabel {color:#F0F5FB;} QLabel#holoHeading {color:#AEBED0;} QPushButton {border-color:#00d9ff;}'
        for theme in ('green-matrix','red-blood'):
            set_theme(theme);rendered=stylesheet(style)
            self.assertIn('color:#F0F5FB',rendered)
            self.assertIn('color:#AEBED0',rendered)
            self.assertNotIn('border-color:#00d9ff',rendered)
        set_theme('blue-neon')
