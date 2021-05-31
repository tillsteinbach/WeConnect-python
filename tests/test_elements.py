import os
import json

import pytest

from weconnect import elements

SCRIPTLOC = os.path.dirname(__file__)


@pytest.mark.parametrize('className, testcase', [(elements.ClimatizationTimer, 'complete')])
def test_Elements(request, className, testcase):
    with open(f'{request.config.rootdir}/tests/ressources/elements/{className.__name__}/{testcase}.json') as file:
        dict = json.load(file)
        element = className(parent=None, statusId='test', fromDict=dict)

        element2 = className(parent=None, statusId='test', fromDict=None)
        element2.update(dict)
        print(repr(str(element2)))

        assert element is not None

        with open(f'{request.config.rootdir}/tests/ressources/elements/{className.__name__}/{testcase}.resultstr') \
                as resultStringFile:
            expectedResult = resultStringFile.read()

            assert expectedResult == str(element2)
