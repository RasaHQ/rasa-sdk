module.exports = {
  someSidebar: {
    'Intro': ['index'],
    'Rasa SDK': [
          'running-the-server',
          {
          type: 'category',
          label: 'Writing Custom Actions',
          collapsed: true,
          items: [
              'actions',
              'tracker',
              'dispatcher',
              'events',
          ],
          },
          'rasa-sdk-changelog',
    ],
    'Other Action Servers': ['events'],
    'HTTP API': ['about-http-api','http-api-spec'],
  },
};
