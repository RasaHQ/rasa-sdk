// @ts-check

const tabula = require('@rasahq/docusaurus-tabula');

module.exports = tabula.use({
  title: 'Rasa Action Server',
  tagline: 'Rasa Action Server',
  productLogo: '/img/logo-rasa-oss.png',
  productKey: 'rasa-sdk',
  staticDirectories: ['static'],
  openApiSpecs: [
    {
      title: 'Rasa Action Server API',
      specUrl: '/spec/action-server.yml',
      slug: '/pages/action-server-api',
    },
  ],
});
