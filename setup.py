#!/usr/bin/python
# -*- coding: utf8 -*-
from setuptools import setup, find_packages

import florun

files = ["icons/*", "examples/*"]

setup(name         = florun.__title__,
      version      = florun.__version__,
      license      = florun.__license__,
      description  = florun.__description__,
      author       = florun.__author__,
      author_email = florun.__email__,
      url          = florun.__url__,
      long_description = florun.__long_description__,

      provides     = ['florun'],
      packages     = find_packages(),
      package_data = {'florun' : files },
      scripts      = ["florun.py"],
      platforms    = ('any',),
      requires     = ['PyQt (>=4.6)'],
      keywords     = ['flow', 'PyQt', 'GUI'],
      classifiers  = ['Programming Language :: Python :: 2.5',
                      'Operating System :: OS Independent',
                      'Intended Audience :: End Users/Desktop',
                      'Natural Language :: English',
                      'Topic :: Utilities',
                      'Development Status :: %s' % florun.__status__],
) 
