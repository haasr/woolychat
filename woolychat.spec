# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Add the current directory to the path
current_dir = os.path.dirname(os.path.abspath('woolychat_launcher.py'))

# Collect all Flask and SQLAlchemy submodules
flask_imports = collect_submodules('flask')
sqlalchemy_imports = collect_submodules('sqlalchemy')
flask_sqlalchemy_imports = collect_submodules('flask_sqlalchemy')

# Get all standard library modules
try:
    import stdlib_list
    stdlib_modules = list(stdlib_list.stdlib_list())
    print(f"📦 Including {len(stdlib_modules)} standard library modules")
except ImportError:
    print("⚠️ stdlib_list not found, install with: pip install stdlib_list")
    stdlib_modules = [
        'calendar', 'datetime', 'json', 'os', 'sys', 'time', 'threading',
        'subprocess', 'webbrowser', 're', 'socket', 'pathlib', 'math',
        'collections', 'functools', 'itertools', 'locale', 'platform',
        'tempfile', 'shutil', 'glob', 'mimetypes', 'uuid', 'base64',
        'logging', 'warnings', 'weakref', 'copy', 'pickle', 'types',
        'inspect', 'traceback', 'io', 'contextlib', 'codecs', 'encodings',
        'urllib', 'http', 'ssl', 'email', 'xml', 'zipfile', 'gzip'
    ]

a = Analysis(
    ['woolychat_launcher.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        # Include all templates
        ('templates', 'templates'),
        # Include all static files
        ('static', 'static'),
        # Include any other necessary files
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        # Explicitly include the core packages we need
        'flask',
        'flask_sqlalchemy', 
        'sqlalchemy',
        'werkzeug',
        'jinja2',
        'requests',
        'PyPDF2',
        'docx',
        
        # Include their submodules
        *flask_imports,
        *sqlalchemy_imports, 
        *flask_sqlalchemy_imports,
        
        # Key standard library modules (only the ones we know we need)
        'calendar', 'datetime', 'json', 'os', 'sys', 'time', 'threading',
        'subprocess', 'webbrowser', 're', 'socket', 'pathlib', 'math',
        'collections', 'functools', 'itertools', 'mimetypes', 'uuid', 'base64',
        'logging', 'urllib', 'http', 'ssl', 'email', 'xml', 'io', 'tempfile',
        'shutil', 'glob', 'hashlib', 'hmac', 'secrets', 'random', 'string',
        'contextlib', 'warnings', 'weakref', 'copy', 'pickle', 'types',
        'inspect', 'traceback', 'codecs', 'encodings', 'binascii', 'struct',
        'platform', 'locale', 'difflib',
        
        # Tkinter for GUI
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        
        # Additional third-party modules that collect_submodules might miss
        'requests.adapters',
        'requests.auth',
        'requests.packages.urllib3',
        'urllib3.util.retry',
        'PyPDF2.pdf',
        'docx.document',
        'docx.shared',
        'docx.oxml',
        'werkzeug.security',
        'werkzeug.serving',
        'werkzeug.routing',
        'werkzeug.exceptions',
        'jinja2.loaders',
        'jinja2.runtime',
        'jinja2.environment',
        'sqlalchemy.dialects.sqlite.pysqlite',
        'sqlalchemy.engine.default',
        'sqlalchemy.sql.schema',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Large packages we definitely don't need
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'PIL',
        'Pillow',
        
        # Testing and development tools
        'pytest',
        'unittest',
        'test',
        'tests',
        'tkinter.test',
        'pydoc',
        'doctest',
        
        # Debugging and profiling tools  
        'pdb',
        'profile',
        'pstats',
        'cProfile',
        'trace',
        'timeit',
        
        # Build and packaging tools
        'distutils',
        'setuptools',
        'pip',
        'wheel',
        'pkg_resources',
        'jaraco',
        'importlib_metadata',
        'zipp',
        'more_itertools',
        
        # Other large/unnecessary modules
        'babel',
        'pytz',
        'dateutil',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# For macOS, we create an app bundle
if sys.platform == 'darwin':  # macOS
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='WoolyChat_v0.4',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='WoolyChat_v0.4'
    )
    
    app = BUNDLE(
        coll,
        name='WoolyChat_v0.4.app',
        icon='static/img/woolychat.icns' if os.path.exists('static/img/woolychat.icns') else None,
        bundle_identifier='com.woolychat.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleDocumentTypes': [
                {
                    'CFBundleTypeName': 'WoolyChat Document',
                    'CFBundleTypeIconFile': 'woolychat.icns',
                    'LSItemContentTypes': ['com.woolychat.document'],
                    'LSHandlerRank': 'Owner'
                }
            ]
        },
    )

else:  # Windows/Linux
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='WoolyChat_v0.4',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window
        disable_windowed_traceback=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='static/img/woolychat.ico' if os.path.exists('static/img/woolychat.ico') else None,
    )