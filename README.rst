Flash Services
--------------

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

The services that can be shown on a `Flash`_ dashboard.

Available services
==================

The following service definitions include the configuration options:

* ``github`` - for project repositories on `GitHub`_

  * ``api_token`` (required),
  * ``account`` (required - the name of the account the project is in, e.g.
    ``"textbook"``)
  * ``repo`` (required - the name of the project repository within that account,
    e.g. ``"flash"``)
  * ``branch`` (the name of the branch to show commits from, defaulting to the
    repository's default branch, which is usually ``master``).

* ``codeship`` - for CI builds on `Codeship`_

  * ``api_token`` (required)
  * ``project_id`` (required)

* ``tracker`` - for projects on `Pivotal Tracker`_

  * ``api_token`` (required)
  * ``project_id`` (required)

* ``travis`` - for CI builds on `Travis CI`_ (currently only supports open-
  source builds on the ``.org`` site).

  * ``account`` (required)
  * ``app`` (required)

.. _Codeship: https://codeship.com/
.. _Flash: https://github.com/textbook/flash
.. _GitHub: https://github.com/
.. _Pivotal Tracker: https://www.pivotaltracker.com/
.. _Travis CI: https://travis-ci.org/
