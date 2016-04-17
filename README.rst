Flash Services
--------------

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
