#!/usr/bin/env python
from setuptools import setup, find_namespace_packages

setup(
    name='mdlg',
    version='0.0.1',
    license='Apache 2.0',
    url='https://github.com/fturib/mandlagore',
    description='Machine Learning for Mandragore',
    package_dir={'': 'src'},  # tell distutils packages are under src
    packages=find_namespace_packages('src'),  # include all packages under src
    project_urls={'Source Code': 'https://github.com/fturib/mandlagore'},
    install_requires=['click', 'requests'],
    package_data={
        '': ['*.sql'],
    },
    zip_safe=False)
