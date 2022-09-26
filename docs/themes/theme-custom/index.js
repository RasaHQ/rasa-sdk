module.exports = function (context) {
  const {
    siteConfig: { url: siteUrl, baseUrl },
  } = context;

  return {
    name: 'theme-custom',
    injectHtmlTags() {
      return {
        headTags: [
          {
            tagName: 'meta',
            attributes: {
              property: 'og:image',
              content: `${siteUrl}${baseUrl}img/og-image.png`,
            },
          },
        ],
      };
    },
  };
};
