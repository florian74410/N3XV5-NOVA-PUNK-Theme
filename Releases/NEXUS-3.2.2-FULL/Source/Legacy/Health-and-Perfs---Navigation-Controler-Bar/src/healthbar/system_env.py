"""Native desktop commands must not load the frozen application's Qt/GLib libraries."""
import os


def native_env():
    env = os.environ.copy()
    for key in ('LD_LIBRARY_PATH', 'DYLD_LIBRARY_PATH'):
        if key+'_ORIG' in env:
            original=env[key+'_ORIG']
            # Older updaters could pass their own embedded libraries to the new runtime.
            env[key] = os.pathsep.join(p for p in original.split(os.pathsep)
                                      if not p.rstrip('/').endswith('/HealthPerfsBar/_internal'))
        else:
            env.pop(key, None)
    # Restore host GIO plugins for Thunar, XFCE and other child processes.
    original_gio = env.pop('NOVABAR_ORIG_GIO_MODULE_DIR', None)
    if original_gio is not None:
        env['GIO_MODULE_DIR'] = original_gio
    else:
        env.pop('GIO_MODULE_DIR', None)
    original_extra=env.pop('NOVABAR_ORIG_GIO_EXTRA_MODULES',None)
    if original_extra is not None:
        env['GIO_EXTRA_MODULES']=original_extra
    else:
        env.pop('GIO_EXTRA_MODULES',None)
    for key in ('QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH', 'PYTHONHOME'):
        env.pop(key, None)
    return env
