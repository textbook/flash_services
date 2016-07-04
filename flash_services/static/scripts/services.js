/* globals updateCommit,updateItems,updateOutcome */

function builds(pane, data) {
  if (data.builds) {
    updateItems(pane, data.builds, '.build-outcome', updateOutcome);
  }
}

function gh_issues(pane, data) {
  pane.find('.half-life').text(data.halflife || 'N/A');
  if (data.issues) {
    var states = ['open-issues', 'closed-issues', 'open-pull-requests',
                  'closed-pull-requests'];
    states.forEach(function (state) {
      pane.find('.' + state).text(data.issues[state] || 0);
    });
  }
}

function github(pane, data) {
  if (data.commits) {
    updateItems(pane, data.commits, '.commit', updateCommit);
  }
}

var SERVICES = {
  codeship: builds,
  coveralls: function (pane, data) {
    if (data.builds) {
      updateItems(pane, data.builds, '.coverage', function (element, data) {
        ['author', 'committed', 'coverage', 'message_text'].forEach(function (attr) {
          element.find('.' + attr).text(data[attr]);
        });
      });
    }
  },
  gh_issues: gh_issues,
  ghe_issues: gh_issues,
  github: github,
  github_enterprise: github,
  tracker: function (pane, data) {
    if (data.velocity) { pane.find('.velocity').text(data.velocity); }
    if (data.stories) {
      pane.find('.ready').text(
        (data.stories.planned || 0) + (data.stories.unstarted || 0)
      );
      pane.find('.accepted').text(data.stories.accepted || 0);
      pane.find('.in-flight').text(data.stories.started || 0);
      pane.find('.completed').text(
        (data.stories.finished || 0) + (data.stories.delivered || 0)
      );
    }
  },
  travis: builds,
  travis_pro: builds
};
