pip install pyinstaller[encryption] | Out-Null
[Console]::ResetColor()

$COMPILE_ICON_FILE = "icon.ico"
$COMPILE_VERSION_FILE = "rage-lint.version"
$COMPILE_KEY = "g0atg33k"

$COMPILE_ARGS = "--onefile --clean --log-level WARN"
$COMPILE_ARGS = "$COMPILE_ARGS --version-file=$COMPILE_VERSION_FILE"
$COMPILE_ARGS = "$COMPILE_ARGS --icon=$COMPILE_ICON_FILE"
$COMPILE_ARGS = "$COMPILE_ARGS --key=$COMPILE_KEY"

$TARGET_FILE = "../rage-lint.py"

echo "------------------------------------------------------------------------"
echo "|                      Compiling rage-lint.exe                         |"
echo "------------------------------------------------------------------------"
echo "|  :: COMPILE_ARGS = $COMPILE_ARGS"
echo "|  :: TARGET_FILE  = $TARGET_FILE"
echo "------------------------------------------------------------------------"

$CMD = "pyinstaller $COMPILE_ARGS $TARGET_FILE"
echo "# $CMD"

$ORIGINAL_DIR = $( Get-Location )
cd "$( Get-Location )\.build"
$CMD | Invoke-Expression
cd $ORIGINAL_DIR