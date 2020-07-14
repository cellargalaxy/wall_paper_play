rd /s /q __pycache__
rd /s /q build
rd /s /q dist
del wall_paper_play.spec

pyinstaller -F wall_paper_play.py