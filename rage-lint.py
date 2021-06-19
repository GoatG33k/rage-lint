import sys
from argparse import ArgumentParser
from glob import glob
from os import stat, unlink, getcwd
from os.path import abspath, realpath, dirname, exists
from time import time
from urllib import request

from colored import fg, attr
from lxml import etree
from packaging.version import parse as parse_version

__VERSION__ = '0.0.4'

argParser = ArgumentParser(description='A linter for RAGE metafiles')
argParser.add_argument('globs', metavar='glob', type=str, nargs='+', help="glob paths to lint")
argParser.add_argument('-u', '--update', action='store_true', help='forcibly update to the latest schema')
argParser.add_argument('-v', '--verbose', action='count', default=0)
args = argParser.parse_args()

copyright_str = '\n'.join((
    '===',
    '=== %srage-lint%s - RAGE Metafile linter%s' % (fg('red'), fg('yellow'), fg('cyan')),
    '===     %s[[ %sVersion %s%s%s ]]%s' % (
        fg('dark_gray'), fg('white'), fg('yellow'), __VERSION__, fg('dark_gray'), fg('cyan')),
    '===\n',
))
print(fg('cyan') + copyright_str + attr(0))

try:
    # TODO: update to master
    version_check_url = "https://raw.githubusercontent.com/GoatG33k/rage-lint/master/latest.txt?%d" % time()
    with request.urlopen(version_check_url) as response:
        version_str = response.read().decode('utf-8')
        if parse_version(__VERSION__) < parse_version(version_str):
            print("%s-------------------------------------%s" % (fg('yellow'), attr(0)))
            print("%sA new version %s%s%s is available!%s" % (
                fg('green'), fg('yellow'), version_str, fg('green'), attr(0)))
            print("https://github.com/GoatG33k/rage-lint/releases/")
            print("%s-------------------------------------%s\n" % (fg('yellow'), attr(0)))
except BaseException as e:
    print("%s%s%s" % (fg('red'), e, attr(0)))
    print("%sFailed to check for application update%s" % (fg('yellow'), attr(0)))

data_dir = dirname(realpath(__file__))
if getattr(sys, 'frozen', False):
    data_dir = sys._MEIPASS

xsd_schema = None
xsd_schema_path = abspath(data_dir + '/schema.xsd')
if exists(xsd_schema_path):
    schema_age = time() - (stat(xsd_schema_path)).st_mtime
    # remove cached after 1 week, or if update requested
    if schema_age > (3600 * 24 * 7) or args.update:
        print("%sRemoving old schema and re-fetching...%s" % (fg('yellow'), attr(0)))
        unlink(xsd_schema_path)

if not exists(xsd_schema_path):
    xsd_url = "https://raw.githubusercontent.com/GoatG33k/gta5-xsd/master/GTA5.xsd"
    print("%sDownloading schema...%s" % (fg('yellow'), attr(0)))
    with request.urlopen(xsd_url) as response, open(xsd_schema_path, 'w') as f:
        f.write(response.read().decode('utf-8'))
        f.close()

xsd_root = None
xsd_schema = None

try:
    print("%sReading schema...%s" % (fg('yellow'), attr(0)))
    xsd_root = etree.parse(xsd_schema_path)
    xsd_schema = etree.XMLSchema(xsd_root)
except etree.XMLSchemaParseError as e:
    print("%sFailed to parse GTA5.xsd, please report this issue to the GitHub repository%s:" % (fg('red'), attr(0)))
    print("\t%s%s%s" % (fg('yellow'), str(e), attr(0)))
    exit(1)

known_root_types = []
for el in xsd_root.iter():
    parent = el.getparent()
    if parent is not None and parent.tag == '{http://www.w3.org/2001/XMLSchema}schema':
        known_root_types.append(el.get('name'))

files = []
for _glob in args.globs:
    glob_files = glob(_glob, recursive=True)
    files.extend(glob_files)

total_file_count = len(files)
skipped_files = []
failed_files = []


def handle_pass():
    print("%s OK%s" % (fg('green'), attr(0)), file=sys.stderr)


