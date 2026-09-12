from distutils.core import setup
from Cython.Build import cythonize
import numpy

setup(
    ext_modules=cythonize(
        "model_help.pyx", compiler_directives={"language_level": "3"}
    ),
    include_dirs=[numpy.get_include()],
)
