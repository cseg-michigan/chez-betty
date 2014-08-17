import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

requires = [
    'pyramid',
    'pyramid_jinja2',
    'pyramid_debugtoolbar',
    'pyramid_tm',
    'pyramid_beaker',
    'SQLAlchemy',
    'transaction',
    'zope.sqlalchemy',
    'waitress',
    'python3-ldap',
    'qrcode',
    'reportlab',
    'twitter',
    'pytz',
    'psycopg2'
    ]

setup(name='chezbetty',
      version='0.0',
      description='chezbetty',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='chezbetty',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = chezbetty:main
      [console_scripts]
      initialize_chezbetty_db = chezbetty.scripts.initializedb:main
      """,
      )