def handle_fail(path, msg):
    failed_files.append((path, msg))
    print("%s FAIL%s" % (fg('red'), attr(0)), file=sys.stderr)
    print(("  - %s" + msg + "%s") % (fg('red'), attr(0)) + "\n", file=sys.stderr)


def handle_skip(path, msg):
    skipped_files.append((path, msg))
    print("%s WARN%s" % (fg('yellow'), attr(0)), file=sys.stderr)
    print(("  - %s" + msg + "%s") % (fg('yellow'), attr(0)) + "\n", file=sys.stderr)


print("%sFound %s%d%s file%s to lint...%s\n" % (fg('yellow'), fg('green'), len(files), fg('yellow'),
                                                's' if len(files) > 0 else '', attr(0)))
for file in files:
    relative_file_path = realpath(file).replace(getcwd(), '.')
    print(("Linting %s%s%s" % (fg('yellow'), relative_file_path, attr(0))).ljust(75), end="", file=sys.stderr)
    try:
        doc = etree.parse(file, parser=etree.XMLParser(remove_comments=True))
        # check that the root is recognized
        root_tag_name = doc.getroot().tag
        if root_tag_name not in known_root_types:
            handle_skip(file, "The root '%s' is not recognized" % root_tag_name)
            continue
        # we do a bit of magic to process R* ambiguous array types:
        # since <Item> can be anything, if a type is specified in the file,
        # rewrite the element to be a special element named '__Item__{type}'
        # which will be a determininstic type
        for el in doc.iter():
            if el.tag not in ['Item', 'item']:
                continue
            type_attr = el.attrib.get('type')
            if type_attr is not None and 'xs:' not in type_attr and type_attr != 'NULL' and type_attr in known_root_types:
                new_tag_name = "Item__" + type_attr
                el.tag = new_tag_name

        xsd_schema.assertValid(doc)
        handle_pass()
    except etree.XMLSyntaxError as e:
        handle_skip(file, str(e))
    except etree.DocumentInvalid as e:
        handle_fail(file, str(e))

total_failed = len(failed_files)
total_skipped = len(skipped_files)
_result_str = ("%sPASSED%s" % (fg('green'), attr(0)))
if len(failed_files) > 0:
    _result_str = ("%sFAIL%s" % (fg('red'), attr(0)))

total_passed_files = total_file_count - total_failed - total_skipped
code = 0

if total_file_count == 0:
    code = 1

if total_skipped > 0:
    code = 1
    print("\n\nSkipped files (%d):" % total_skipped)
    for warn_file in skipped_files:
        print("  - %s%s %s(%s)%s" % (fg('red'), warn_file[0], fg('yellow'), warn_file[1], attr(0)))

if total_failed > 0:
    code = 2
    print("\n\nFailed files (%d):" % total_failed)
    for failed_file in failed_files:
        print("  - %s%s %s(%s)%s" % (fg('red'), failed_file[0], fg('yellow'), failed_file[1], attr(0)))

# Calculate percentage total
total_percent = 1
if total_file_count > 0:
    total_percent = (total_passed_files / (total_file_count - total_skipped))
    total_percent = round(total_percent * 100, 2)

# Generate final output
if total_percent > 0.8:
    _total_percent_str = fg('green')
elif total_percent > 0.5:
    _total_percent_str = fg('yellow')
else:
    _total_percent_str = fg('red')
_result_color_str = _total_percent_str
_total_percent_str = "%s%s%s" % (_result_color_str, str(total_percent) + "%", attr(0))
_skipped_str = "%s%d%s skipped" % (fg('yellow') if total_skipped > 0 else fg('light_gray'), total_skipped, attr(0))
_failed_str = "%s%d%s failed" % (fg('red') if total_failed > 0 else fg('light_gray'), total_failed, attr(0))
_emoji = (fg('red') if total_failed > 0 else fg('green')) + ("✔" if total_failed == 0 else "✘" + attr(0))
print('\n  %s Total (%s): %s / %s in %d files' % (
    _emoji, _total_percent_str, _skipped_str, _failed_str, total_file_count), end='')
sys.exit(code)
