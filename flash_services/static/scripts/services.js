/* globals updateCommit,updateItems,updateOutcome */

var SERVICES = {
  codeship: function (pane, data) {
    if (data.builds) {
      updateItems(pane, data.builds, '.build-outcome', updateOutcome);
    }
  },
  github: function (pane, data) {
    if (data.commits) {
      updateItems(pane, data.commits, '.commit', updateCommit);
    }
  },
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
  travis: function (pane, data) {
    if (data.builds) {
      updateItems(pane, data.builds, '.build-outcome', updateOutcome);
    }
  }
};
