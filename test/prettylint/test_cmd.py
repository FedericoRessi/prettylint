'''Functional tests for prettylint command line interface
'''

from subprocess import check_output, CalledProcessError

import pytest


def test_empty_parameters():
    '''Test it fails when called without arguments
    '''

    # When
    with pytest.raises(CalledProcessError) as excinfo:
        check_output("prettylint")

    # Then
    assert excinfo.value.output == b""
