"""Tests that all manuals can be built.
"""


import os, sys

from reportlab.test import unittest
from reportlab.test.utils import SecureTestCase


class ManualTestCase(SecureTestCase):
    "Runs all 3 manual-builders from the top."
    
    def test1(self):
        "Test if all manuals buildable from source."

        import reportlab
        rlFolder = os.path.dirname(reportlab.__file__)
        docsFolder = os.path.join(rlFolder, 'docs')
        os.chdir(docsFolder)

        if os.path.isfile('userguide.pdf'):
            os.remove('userguide.pdf')
        if os.path.isfile('graphguide.pdf'):
            os.remove('graphguide.pdf')
        if os.path.isfile('reference.pdf'):
            os.remove('reference.pdf')
        if os.path.isfile('graphics_reference.pdf'):
            os.remove('graphics_reference.pdf')
        
        os.system("python genAll.py -s")

        assert os.path.isfile('userguide.pdf'), 'genAll.py failed to generate userguide.pdf!'
        assert os.path.isfile('graphguide.pdf'), 'genAll.py failed to generate graphguide.pdf!'
        assert os.path.isfile('reference.pdf'), 'genAll.py failed to generate reference.pdf!'
        assert os.path.isfile('graphics_reference.pdf'), 'genAll.py failed to generate graphics_reference.pdf!'
        

def makeSuite():
    suite = unittest.TestSuite()
    
    suite.addTest(ManualTestCase('test1'))
    return suite


#noruntests
if __name__ == "__main__":
    unittest.TextTestRunner().run(makeSuite())
