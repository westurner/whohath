#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function
"""
whohath -- a package lookup utility
"""
from collections import namedtuple, OrderedDict

LICENSE_INFO = ("""
Whohath, Copyright (C) 2014 Wes Turner.
 Whohath comes with ABSOLUTELY NO WARRANTY;
 for details, run `%s --license`.
 This is free software, and you are welcome to redistribute it
 under certain conditions; run `%s --license` for details. (GPLv2)
""" % (__file__, __file__))

def print_license_info(short=True, fulltext=False):
    if short:
        print(LICENSE_INFO)
    if fulltext:
        import os
        path = os.path.join(os.path.dirname(__file__), '..', 'LICENSE')
        with open(path) as f:
            print(f.read())


class Package(namedtuple('Package', ('name', 'version',))):
    pass


class Distro(object):
    name = None
    version = None

    def __init__(self, name=None, version=None):
        if name:
            self.name = name
        else:
            self.name = self.__class__.__name__

        if version:
            self.version = version

    def __str__(self):
        return u'-'.join((self.name, self.version))

    def find_package(self, pkgstr):
        raise NotImplemented


class MockLinux(Distro):
    def find_package(self, pkgstr):
        return [ Package(pkgstr, 'todo') ] # XXX


class DistroRegistry(OrderedDict):
    def register(self, distro):
        self[str(distro)] = distro


def get_distro_registry():
    registry = DistroRegistry()
    registry.register(MockLinux(version='3000'))
    return registry


def whohath(pkgstr, distrospec=None, distro_registry=None):
    """
    find matching packages in each distro matching distrospec
    """
    distro_registry = distro_registry or get_distro_registry()
    for distrokey, distro in distro_registry.iteritems():
        if not distrospec or distrokey in distrospec:  # XXX
            for pkg in distro.find_package(pkgstr):
                yield (distro, pkg)


def print_whohath_results(results):
    if not results:
        print("... None...")
        return
    for distro, result in results:
        print("%s :: %s" % (distro, result))


import unittest
class Test_whohath(unittest.TestCase):
    def test_whohath(self):
        PKGNAME = "python"
        distrospec = None
        whohath(PKGNAME, distrospec=distrospec)

    def test_main(self):
        IO = (
            (tuple(), 2),
            (('python',), 0),
        )
        for I, O in IO:
            args = list(I)
            output = main(*args)
            try:
                self.assertEqual(output, O)
            except:
                print("Input: %s" % str(args))
                raise


def main(*args):
    import logging
    import optparse
    import sys

    prs = optparse.OptionParser(
        usage="%prog <pkgstr>",
        description=LICENSE_INFO,
    )

    prs.add_option('-d', '--distro',
                    dest='distros',
                    action='append',)

    prs.add_option('--license',
                    dest='license',
                    action='store_true',
                    help='Print GPLv2 License Text')

    prs.add_option('-v', '--verbose',
                    dest='verbose',
                    action='store_true',)
    prs.add_option('-q', '--quiet',
                    dest='quiet',
                    action='store_true',)
    prs.add_option('-t', '--test',
                    dest='run_tests',
                    action='store_true',)

    args = args and list(args) or sys.argv[1:]
    (opts, args) = prs.parse_args(args=args)

    if not opts.quiet:
        logging.basicConfig()

        if opts.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

    if opts.run_tests:
        sys.argv = [sys.argv[0]] + args
        import unittest
        sys.exit(unittest.main())

    if opts.license:
        print_license_info(fulltext=True)
        return 0

    if len(args) != 1:
        err = "Must specify a package string"
        #prs.error(err)
        print(err)
        return 2

    pkgstr = args[0]
    distrospec = opts.distros

    results = whohath(pkgstr, distrospec)
    print_whohath_results(results)

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
