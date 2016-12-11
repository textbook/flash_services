Flash Services
--------------

.. image:: https://img.shields.io/pypi/v/flash_services.svg
    :target: https://pypi.python.org/pypi/flash_services
    :alt: PyPI Version

.. image:: https://travis-ci.org/textbook/flash_services.svg?branch=master
  :target: https://travis-ci.org/textbook/flash_services
  :alt: Travis Build Status

.. image:: https://coveralls.io/repos/github/textbook/flash_services/badge.svg?branch=master
  :target: https://coveralls.io/github/textbook/flash_services?branch=master
  :alt: Test Coverage

.. image:: https://www.quantifiedcode.com/api/v1/project/9f4a57999d474c9db7210dd9e576ac6a/badge.svg
  :target: https://www.quantifiedcode.com/app/project/9f4a57999d474c9db7210dd9e576ac6a
  :alt: Code Issues

.. image:: https://api.codacy.com/project/badge/grade/c20159586c524b108e17609d11a88688
  :target: https://www.codacy.com/app/j-r-sharpe-github/flash_services
  :alt: Other Code Issues

.. image:: https://img.shields.io/badge/license-ISC-blue.svg
  :target: https://github.com/textbook/flash_services/blob/master/LICENSE
  :alt: ISC License

The services that can be shown on a `Flash`_ dashboard. Includes the service
update code and any custom templates not available in the core Flash package.

Documentation
=============

Documentation is available on PythonHosted_.

Available services
==================

The following service definitions include the configuration options:

* ``codeship`` - for CI builds on `Codeship`_

  * ``api_token`` (required)
  * ``project_id`` (required)

* ``coveralls`` - for coverage reporting on `Coveralls`_ (currently only
  supports open-source builds)

  * ``vcs_name`` (required - the name of the service the project is accessed
    via, e.g. ``'github'``)
  * ``account`` (required - the name of the account the project is in, e.g.
    ``"textbook"``)
  * ``repo`` (required - the name of the project repository within that account,
    e.g. ``"flash"``)
  * ``ok_threshold`` (the minimum coverage level to show as an OK state,
    defaults to 80%)
  * ``neutral_threshold`` (the minimum coverage level to show as a neutral
    state, defaults to 50%)

* ``gh_issues`` - for issues and PRs in project repositories on `GitHub`_

  * ``api_token`` (required),
  * ``account`` (required - the name of the account the project is in, e.g.
    ``"textbook"``)
  * ``repo`` (required - the name of the project repository within that account,
    e.g. ``"flash"``)
  * ``neutral_threshold`` (the maximum half life to show as a neutral state,
    in days, defaults to 30)
  * ``ok_threshold`` (the maximum half life to show as an OK state, in days,
    defaults to 7)

* ``ghe_issues`` - for issues and PRs in project repositories on
  `GitHub Enterprise`_ installations

  * ``api_token`` (required),
  * ``account`` (required - the name of the account the project is in, e.g.
    ``"textbook"``)
  * ``repo`` (required - the name of the project repository within that account,
    e.g. ``"flash"``)
  * ``neutral_threshold`` (the maximum half life to show as a neutral state,
    in days, defaults to 30)
  * ``ok_threshold`` (the maximum half life to show as an OK state, in days,
    defaults to 7)

* ``github`` - for project repositories on `GitHub`_

  * ``api_token`` (required),
  * ``account`` (required - the name of the account the project is in, e.g.
    ``"textbook"``)
  * ``repo`` (required - the name of the project repository within that account,
    e.g. ``"flash"``)
  * ``branch`` (the name of the branch to show commits from, defaulting to the
    repository's default branch, which is usually ``master``)

* ``github_enterprise`` - for project repositories on `GitHub Enterprise`_
  installations

  * ``api_token`` (required),
  * ``account`` (required - the name of the account the project is in, e.g.
    ``"textbook"``)
  * ``repo`` (required - the name of the project repository within that account,
    e.g. ``"flash"``)
  * ``branch`` (the name of the branch to show commits from, defaulting to the
    repository's default branch, which is usually ``master``)

* ``jenkins`` - for CI builds on `Jenkins`_ instances.

  * ``username`` (required)
  * ``password`` (required)
  * ``root`` (required - the root URL for the Jenkins instance)
  * ``job`` (required - the name of the job, which must match the job URL)

* ``tracker`` - for projects on `Pivotal Tracker`_

  * ``api_token`` (required)
  * ``project_id`` (required)

* ``travis`` - for public CI builds on `Travis CI (.org)`_.

  * ``account`` (required)
  * ``app`` (required)

* ``travis_pro`` - for private CI builds on `Travis CI (.com)`_

  * ``account`` (required)
  * ``api_token`` (required - see `Travis API docs`_ for details)
  * ``app`` (required)

Writing a service
=================

The idea behind this package is to make it easier to add new service providers
to Flash. Each new service should subclass ``Service`` (or one of its more
specific children, where appropriate) from the ``core.py`` file. The mix-in
classes in ``auth.py`` can be used to implement authentication to the service
API endpoint as needed (currently both header and query parameter token
validation are supported).

* Create a new ``Service`` subclass, or use one of the pre-provided
  subclasses for continuous integration or version control systems;
* Use the mix-ins from ``auth.py`` and ``core.py`` to add any required
  authentication, custom root setting and/or health thresholds;
* Define any additional ``REQUIRED`` configuration parameters on the class
  (required parameters from its superclasses will be added automatically);
* Set the appropriate ``TEMPLATE`` for it (if not a standard template, add it
  to ``templates/partials`` - use the `Jinja2`_ templating language);
* Set the ``FRIENDLY_NAME``, for display in the top-left of each pane, if not
  the same as the class name;
* Register the service in **both** ``SERVICES`` objects, using the same key:

  * in Python (``__init__.py``); and
  * in JavaScript (``static/scripts/services.js``, where any service-specific
    client-side behaviour should also be placed).

.. _Codeship: https://codeship.com/
.. _Coveralls: https://coveralls.io/
.. _Flash: https://github.com/textbook/flash
.. _GitHub: https://github.com/
.. _GitHub Enterprise: https://enterprise.github.com/home
.. _Jenkins: https://jenkins.io/
.. _Jinja2: http://jinja.pocoo.org/
.. _Pivotal Tracker: https://www.pivotaltracker.com/
.. _PythonHosted: https://pythonhosted.org/flash_services
.. _Travis API docs: https://docs.travis-ci.com/api?shell#authentication
.. _Travis CI (.org): https://travis-ci.org/
.. _Travis CI (.com): https://travis-ci.com/
