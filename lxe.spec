# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('1C Ent_TRANS.xml', '.')]
binaries = [('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QAxContainer.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\Qsci.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtBluetooth.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtCore.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtDBus.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtDesigner.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtGui.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtHelp.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtMultimedia.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtMultimediaWidgets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtNetwork.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtNfc.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtOpenGL.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtOpenGLWidgets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtPdf.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtPdfWidgets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtPositioning.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtPrintSupport.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtQml.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtQuick.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtQuick3D.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtQuickWidgets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtRemoteObjects.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtSensors.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtSerialPort.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtSpatialAudio.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtSql.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtSvg.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtSvgWidgets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtTest.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtTextToSpeech.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtWebChannel.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtWebSockets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtWidgets.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\QtXml.pyd', 'PyQt6'), ('D:\\ptn313\\Lib\\site-packages\\PyQt6\\sip.cp313-win_amd64.pyd', 'PyQt6')]
hiddenimports = ['PyQt6.Qsci', 'lxml', 'chardet', 'pygments']
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=['D:\\ptn313\\Lib\\site-packages\\PyQt6'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='lxe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['blotus.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lxe',
)
