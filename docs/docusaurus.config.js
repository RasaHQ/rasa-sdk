const path = require('path');
const {
  rehypePlugins: themeRehypePlugins,
  remarkPlugins: themeRemarkPlugins,
} = require('@rasahq/docusaurus-theme-tabula');
const { remarkProgramOutput } = require("./plugins/program_output");

const isDev = process.env.NODE_ENV === 'development';

let existingVersions = [];
try { existingVersions = require('./versions.json'); } catch (e) { console.info('no versions.json file found') }

const BASE_URL = '/docs/action-server/';
const SITE_URL = 'https://rasa.com';
// NOTE: this allows switching between local dev instances of rasa/rasa and rasa/rasa-x
const RASA_OPEN_SOURCE_SWAP_URL = isDev ? 'http://localhost:3000' : SITE_URL;
const RASA_X_SWAP_URL = isDev ? 'http://localhost:3001' : SITE_URL;

const versionLabels = {
  current: 'Master/Unreleased'
};

module.exports = {
  customFields: {
    productLogo: '/img/logo-rasa-oss.png',
    versionLabels,
    redocPages: [
      {
        title: 'Rasa Action Server API',
        specUrl: '/spec/action-server.yml',
        slug: '/pages/action-server-api',
      }
    ]
  },
  title: 'Rasa Action Server Documentation',
  tagline: 'Rasa Action Server Documentation',
  url: SITE_URL,
  baseUrl: BASE_URL,
  favicon: '/img/favicon.ico',
  organizationName: 'RasaHQ',
  projectName: 'rasa-sdk',
  themeConfig: {
    algolia: {
      // this is configured via DocSearch here:
      // https://github.com/algolia/docsearch-configs/blob/master/configs/rasa.json
      disabled: true,
      apiKey: '25626fae796133dc1e734c6bcaaeac3c', // FIXME: replace with values from our own index
      indexName: 'rasa',
      inputSelector: '.search-bar',
      searchParameters: {
        'facetFilters': ["tags:rasa-action-server"]
      }
    },
    navbar: {
      hideOnScroll: false,
      title: 'Rasa Action Server',
      items: [
        {
          label: 'Rasa Open Source',
          href: `${RASA_OPEN_SOURCE_SWAP_URL}/docs/rasa/`,
          position: 'left',
        },
        {
          label: 'Rasa X',
          position: 'left',
          href: `${RASA_X_SWAP_URL}/docs/rasa-x/`,
          target: '_self',
        },
        {
          label: 'Rasa Action Server',
          position: 'left',
          to: path.join('/', BASE_URL),
        },
        {
          href: 'https://github.com/rasahq/rasa',
          className: 'header-github-link',
          'aria-label': 'GitHub repository',
          position: 'right',
        },
        {
          target: '_self',
          href: 'https://blog.rasa.com/',
          label: 'Blog',
          position: 'right',
        },
        {
          label: 'Community',
          position: 'right',
          items: [
            {
              target: '_self',
              href: 'https://rasa.com/community/join/',
              label: 'Community Hub',
            },
            {
              target: '_self',
              href: 'https://forum.rasa.com',
              label: 'Forum',
            },
            {
              target: '_self',
              href: 'https://rasa.com/community/contribute/',
              label: 'How to Contribute',
            },
            {
              target: '_self',
              href: 'https://rasa.com/showcase/',
              label: 'Community Showcase',
            },
          ],
        },
      ],
    },
    footer: {
      copyright: `Copyright © ${new Date().getFullYear()} Rasa Technologies GmbH`,
    },
    gtm: {
      containerID: 'GTM-MMHSZCS',
    },
  },
  themes: [
    '@docusaurus/theme-search-algolia',
    '@rasahq/docusaurus-theme-tabula',
  ],
  plugins: [
    ['@docusaurus/plugin-content-docs', {
      // https://v2.docusaurus.io/docs/next/docs-introduction/#docs-only-mode
      routeBasePath: '/',
      sidebarPath: require.resolve('./sidebars.js'),
      editUrl: 'https://github.com/rasahq/rasa-sdk/edit/master/docs/',
      showLastUpdateTime: true,
      showLastUpdateAuthor: true,
      rehypePlugins: [
        ...themeRehypePlugins,
      ],
      remarkPlugins: [
        ...themeRemarkPlugins,
        remarkProgramOutput,
      ],
      lastVersion: existingVersions[0] || 'current', // aligns / to last versioned folder in production
      versions: {
        current: {
          label: versionLabels['current'],
          path: existingVersions.length < 1 ? '' : 'next',
        },
      },
    }],
    ['@docusaurus/plugin-content-pages', {}],
    ['@docusaurus/plugin-sitemap',
      {
        cacheTime: 600 * 1000, // 600 sec - cache purge period
        changefreq: 'weekly',
        priority: 0.5,
      }],
    isDev && ['@docusaurus/plugin-debug', {}],
    [path.resolve(__dirname, './plugins/google-tagmanager'), {}],
  ].filter(Boolean),
};
