@echo off
rem T-205: renders a bake package with Blender on this PC. Only calls render_package.py (same arguments);
rem changes no setting and runs no engine executable. Python: the py launcher, else Blender's bundled
rem python.exe, else python on PATH.
rem     tools\pc\render_package.cmd C:\Downloads\e912_paper_boat_s010_<commit>.bake.zip [--profile preview_eevee]
setlocal
set "SCRIPT=%~dp0render_package.py"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if defined PY goto run
for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender *") do (
  for /d %%V in ("%%~D\*") do (
    if exist "%%~V\python\bin\python.exe" set "PY="%%~V\python\bin\python.exe""
  )
)
if defined PY goto run
where python >nul 2>nul && set "PY=python"
if defined PY goto run
echo No Python found: install Python 3 or Blender, or run render_package.py with any python.exe.
exit /b 2
:run
%PY% "%SCRIPT%" %*
exit /b %ERRORLEVEL%
