import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage
from PySide6.QtCore import Qt
from healthbar.network_chart import NetworkChart, UP, DOWN, PING
from healthbar.ui_kit import set_theme

class NetworkChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_history_retains_one_ping_bar_per_probe_and_separate_scales(self):
        chart=NetworkChart()
        chart.record({'net_sample_at':1,'net_up_mbs':.1,'net_down_mbs':.2,'net_ping_ms':40,'net_ping_sample_at':1})
        chart.record({'net_sample_at':2,'net_up_mbs':None,'net_down_mbs':0,'net_ping_ms':40,'net_ping_sample_at':1})
        self.assertIsNone(chart.points[-1]['ping'])
        self.assertIsNone(chart.points[-1]['up'])
        self.assertAlmostEqual(chart.scales()[0],.23)
        self.assertAlmostEqual(chart.scales()[1],46)
        chart.record({'net_sample_at':2,'net_up_mbs':5})
        self.assertEqual(len(chart.points),2)
        chart.record({'net_sample_at':130,'net_up_mbs':.3})
        self.assertEqual(len(chart.points),1)
        chart.close()

    def test_chart_keeps_semantic_colors_in_every_theme_and_has_no_filled_backdrop(self):
        chart=NetworkChart();chart.resize(420,118)
        for theme in ('blue-neon','green-matrix','red-blood'):
            set_theme(theme)
            for i in range(60):
                chart.record({'net_sample_at':i*2+1,'net_up_mbs':.04+i*.001,'net_down_mbs':.2-i*.001,
                              'net_ping_ms':20 if i%5==0 else None,'net_ping_sample_at':i//5})
            image=QImage(chart.size(),QImage.Format.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent);chart.render(image)
            self.assertEqual(image.pixelColor(5,90).alpha(),0)
            colors={image.pixelColor(x,y).name() for x in range(image.width()) for y in range(32,98)}
            for color in (UP,DOWN,PING):self.assertIn(color,colors)
        set_theme('blue-neon');chart.close()
