from bs4 import BeautifulSoup


def test_coveralls_section_without_builds(jinja):
    context = _create_context('fake-service', {'builds': []})

    soup = _render(jinja, 'partials/coveralls-section.html', context)

    assert 'coveralls-pane' in soup.find('section', class_='pane')['class']
    assert len(soup.find_all('div', class_='pane-item')) == 4


def test_coveralls_section_with_builds(jinja):
    builds = [
        _coverage('10%', 'Alice', 'one minute ago', 'one'),
        _coverage('20%', 'Bob', 'two minutes ago', 'two'),
        _coverage('30%', 'Chris', 'three minutes ago', 'three'),
        _coverage('40%', 'Dipak', 'four minutes ago', 'four'),
    ]
    context = _create_context('fake-service', {'builds': builds})

    soup = _render(jinja, 'partials/coveralls-section.html', context)

    assert 'coveralls-pane' in soup.find('section', class_='pane')['class']
    items = soup.find_all('div', class_='pane-item')
    _assert_contains(items, 'author', ['Alice', 'Bob', 'Chris', 'Dipak'])
    _assert_contains(items, 'coverage', ['10%', '20%', '30%', '40%'])
    _assert_contains(items, 'message_text', ['one', 'two', 'three', 'four'])
    _assert_contains(
        items,
        'committed',
        [
            'one minute ago',
            'two minutes ago',
            'three minutes ago',
            'four minutes ago',
        ],
    )


def test_issues_section_with_halflife(jinja):
    context = _create_context('fake-service', dict(
        issues={
            'open-issues': 1,
            'closed-issues': 2,
            'open-pull-requests': 3,
            'closed-pull-requests': 4,
        },
        halflife='one day',
    ))

    soup = _render(jinja, 'partials/gh-issues-section.html', context)

    assert 'gh_issues-pane' in soup.find('section', class_='pane')['class']
    items = soup.find_all('div', class_='pane-item')
    _assert_contains(items, 'count', ['1', '2', '3', '4', 'one day'])
    _assert_classes_contain(
        [item.find(class_='count') for item in items],
        [
            'open-issues',
            'closed-issues',
            'open-pull-requests',
            'closed-pull-requests',
            'half-life',
        ],
    )


def test_issues_section_without_halflife(jinja):
    context = _create_context('fake-service', dict(
        issues={
            'open-issues': 1,
            'closed-issues': 2,
            'open-pull-requests': 3,
            'closed-pull-requests': 4,
        },
    ))

    soup = _render(jinja, 'partials/gh-issues-section.html', context)

    assert 'gh_issues-pane' in soup.find('section', class_='pane')['class']
    items = soup.find_all('div', class_='pane-item')
    _assert_contains(items, 'count', ['1', '2', '3', '4', 'N/A'])


def test_tracker_section(jinja):
    context = _create_context('fake-service', dict(
        stories={'ready': 10, 'in-flight': 2, 'completed': 3, 'accepted': 0},
        velocity=7,
    ))

    soup = _render(jinja, 'partials/tracker-section.html', context)

    assert 'tracker-pane' in soup.find('section', class_='pane')['class']
    items = soup.find_all('div', class_='pane-item')
    _assert_contains(items, 'count', ['7', '10', '2', '3', '0'])
    _assert_contains(
        items,
        'item-title',
        ['Velocity: ', 'Ready: ', 'In flight: ', 'Completed: ', 'Accepted: '],
    )
    _assert_classes_contain(
        [item.find(class_='count') for item in items],
        ['velocity', 'ready', 'in-flight', 'completed', 'accepted'],
    )


def test_tracker_section_missing_categories(jinja):
    context = _create_context('fake-service', dict(
        stories={'ready': 10, 'completed': 3},
        velocity=7,
    ))

    soup = _render(jinja, 'partials/tracker-section.html', context)

    assert 'tracker-pane' in soup.find('section', class_='pane')['class']
    items = soup.find_all('div', class_='pane-item')
    _assert_contains(items, 'count', ['7', '10', '0', '3', '0'])


def _assert_contains(items, cls, expected):
    assert [element.find(class_=cls).string for element in items] == expected


def _assert_classes_contain(items, classes):
    for item, cls in zip(items, classes):
        assert cls in item['class']


def _coverage(coverage, author, committed, message_text):
    return dict(
        coverage=coverage,
        message_text=message_text,
        committed=committed,
        author=author,
    )


def _render(jinja, template, context):
    rendered = jinja.get_template(template).render(context)
    return BeautifulSoup(rendered, 'html.parser')


def _create_context(service_name, service_data=None):
    service_id = 'abc123'
    return dict(
        service_id=service_id,
        service_data=service_data,
        service={'service_name': service_name},
    )
