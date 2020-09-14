module.exports = {
  someSidebar: {
    'Intro': ['index'],
    'All Action Servers': [
      'actions',
      'events'
    ],
    'Rasa SDK': [
          'running-action-server',
          {
          type: 'category',
          label: 'Writing Custom Actions',
          collapsed: true,
          items: [
              'sdk-actions',
              'sdk-tracker',
              'sdk-dispatcher',
              'sdk-events',
          ],
          },
          'rasa-sdk-changelog',
    ],
    'HTTP API': ['about-http-api','http-api-spec'],
  },
};
