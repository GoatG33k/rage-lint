import argparse
import glob
import os.path
import sys
import time
from os.path import abspath, realpath, dirname, exists
from urllib import request

from colored import fg, attr
from lxml import etree

__VERSION__ = '0.0.2'


def silly_log(s):
    print(s) if args.verbose >= 2 else None


def debug(s):
    print(s) if args.verbose >= 1 else None


argParser = argparse.ArgumentParser(description='A linter for RAGE metafiles')
argParser.add_argument('globs', metavar='glob', type=str, nargs='+', help="glob paths to lint")
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

dataDir = dirname(realpath(__file__))
if getattr(sys, 'frozen', False):
    dataDir = sys._MEIPASS

xsdSchema = None
schemaPath = abspath(dataDir + '/schema.xsd')
if exists(schemaPath):
    schemaAge = time.time() - (os.stat(schemaPath)).st_mtime
    # remove cached after 1 week
    if schemaAge > (3600 * 24 * 7):
        print("%sRemoving old schema and re-fetching...%s" % (fg('light_gray'), attr(0)))
        os.unlink(schemaPath)

if not exists(schemaPath):
    xsdUrl = "https://raw.githubusercontent.com/GoatG33k/gta5-xsd/master/GTA5.xsd"
    print("%sDownloading schema...%s" % (fg('cyan'), attr(0)))
    with request.urlopen(xsdUrl) as response, open(schemaPath, 'w') as f:
        f.write(response.read().decode('utf-8'))
        f.close()

xsdRoot = None
xsdSchema = None

try:
    print("%sReading schema...%s" % (fg('yellow'), attr(0)))
    xsdRoot = etree.parse(schemaPath)
    xsdSchema = etree.XMLSchema(xsdRoot)
except etree.XMLSchemaParseError as e:
    print("%sFailed to parse GTA5.xsd, please report this issue to the GitHub repository%s:" % (fg('red'), attr(0)))
    print("\t%s%s%s" % (fg('yellow'), str(e), attr(0)))
    exit(1)

knownRootTypes = []
for el in xsdRoot.iter():
    parent = el.getparent()
    if parent is not None and parent.tag == '{http://www.w3.org/2001/XMLSchema}schema':
        knownRootTypes.append(el.get('name'))

files = []
for _glob in args.globs:
    globFiles = glob.glob(_glob, recursive=True)
    files.extend(globFiles)

totalFiles = len(files)
skippedFiles = []
failedFiles = []


def handle_pass():
    print("%s OK%s" % (fg('green'), attr(0)), file=sys.stderr)


def handle_fail(path, msg):
    failedFiles.append((path, msg))
    print("%s FAIL%s" % (fg('red'), attr(0)), file=sys.stderr)
    print(("  - %s" + msg + "%s") % (fg('red'), attr(0)) + "\n", file=sys.stderr)


def handle_skip(path, msg):
    skippedFiles.append((path, msg))
    print("%s WARN%s" % (fg('yellow'), attr(0)), file=sys.stderr)
    print(("  - %s" + msg + "%s") % (fg('yellow'), attr(0)) + "\n", file=sys.stderr)


print("%sFound %d file%s to lint...%s\n" % (fg('cyan'), len(files), 's' if len(files) > 0 else '', attr(0)))
for file in files:
    relative_file_path = realpath(file).replace(os.getcwd(), '.')
    print(("Linting %s%s%s" % (fg('yellow'), relative_file_path, attr(0))).ljust(75), end="", file=sys.stderr)
    try:
        doc = etree.parse(file, parser=etree.XMLParser(remove_comments=True))
        # check that the root is recognized
        rootTagName = doc.getroot().tag
        if rootTagName not in knownRootTypes:
            handle_skip(file, "The root '%s' is not recognized" % rootTagName)
            continue
        # we do a bit of magic to process R* ambiguous array types:
        # since <Item> can be anything, if a type is specified in the file,
        # rewrite the element to be a special element named '__Item__{type}'
        # which will be a determininstic type
        for el in doc.iter():
            if el.tag not in ['Item', 'item']:
                continue
            type_attr = el.attrib.get('type')
            if type_attr is not None and 'xs:' not in type_attr and type_attr != 'NULL' and type_attr in knownRootTypes:
                new_tag_name = "Item__" + type_attr
                el.tag = new_tag_name

        xsdSchema.assertValid(doc)
        handle_pass()
    except etree.XMLSyntaxError as e:
        handle_skip(file, str(e))
    except etree.DocumentInvalid as e:
        handle_fail(file, str(e))

totalFailedFiles = len(failedFiles)
totalSkippedFiles = len(skippedFiles)
resultStr = ("%sPASSED%s" % (fg('green'), attr(0)))
if len(failedFiles) > 0:
    resultStr = ("%sFAIL%s" % (fg('red'), attr(0)))

totalPassedFiles = totalFiles - totalFailedFiles - totalSkippedFiles
code = 0

if totalFiles == 0:
    code = 1

if totalSkippedFiles > 0:
    code = 1
    print("\n\nSkipped files (%d):" % totalSkippedFiles)
    for warnFile in skippedFiles:
        print("  - %s%s %s(%s)%s" % (fg('red'), warnFile[0], fg('yellow'), warnFile[1], attr(0)))

if totalFailedFiles > 0:
    code = 2
    print("\n\nFailed files (%d):" % totalFailedFiles)
    for failedFile in failedFiles:
        print("  - %s%s %s(%s)%s" % (fg('red'), failedFile[0], fg('yellow'), failedFile[1], attr(0)))

totalPercent = 1
if totalFiles > 0:
    totalPercent = (totalPassedFiles / (totalFiles - totalSkippedFiles))

if totalPercent > 0.8:
    totalPercentColorStr = fg('green')
elif totalPercent > 0.5:
    totalPercentColorStr = fg('yellow')
else:
    totalPercentColorStr = fg('red')

resultStr = '\n\t'.join((
    '\n Lint %s! (%s%s%s)' % (resultStr, totalPercentColorStr, str(round(totalPercent * 100, 2)) + "%", attr(0)),
    'Passed: %s%d%s' % (fg('green') if totalPassedFiles > 0 else fg('light_gray'), totalPassedFiles, attr(0)),
    'Failed: %s%d%s' % (fg('red') if totalFailedFiles > 0 else fg('light_gray'), totalFailedFiles, attr(0)),
    'Skipped: %s%d%s' % (fg('yellow') if totalSkippedFiles > 0 else fg('light_gray'), totalSkippedFiles, attr(0)),
))
print(resultStr, end='')

sys.exit(code)
