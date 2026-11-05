"""Dependency-free structural checks (no Qt display needed)."""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
from tempfile import TemporaryDirectory
import ast
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TOP=ROOT/'App/Modules/Top/HUD_Plugins_ViewBar/NativeQt/n3xvs_top_native.py'
BOTTOM=ROOT/'App/Modules/Bottom/HUD_HomeNavBar/NativeQt/slim_style.py'
HELPER=ROOT/'Linux/n3xvs-hud-turbo'

def run():
    for p in (TOP,BOTTOM,HELPER): ast.parse(p.read_text())
    spec=spec_from_file_location('top_native',TOP)
    mod=module_from_spec(spec)
    spec.loader.exec_module(mod)
    with TemporaryDirectory() as tmp:
        settings=Path(tmp)/'prefs.json'
        values=mod._load_prefs(settings)
        assert values['bottom_enabled'] is True
        assert values['bottom_height']==62
        assert values['hide_delay_s']==2
        assert values['always_visible'] is False
        values.update(bottom_height=80,bottom_opacity=38,always_visible=True,
                      hidden_modules=['gpu','power'])
        mod._save_prefs(settings,values)
        loaded=mod._load_prefs(settings)
        assert loaded['bottom_height']==80 and loaded['bottom_opacity']==38
        assert loaded['hidden_modules']==['gpu','power']
        assert loaded['always_visible'] is True
    src=TOP.read_text()
    assert 'apply_skin()' in src
    assert 'bottom_dock_enabled=prefs' in src
    assert "bar.bottom_dock.settings_requested.connect(show_settings)" in src
    assert 'proc.setProgram(\'pkexec\')' in src
    assert '/usr/local/libexec/n3xvs-hud-turbo' in src
    # Geometry tests: screen 1280x800; TOP 100 / BOTTOM 70.
    bounds=mod._settings_workspace_bounds((0,0,1280,800),(0,0,1280,800),
                                           (0,0,1280,100),(0,730,1280,70))
    assert bounds==(0,100,1280,730), bounds
    x,y,w,h=mod._settings_window_rect(bounds)
    assert x>=0 and y>=100 and y+h<=718, (x,y,w,h)
    # Retracted TOP: the client regains its 100px; footer remains above dock.
    retracted=mod._settings_workspace_bounds((0,0,1280,800),(0,0,1280,730),
                                              None,(0,730,1280,70))
    assert retracted==(0,0,1280,730), retracted
    x,y,w,h=mod._settings_window_rect(retracted)
    assert y+h<=718
    # WM reservation can already include top and bottom, do not double subtract.
    assert mod._settings_workspace_bounds((0,0,1280,800),(0,100,1280,630),
            (0,0,1280,100),(0,730,1280,70))==(0,100,1280,730)
    assert 'app.exec()' in src
    assert 'QWebEngine' not in src
    assert '_settings_workspace_bounds(' in src
    assert 'timer.timeout.connect(fit_settings_window)' in src
    assert 'QScrollArea(dlg)' in src
    assert 'root.addWidget(scroll,1)' in src
    assert 'content_layout.addWidget(turbo_group)' in src
    assert "reserve_edge(bar,'top',0,False)" in src
    assert 'bar._reserve_workarea=n3xvs_reserve_top_workarea' in src
    for p in [ROOT/'install.sh',ROOT/'uninstall.sh',ROOT/'Linux/start.sh',ROOT/'update.sh']:
        subprocess.run(['bash','-n',str(p)],check=True)
    assert 'flock -n 9' in (ROOT/'Linux/start.sh').read_text()
    assert 'x11_window_pids' in (ROOT/'Linux/stop_legacy.py').read_text()
    print('OK — native Top+Bottom/Turbo/autostart/uninstall structural checks')

if __name__=='__main__':run()
