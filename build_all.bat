C:\Python27\python.exe setup.py bdist_egg upload --identity="Steven Rossiter" --sign --quiet
C:\Python34\python.exe setup.py bdist_egg upload --identity="Steven Rossiter" --sign --quiet
C:\Python27\python.exe setup.py bdist_wininst --target-version=2.7 register upload --identity="Steven Rossiter" --sign --quiet
C:\Python34\python.exe setup.py bdist_wininst --target-version=3.4 register upload --identity="Steven Rossiter" --sign --quiet
C:\Python34\python.exe setup.py sdist upload --identity="Steven Rossiter" --sign
C:\Python27\python.exe setup.py sdist upload --identity="Steven Rossiter" --sign
pause