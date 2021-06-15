import glob
import os.path
import subprocess
import sys

from colored import attr, fg

script_path = os.path.relpath(os.path.dirname(__file__) + "/../rage-lint.py")
search_glob = os.path.dirname(__file__).replace("\\", "/") + "/xml/**/*.xml"
print(search_glob)
files = glob.glob(search_glob)
failed = False
with open(os.devnull, 'wb') as null:
    for test_file in files:
        test_name = os.path.basename(test_file)
        with open(test_file, 'r') as f:
            expected_to_fail = ('ASSERT FAIL' in f.read())

        expected_state_str = '%sFAIL%s' % (fg('red'), attr(0)) if expected_to_fail else '%sPASS%s' % (
            fg('green'), attr(0))
        print("=> Running test '%s' (expected: %s)" % (test_name, expected_state_str))
        cmd_parts = (sys.executable, script_path, test_file)
        rc = 0
        try:
            rc = subprocess.check_call(cmd_parts, env=os.environ, stdout=null, stderr=null)
        except subprocess.CalledProcessError as e:
            rc = e.returncode

        # test return code
        if (not expected_to_fail and rc > 0) or (expected_to_fail and rc == 0):
            print("%sTest '%s' FAILED! Expected %s%s" % (fg('red'), test_name, expected_state_str, attr(0)))
            failed = True
        else:
            print("%sTest '%s' PASSED!%s" % (fg('green'), test_name, attr(0)))
