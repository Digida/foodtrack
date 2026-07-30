/**
 * SEO utility — dynamically updates meta tags and JSON-LD structured data.
 * Call SEO.setPage(title, description, url, image, jsonLd) on each page render.
 */
window.SEO = {
  _defaults: {
    title: 'FoodTrack — Digital Trust Infrastructure',
    description: 'Blockchain-powered traceability, certification, and product integrity platform for agrifood supply chains.',
    url: window.location.origin + '/',
    image: window.location.origin + '/icon-512.png',
  },

  setPage(title, description, url, image, jsonLd) {
    // Title
    document.title = title || this._defaults.title;

    // Meta description
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) { meta = document.createElement('meta'); meta.setAttribute('name', 'description'); document.head.appendChild(meta); }
    meta.setAttribute('content', (description || this._defaults.description).substring(0, 300));

    // OG title
    let ogTitle = document.querySelector('meta[property="og:title"]');
    if (!ogTitle) { ogTitle = document.createElement('meta'); ogTitle.setAttribute('property', 'og:title'); document.head.appendChild(ogTitle); }
    ogTitle.setAttribute('content', title || this._defaults.title);

    // OG description
    let ogDesc = document.querySelector('meta[property="og:description"]');
    if (!ogDesc) { ogDesc = document.createElement('meta'); ogDesc.setAttribute('property', 'og:description'); document.head.appendChild(ogDesc); }
    ogDesc.setAttribute('content', (description || this._defaults.description).substring(0, 300));

    // OG url
    let ogUrl = document.querySelector('meta[property="og:url"]');
    if (!ogUrl) { ogUrl = document.createElement('meta'); ogUrl.setAttribute('property', 'og:url'); document.head.appendChild(ogUrl); }
    ogUrl.setAttribute('content', url || this._defaults.url);

    // OG image
    const img = image || this._defaults.image;
    let ogImage = document.querySelector('meta[property="og:image"]');
    if (!ogImage) { ogImage = document.createElement('meta'); ogImage.setAttribute('property', 'og:image'); document.head.appendChild(ogImage); }
    ogImage.setAttribute('content', img);

    // Twitter card
    let twCard = document.querySelector('meta[name="twitter:card"]');
    if (!twCard) { twCard = document.createElement('meta'); twCard.setAttribute('name', 'twitter:card'); document.head.appendChild(twCard); }
    twCard.setAttribute('content', 'summary_large_image');

    let twTitle = document.querySelector('meta[name="twitter:title"]');
    if (!twTitle) { twTitle = document.createElement('meta'); twTitle.setAttribute('name', 'twitter:title'); document.head.appendChild(twTitle); }
    twTitle.setAttribute('content', (title || this._defaults.title).substring(0, 200));

    let twDesc = document.querySelector('meta[name="twitter:description"]');
    if (!twDesc) { twDesc = document.createElement('meta'); twDesc.setAttribute('name', 'twitter:description'); document.head.appendChild(twDesc); }
    twDesc.setAttribute('content', (description || this._defaults.description).substring(0, 200));

    // JSON-LD structured data
    const existingScript = document.getElementById('ld-json');
    if (existingScript) existingScript.remove();
    if (jsonLd) {
      const script = document.createElement('script');
      script.id = 'ld-json';
      script.type = 'application/ld+json';
      script.textContent = JSON.stringify(jsonLd, null, 2);
      document.head.appendChild(script);
    }
  },

  reset() {
    this.setPage(
      this._defaults.title,
      this._defaults.description,
      this._defaults.url,
      this._defaults.image,
      null
    );
  }
};