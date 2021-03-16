"""A setuptools based setup module.
See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='lockable',
    use_scm_version=True,
    setup_requires=["setuptools_scm"],
    description='lockable resource module',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jupe/py-lockable',
    author='Jussi Vatjus-Anttila',
    author_email='jussiva@gmail.com',

    # Classifiers help users find your project by categorizing it.
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[  # Optional
        'Development Status :: 3 - Alpha',
        "Intended Audience :: Developers",
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Utilities",
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.7',
        "Programming Language :: Python :: 3 :: Only",
    ],
    packages=find_packages(exclude=['tests']),  # Required
    keywords="py.test pytest lockable resource",
    # Specify which Python versions you support.
    python_requires='>=3.7, <4',
    install_requires=[
        'pid',
        'pydash'
    ],
    extras_require={  # Optional
        'dev': ['nose', 'coveralls', 'pylint', 'coverage'],
        'optional': ['pytest-metadata']
    },

    project_urls={  # Optional
        'Bug Reports': 'https://github.com/jupe/pytest-lockable',
        'Source': 'https://github.com/jupe/pytest-lockable/',
    }
)
