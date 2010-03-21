#!/usr/bin/python
# -*- coding: utf8 -*-

from distutils.core import setup
import florun

files = ["icons/*", "examples/*"]

setup( name         = florun.__title__,
       version      = florun.__version__,
       license      = florun.__license__,
       #platform     = florun.__platform__,
       description  = florun.__description__,
       author       = florun.__author__,
       author_email = florun.__email__,
       url          = florun.__url__,
       long_description = florun.__long_description__,
       
    packages     = ['florun'],
    package_data = {'florun' : files },
    scripts      = ["runner"],
    #requires     = ['PyQt4>4'],
    #provides     = ['florun'],
    #classifiers  = ['Programming Language :: Python'],
) 
