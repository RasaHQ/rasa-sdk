const remarkSources = require('remark-sources');
const remarkCollapse = require('remark-collapse'); // TODO: probably won't need this one
const { remarkProgramOutput } = require("./plugins/program_output");

let versions = [];
try {
  versions = require('./versions.json');
} catch (ex) {
  // Nothing to do here, in dev mode, only
  // one version of the doc is available
}
let legacyVersions = [];

const URL = "https://rasa.com";
// FIXME: remove "next/" when releasing + remove the "next/" in
// https://github.com/RasaHQ/rasa-website/blob/master/netlify.toml
const BASE_URL = "/docs/rasa-sdk/next/";


module.exports = {
  title: 'Rasa SDK Documentation',
  tagline: 'Rasa SDK Documentation',
  // TODO: is it needed?
  url: URL
  baseUrl: BASE_URL
  onBrokenLinks: 'throw',
  favicon: 'img/favicon.ico',
  organizationName: 'RasaHQ',
  projectName: 'rasa-sdk',
  themeConfig: {
    navbar: {
      title: 'Rasa SDK',
      logo: {
        alt: 'Rasa',
        src: 'https://rasa.com/static/60e441f8eadef13bea0cc790c8cf188b/rasa-logo.svg',
      },
      items: [
        {
          label: 'Docs',
          to: '/', // "fake" link
          position: 'left',
          items: versions.length > 0 ? [
            {
              label: versions[0],
              to: '/',
              activeBaseRegex: versions[0],
            },
            ...versions.slice(1).map((version) => ({
              label: version,
              to: `${version}/`,
              activeBaseRegex: version,
            })),
            ...legacyVersions,
          ] : [
            {
              label: 'Latest',
              to: '/',
              activeBaseRegex: `/`,
            },
            ...legacyVersions,
          ],
        },
      ],
    },
    footer: {
      style: 'dark',
      copyright: `Copyright © ${new Date().getFullYear()} Rasa Technologies GmbH`,
    },
    gtm: {
      containerID: 'GTM-PK448GB',
    },
  },
  themes: [
    ['@docusaurus/theme-classic', {
      customCss: require.resolve('./src/css/custom.css'),
    }],
  ],
  plugins: [
    ['@docusaurus/plugin-content-docs', {
      // https://v2.docusaurus.io/docs/next/docs-introduction/#docs-only-mode
      routeBasePath: '/',
      // It is recommended to set document id as docs home page (`docs/` path).
      homePageId: 'index',
      sidebarPath: require.resolve('./sidebars.js'),
      editUrl: 'https://github.com/rasahq/rasa-sdk/edit/master/docs/',
      remarkPlugins: [
        [ remarkCollapse, { test: '' }],
        remarkSources,
        // remarkProgramOutput
      ],
    }],
    ['@docusaurus/plugin-sitemap', {
      cacheTime: 600 * 1000, // 600 sec - cache purge period
      changefreq: 'weekly',
      priority: 0.5,
    }],
  ],
};
