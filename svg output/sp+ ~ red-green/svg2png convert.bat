@echo off
for %%f in (*.svg) do (
    echo %%~f
    "C:\Program Files\Inkscape\inkscape.exe" ^
      -z ^
      --export-background-opacity=0 ^
      --export-png="%%~dpnf.png" ^
      --file="%%~f"

)