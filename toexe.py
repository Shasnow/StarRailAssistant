"""
崩坏：星穹铁道助手
beta v0.6
作者：雪影
打包
"""

import os

os.system(
    'pyinstaller -F --version-file res/info.txt -i="res/SRAicon.ico" --window -F SRAbeta_v_0_6.py --hidden-import plyer.platforms.win.notification'
)
