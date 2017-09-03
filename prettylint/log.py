'''
Logging formatter
'''

import logging
import os

import six

_log = logging.getLogger(__name__)

MAX_PRINTED_LEVEL_LEN = 3
MAX_LEFT_COLUMNS = 80

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
BOLD = 8

LEVEL_COLORS = {
    logging.DEBUG: WHITE,
    logging.INFO: WHITE + BOLD,
    logging.WARNING: YELLOW + BOLD,
    logging.ERROR: RED + BOLD,
    logging.CRITICAL: MAGENTA + BOLD,
}

HEAD_COLOR = WHITE

LINE_COLORS = LEVEL_COLORS

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[%d;%dm"


try:
    COLORIZED_BY_DEFAULT = bool(int(os.environ.get("COLORED_FORMATTER", "0")))
except ValueError:
    COLORIZED_BY_DEFAULT = True


levelNames = {}
try:
    from logging import _levelsNames
    for level in _levelsNames:
        if isinstance(level, int):
            levelNames[level] = logging.getLevelName(level)
except ImportError:
    for level in [logging.CRITICAL, logging.ERROR, logging.WARNING,
                  logging.INFO, logging.DEBUG, logging.NOTSET]:
        levelNames[level] = logging.getLevelName(level)

uncoloredLevelNames = {}
for level, name in six.iteritems(levelNames):
    uncoloredLevelNames[level] = name[:MAX_PRINTED_LEVEL_LEN].upper()

whiteLine = ""
for i in range(MAX_LEFT_COLUMNS):
    whiteLine += " "


def colorize(string, color):
    bold = color / BOLD
    color = color % BOLD
    if bold != 0:
        bold = 1
    beginTag = COLOR_SEQ % (bold, 30 + color)
    string = string.replace(RESET_SEQ, RESET_SEQ + beginTag)
    endTag = RESET_SEQ
    return beginTag + string + endTag


coloredLenDiff = {}
coloredLevelNames = {}
for level, name in six.iteritems(uncoloredLevelNames):
    coloredLevelName = colorize(name, LEVEL_COLORS.get(level, -1))
    coloredLevelNames[level] = coloredLevelName
    coloredLenDiff[level] = len(coloredLevelName) - len(name)


class ColoredFormatter(logging.Formatter):

    def __init__(self, fmt=None, datefmt=None, colored=COLORIZED_BY_DEFAULT):
        super(ColoredFormatter, self).__init__(fmt, datefmt)

        self.colored = colored

        if self.colored:
            self.colorize = lambda s, c: colorize(s, c)
        else:
            self.colorize = lambda s, c: s

        if colored:
            self.levelNames = coloredLevelNames
        else:
            self.levelNames = uncoloredLevelNames
        self.lastHead = ""

    def format(self, record):

        try:
            message = record.getMessage()
            if record.exc_info and record.exc_info[0] is not None:
                message += "\n" + self.formatException(record.exc_info)
            lines = message.split('\n')
            spaceLine = "\n"

            if len(lines) > 0:
                for firstLine, line in enumerate(lines):
                    if line and not line.isspace():
                        break
                if firstLine > 0:
                    lines = lines[firstLine:]

                for lastLine, line in enumerate(reversed(lines)):
                    if line and not line.isspace():
                        break
                if lastLine > 0:
                    lines = lines[:len(lines) - lastLine]

            if len(lines) == 0:
                return ""

            newRecordData = dict(record.__dict__)
            del newRecordData['exc_info']
            newRecordData['msg'] = ''
            newRecordData['args'] = []

            level = record.levelno
            newRecordData['levelname'] = self.levelNames.get(level,
                                                             record.levelname)

            newRecord = logging.makeLogRecord(newRecordData)
            head = super(ColoredFormatter, self).format(newRecord)
            headLen = len(head)
            if headLen > MAX_LEFT_COLUMNS:
                head = head[:MAX_LEFT_COLUMNS - 3] + "..."
                headLen = len(head)
            indentLen = headLen
            if self.colored:
                indentLen -= coloredLenDiff.get(level, 0)

            lastHead = self.lastHead
            self.lastHead = head

            if lines[0][:1] == ' ' or lines[0][:1] == '\t':
                spaceLine = ''
                if head == lastHead:
                    head = whiteLine[:indentLen]

            finalMessage = ('\n' + whiteLine[:indentLen]).join(lines)
            return (
                spaceLine + self.colorize(head, HEAD_COLOR) +
                self.colorize(finalMessage, LINE_COLORS.get(level, -1))
            )

        except Exception as exception:
            _log.error("Error formatting logging message:\n"
                       " source: %s(%s)\n"
                       " message: %s\n"
                       " args: %s\n"
                       " excepion: %s\n",
                       record.pathname, record.lineno, record.msg,
                       record.args, exception)
            return ""


def configure_logging(level=logging.INFO):
    logging.basicConfig(
        format='%(levelname)-7s %(name)-16s | %(message)s',
        level=logging.DEBUG
    )
