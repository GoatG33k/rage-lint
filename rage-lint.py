import argparse
import glob
from os.path import relpath, realpath, dirname, exists
from urllib import request

from colored import fg, attr
from lxml import etree


def silly_log(s):
    print(s) if args.verbose >= 2 else None


def debug(s):
    print(s) if args.verbose >= 1 else None


argParser = argparse.ArgumentParser(description='A linter for RAGE metafiles')
argParser.add_argument('globs', metavar='glob', type=str, nargs='+', help="glob paths to lint")
argParser.add_argument('-v', '--verbose', action='count', default=0)
args = argParser.parse_args()

xsdSchema = None
schemaPath = relpath(dirname(realpath(__file__)) + '/schema.xsd')
if not exists(schemaPath):
    xsdUrl = "https://gitcdn.xyz/repo/GoatG33k/gta5-xsd/master/GTA5.xsd"
    with request.urlopen(xsdUrl) as response, open(schemaPath, 'w') as f:
        print("Reading XSD schema...")
        f.write(response.read().decode('utf-8'))
        f.close()

try:
    print("Parsing XSD schema...")
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

print("Searching for files to lint...")

files = []
for _glob in args.globs:
    globFiles = glob.glob(_glob, recursive=True)
    files.extend(globFiles)

totalFiles = len(files)
warnFiles = []
failedFiles = []


def handle_fail(path, msg):
    failedFiles.append((path, msg))
    print("%sFAIL%s" % (fg('red'), attr(0)))
    print(("  - %s" + msg + "%s") % (fg('red'), attr(0)) + "\n")


def handle_warn(path, msg):
    warnFiles.append((path, msg))
    print("%sWARN%s" % (fg('yellow'), attr(0)))
    print(("  - %s" + msg + "%s") % (fg('red'), attr(0)) + "\n")


print("Found " + str(len(files)) + " files to lint...")
for file in files:
    print(("Linting " + file).ljust(60), end="")
    try:
        doc = etree.parse(file, parser=etree.XMLParser(remove_comments=True))
        # check that the root is recognized
        rootTagName = doc.getroot().tag
        if rootTagName not in knownRootTypes:
            handle_warn(file, "The root '%s' is not recognized" % rootTagName)
            continue
        xsdSchema.assertValid(doc)
        print("%sOK%s" % (fg('green'), attr(0)))
    except etree.XMLSyntaxError as e:
        handle_fail(file, str(e))
    except etree.DocumentInvalid as e:
        handle_fail(file, str(e))

totalFailedFiles = len(failedFiles)
totalWarnFiles = len(warnFiles)
resultStr = ("%sPASSED%s" % (fg('green'), attr(0)))
if len(failedFiles) > 0:
    resultStr = ("%sFAIL%s" % (fg('red'), attr(0)))

print("\n  Lint %s!\n\tPassed: %d, Warnings: %d\n\tFailed: %d" %
      (resultStr, totalFiles - totalFailedFiles, totalWarnFiles, totalFailedFiles), end='')

if totalWarnFiles > 0:
    print("\n\nFiles with warnings:")
    for warnFile in warnFiles:
        print("  - %s%s %s(%s)%s" % (fg('red'), warnFile[0], fg('yellow'), warnFile[1], attr(0)))
       
if totalFailedFiles > 0:
    print("\n\nFailed files:")
    for failedFile in failedFiles:
        print("  - %s%s %s(%s)%s" % (fg('red'), failedFile[0], fg('yellow'), failedFile[1], attr(0)))
