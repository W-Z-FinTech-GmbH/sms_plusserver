# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import os
from setuptools import setup


with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme_file:
    long_description = readme_file.read()


setup(
    name='sms_plusserver',
    version='0.2.0',
    description=(
        'Python library that allows to send messages using Plusserver SMS '
        'platform.'
    ),
    long_description=long_description,
    url='https://github.com/W-Z-FinTech-GmbH/sms_plusserver',
    author='W&Z FinTech GmbH',
    author_email='dk@ownly.de',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Utilities',
    ],
    keywords='sms plusserver message text phone',
    py_modules=['sms_plusserver'],
    install_requires=[
        'requests >= 2.1',
        'six',
    ],
    test_suite='tests',
    tests_require=[
        'mock',
    ]
)
