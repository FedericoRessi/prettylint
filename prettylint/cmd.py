#!/usr/bin/env python
'''Look for all *.py files for modules and pass them thought pylint

'''

# from python framework
import argparse
from collections import defaultdict, namedtuple
import glob
import logging
import os
import sys

# from pypa installed packages
import six
from pylint.lint import Run

# from prettylynt package
from prettylint.log import configure_logging


LOG = logging.getLogger(__name__)


def main():
    __doc__

    configure_logging()

    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        'files_or_dirs', metavar='files_or_dirs', type=str, nargs='+',
        help='Files or directories to be processed with pylint.')
    options = parser.parse_args()

    status = 0

    # Classify module names by its package root folder
    modules_in_folders = defaultdict(list)
    for item in options.files_or_dirs:
        LOG.debug("Looking at %r", item)
        for module_info in find_modules_from_string(item):
            modules_in_folders[module_info.root_dir].append(module_info)

        # take a copy of the original sys.path
        for folder, modules in six.iteritems(modules_in_folders):
            runner = PyLintRunner(folder)
            status = runner.run(modules) or status

    sys.exit(status)


def find_modules_from_string(item):
    for file_or_dir in glob.glob(item):
        if os.path.isdir(file_or_dir):
            LOG.debug('Looking at dir: %r', file_or_dir)
            for entry in find_modules_from_dir(file_or_dir):
                yield entry
        elif os.path.isfile(file_or_dir):
            LOG.debug('Looking at file: %r', file_or_dir)
            yield find_module_from_file(file_or_dir)
        else:
            raise FileNotFoundError(
                "No such file or folder: '{}'".format(file_or_dir))


def find_module_from_file(file_name):
    module_info = ModuleInfo.from_file(file_name)
    LOG.debug(
        "Found module: %r in dir %r",
        module_info.name, module_info.root_dir)
    return module_info


def find_modules_from_dir(dir_name):
    assert os.path.isdir(dir_name)
    if is_package_dir(dir_name):
        # this folder is a package
        LOG.debug("Looking at package dir: %r", dir_name)
        module_info = ModuleInfo.from_dir(dir_name)
        LOG.debug(
            "Found package: %r in dir %r",
            module_info.name, module_info.root_dir)
        yield module_info

    else:
        LOG.debug("Looking for python sources in dir: %r", dir_name)
        for entry in find_modules_from_string(os.path.join(dir_name, "*.py")):
            yield entry


class ModuleInfo(namedtuple('ModuleInfo', ['name', 'root_dir'])):
    '''Model for basic python module details
    '''

    @classmethod
    def from_dir(cls, dir_name):
        assert is_package_dir(dir_name)
        names = []
        root_dir = os.path.normcase(os.path.abspath(dir_name))
        LOG.debug("Getting package name from dir %r", root_dir)
        while is_package_dir(root_dir):
            root_dir, name = os.path.split(root_dir)
            assert '.' not in name
            LOG.debug("Getting package name from dir %r", root_dir)
            names.append(name)

        return cls(name='.'.join(reversed(names)), root_dir=root_dir)

    @classmethod
    def from_file(cls, file_name):
        assert os.path.isfile(file_name)
        LOG.debug("Getting module name from file %r", file_name)

        root_dir, base_name = os.path.split(file_name)
        name, suffix = os.path.splitext(base_name)
        assert '.' not in name
        if suffix:
            assert suffix == ".py"
        if is_package_dir(root_dir):
            package_info = cls.from_dir(root_dir)
            root_dir = package_info.root_dir
            name = package_info.name + '.' + name

        return cls(name=name, root_dir=root_dir)


def is_package_dir(dir_name):
    return os.path.isdir(dir_name) and os.path.isfile(
        os.path.join(dir_name, '__init__.py'))


class PyLintRunner(object):

    def __init__(self, root_dir):
        self._root_dir = root_dir
        self._stdout = PyLintStream(self, logging.INFO)
        self._stderr = PyLintStream(self, logging.ERROR)
        self._logger = logging.getLogger(
            'pylint.' + os.path.basename(root_dir))

    def parse(self, message, level):
        message = message.strip()
        # Ignore whitespaces
        if message:
            if message.startswith('E: '):
                level = logging.ERROR
            elif message.startswith('W: '):
                level = logging.WARN

            self._logger.log(level, '%s', message)

    def run(self, modules):
        # take a copy of the original sys.path, sys.stdout and sys.stderr
        original_path = list(sys.path)
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = self._stdout
        sys.stderr = self._stderr

        try:
            command_line = [module_info.name for module_info in modules]
            LOG.debug("Running pylint: %r", command_line)
            Run(command_line)

        except SystemExit as exit:
            return exit.code

        else:
            return 0

        finally:
            # restore original system path and stdout
            sys.path = original_path
            sys.stdout = original_stdout
            sys.stderr = original_stderr


class PyLintStream(object):

    def __init__(self, parser, level):
        self._parser = parser
        self._level = level

    def write(self, message):
        self._parser.parse(message, level=self._level)


if __name__ == '__main__':
    main()
