// @ts-check

const configure = require('@rasahq/docusaurus-tabula/configure');

module.exports = configure({
  /**
   * site
   */
  title: 'Rasa Action Server',
  tagline: 'Rasa Action Server',
  projectName: 'rasa-sdk',
  /**
   * presets
   */
  openApiSpecs: [
    {
      id: 'rasa-sdk-http-api',
      specPath: '/spec/action-server.yml',
      pagePath: '/pages/action-server-api',
    },
  ],
  /**
   * plugins
   */

  /**
   * themes
   */
  productLogo: '/img/logo-rasa-oss.png',
  staticDirectories: ['static'],
});
