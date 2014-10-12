#!/usr/bin/env python
# encoding: utf-8
from __future__ import print_function
"""
whohath -- a package lookup utility


Distro
  name
  version
  repos
    Repo

  packages
    Package
      distro
      repo
      name
      version
      date
      size
      checksum
      signature
      url

Distro / Repository relation

"""
import logging
from collections import namedtuple, OrderedDict
import bs4
import requests
import requests_cache

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger()

requests_cache.install_cache('whohathcache.db', backend='sqlite',
  expire_after=60*60*12)

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


class Package(namedtuple('Package',
    ('distro',
     'repo',
     'name',
     'version',
     'desc',
     'date',
     'size',
     'checksum',
     'signature',
     'url'))):
    def __new__(cls,
        distro,
        repo,
        name,
        version,
        desc=None,
        date=None,
        size=None,
        checksum=None, # TODO: multiple checksums
        signature=None,
        url=None):
        return super(Package, cls).__new__(cls,
            distro,
            repo,
            name,
            version,
            desc,
            date,
            size,
            checksum,
            signature,
            url)


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

    __repr__ = __str__

    def find_package(self, pkgstr):
        raise NotImplemented


class Repo(namedtuple('Repo', ('name', 'url',))):
    def __new__(cls, name, url=None):
        if url is None:
            if name.startswith('http'):
                url = name
        return super(Repo, cls).__new__(cls, name, url)


    def __unicode__(self):
        return self.url

    __str__ = __repr_ = __unicode__


class MockLinux(Distro):
    repos = [
        Repo('http://example.org'),]

    def find_package(self, pkgstr):
        for repo in self.repos:
            yield Package(self, repo, pkgstr, 'todo')


class Debian(Distro):
    packages_base_url = 'http://packages.debian.org'
    html_list_base_url = 'http://packages.debian.org/%s/allpackages'
    names = OrderedDict((
        ('squeeze',('squeeze', 'squeeze-updates', 'squeeze-backports',
                    'squeeze-backports-sloppy'),),
        ('wheezy', ('wheezy', 'wheezy-updates', 'wheezy-backports'),),
        ('jessie', ('jessie',),),
        ('sid',    ('sid',),),
        ('experimental', ('experimental',),),
    ))

    repos = [] # TODO

    def get_packages_from_html_list(self, name):
        url = self.html_list_base_url % name
        r = requests.get(url, headers={'Accept':'text/html'})
        log.debug("Retrieving: %r" % url)
        if r.status_code != requests.codes.OK:
            raise Exception("Error requesting: %r: status_code: %s" %
                           (url, r.status_code))
        bs = bs4.BeautifulSoup(r.content)
        for dt in bs.find_all('dt'):
            try:
                dd = dt.find_next('dd')
                pkgdesc = dd.text
                if (pkgdesc.startswith('virtual package provided by')
                    and ') [' not in dt.text):
                    continue

                a = dt.find('a').extract()
                pkgname = a.text
                if ') [' in dt.text:
                    version, reponame = dt.text[1:].split(') [', 1)
                    version = version.lstrip('(')
                    reponame = reponame.rstrip(']')
                else:
                    version = dt.text.strip(' ()')
                    reponame = ''

                _reponame = "%s--%s--%s" % (self, name, reponame)
                _repo = Repo(name=_reponame, url=url) ## TODO: lookup from [...]

                url = "%s/%s/%s" % (self.packages_base_url, name, pkgname)

                yield Package(
                    distro=self,
                    repo=_repo, # XXX
                    name=pkgname,
                    version=version,
                    desc=pkgdesc,
                    url=url)
            except:
                log.error(dt)
                log.error(dd)
                raise

    def get_all_packages_from_all_html_lists(self):
        for distroname, pkgsets in self.names.iteritems():
            for pkgset in pkgsets:
                logging.debug("%s: %s" % (distroname, pkgset))
                for pkg in self.get_packages_from_html_list(pkgset):
                    yield pkg


    def find_package(self, pkgstr):
        packages = self.get_all_packages_from_all_html_lists() # TODO
        for pkg in packages:
            if pkgstr in pkg.name: # XXX: TODO: match_pkgname()
                yield pkg


class Ubuntu(Debian):
    packages_base_url = 'http://packages.ubuntu.com'
    html_list_base_url = 'http://packages.ubuntu.com/%s/allpackages'
    names = OrderedDict((
        ('lucid',   ('lucid', 'lucid-updates', 'lucid-backports'),),
        ('precise', ('precise', 'precise-updates', 'precise-backports'),),
        ('quantal', ('quantal', 'quantal-updates', 'quantal-backports'),),
        ('raring',  ('raring', 'raring-updates', 'raring-backports'),),
        ('saucy',   ('saucy', 'saucy-updates', 'saucy-backports'),),
        ('trusty',  ('trusty',)),
    ))

    repos = []


class DistroRegistry(OrderedDict):
    def register(self, distro):
        self[str(distro)] = distro


def get_distro_registry():
    registry = DistroRegistry()
    registry.register(MockLinux(version='3000'))
    registry.register(Debian(version='uhh')) # TODO
    registry.register(Ubuntu(version='huh')) # TODO
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
