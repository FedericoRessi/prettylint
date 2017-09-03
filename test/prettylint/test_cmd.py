from subprocess import check_output, CalledProcessError

import pytest


def test_empty_parameters():
    # When
    with pytest.raises(CalledProcessError) as excinfo:
        check_output("prettylint")

    # Then
    assert excinfo.value.output == b""
