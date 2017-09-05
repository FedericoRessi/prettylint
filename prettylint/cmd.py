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
from pylint.lint import Run

# from prettylynt package
from prettylint.log import configure_logging

LOG = logging.getLogger(__name__)


def main():
    '''Main pylint wrapper entry point

    :return: the number of files with errors found
    '''

    configure_logging()

    parser = argparse.ArgumentParser(
        description=__doc__
    )
    parser.add_argument(
        'files_or_dirs', metavar='files_or_dirs', type=str, nargs='+',
        help='Files or directories to be processed with pylint.')
    options = parser.parse_args()

    # Classify module names by its package root folder
    modules = list()
    for item in options.files_or_dirs:
        LOG.debug("Looking at %r", item)
        for module_info in find_modules_from_string(item):
            modules.append(module_info)

    runner = PyLintRunner()
    errors = PylintErrors()
    runner.run(modules, errors)

    if errors:
        errors.pretty_print()
        sys.exit(1)

    else:
        sys.exit(0)


def find_modules_from_string(item):
    '''Looks for modules in matching files or folder
    '''
    for file_or_dir in glob.glob(item):
        if os.path.isdir(file_or_dir):
            LOG.debug('Looking at dir: %r', file_or_dir)
            for entry in find_modules_from_dir(file_or_dir):
                yield entry
        elif os.path.isfile(file_or_dir):
            LOG.debug('Looking at file: %r', file_or_dir)
            for module_info in find_module_from_file(file_or_dir):
                yield module_info
        else:
            raise FileNotFoundError(
                "No such file or folder: '{}'".format(file_or_dir))


def find_module_from_file(file_name):
    '''If given file is a python file this yields a ModuleInfo for it

    :param file_name: the path of the file
    :return: a generator that eventually yields a ModuleInfo
    '''

    if file_name.endswith('.py'):
        module_info = ModuleInfo.from_file(file_name)
        LOG.debug(
            "Found module: %r in dir %r",
            module_info.name, module_info.root_dir)
        yield module_info


def find_modules_from_dir(dir_name):
    '''Yields ModuleInfo instances for packages or files found in given dir

    :param dir_name: the path of the directory
    :return: a generator that eventually yields a ModuleInfos
    '''

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
        for item in os.listdir(dir_name):
            for module_info in find_modules_from_string(
                    os.path.join(dir_name, item)):
                yield module_info


class ModuleInfo(
        namedtuple('ModuleInfo', ['name', 'path', 'root_dir'])):
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

        return cls(
            name='.'.join(reversed(names)),
            path=os.path.relpath(dir_name),
            root_dir=root_dir
        )

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

        return cls(
            name=name,
            path=os.path.relpath(file_name),
            root_dir=root_dir
        )


def is_package_dir(dir_name):
    return os.path.isdir(dir_name) and os.path.isfile(
        os.path.join(dir_name, '__init__.py'))


class PyLintRunner(object):
    _logger = logging.getLogger('pylint')
    _module = None
    _file = None
    _root_dir = None
    _errors = None

    def __init__(self):
        self._stdout = PyLintStream(self, logging.DEBUG)
        self._stderr = PyLintStream(self, logging.ERROR)

    def run(self, modules, errors):
        '''Run pylint on given modules filling out errors list

        :param modules: a sequence of ModuleInfo instance
        :param errors: an instance of PyLintErrors
        :return: None
        '''

        # Get a list of root dirs that are already on the PYTHONPATH
        existing_root_dirs = set(
            os.path.normcase(os.path.abspath(path))
            for path in sys.path
            if os.path.exists(path)
        )

        # Get a list of root dirs that has to be added to the PYTHONPATH
        # before running pylint
        new_root_dirs = []
        for module_info in modules:
            if module_info.root_dir not in existing_root_dirs:
                new_root_dirs.append(module_info.root_dir)
                existing_root_dirs.add(module_info.root_dir)

        self._errors = errors

        # add missing modules root dirs to the path
        original_path = list(sys.path)
        sys.path = new_root_dirs + original_path

        # redirect stderr and stdout to self.parse method
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = self._stdout
        sys.stderr = self._stderr

        try:
            command_line = ['-f', 'parseable'] + [m.name for m in modules]
            LOG.debug("Running pylint: %r", command_line)
            Run(command_line)

        except SystemExit as exit:
            pass

        finally:
            # restore original system path and stdout
            sys.path = original_path
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def parse(self, message, level):
        message = message.strip()
        LOG.log(level, "%s", message.strip())

        # Ignore whitespaces
        if message:
            if message.startswith('************* Module '):
                _, _, name = split(message, maxsplit=2)
                self.enter_module(name)
            else:
                fields = split(message, ':', 2)
                self._logger.debug("%r", fields)
                if len(fields) == 3:
                    file_name, line, rest = fields
                    if os.path.isfile(file_name):
                        _, rest = split(rest, '[', 1)
                        rest, message = split(rest, ']', 1)
                        tag, _ = split(rest, ',', 1)
                        # assert module_name == self._module
                        self._errors.add(
                            file_name=file_name,
                            line=line,
                            module_name=self._module,
                            tag=tag,
                            message=message
                        )

    def enter_module(self, name):
        pass
        self._module = name
        self._logger = logging.getLogger(name)
        self._logger.debug("Errors in module: %s", name)


class PyLintStream(object):
    def __init__(self, parser, level):
        self._parser = parser
        self._level = level

    def write(self, message):
        self._parser.parse(message, level=self._level)


def split(string, sep=None, maxsplit=-1):
    return [p.strip() for p in string.split(sep=sep, maxsplit=maxsplit)]


class PyLintError(namedtuple(
        'PyLintError', ('file_name', 'line', 'tag', 'message'))):
    '''Model for basic python module details
    '''

    def pretty_format(self):
        return '{file_name}:{line}: {tag} {message}'.format(
            **self._asdict()
        )


class PylintErrors(object):
    _has_errors = False

    def __init__(self):
        self._errors = defaultdict(list)

    def add(self, module_name, file_name, line, tag, message):
        self._has_errors = True
        self._errors[module_name].append(
            PyLintError(
                file_name=file_name,
                line=int(line),
                tag=tag,
                message=message
            )
        )

    def __bool__(self):
        return self._has_errors

    def __iter__(self):
        for file_name in sorted(self._errors):
            yield file_name, sorted(self._errors[file_name])

    def pretty_print(self):
        for module_name, errors in self:
            logger = logging.getLogger(module_name)
            logger.error(
                "\nModule %s has %d error(s):", module_name, len(errors)
            )
            for e in errors:
                logger.error("%s", e.pretty_format())


if __name__ == '__main__':
    main()
