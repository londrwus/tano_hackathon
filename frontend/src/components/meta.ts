/* Per-card <meta property="og:image"> etc. Set imperatively so each
   card id gets its own 1080x1350 preview in iMessage / WhatsApp. */

function upsert(attr: 'property' | 'name', key: string, content: string) {
  let el = document.head.querySelector<HTMLMetaElement>(`meta[${attr}="${key}"]`)
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute(attr, key)
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

export function setCardMeta(opts: {
  title: string
  description: string
  ogImage: string
  url: string
}) {
  const abs = (p: string) => (p.startsWith('http') ? p : window.location.origin + p)
  document.title = opts.title
  upsert('property', 'og:type', 'website')
  upsert('property', 'og:title', opts.title)
  upsert('property', 'og:description', opts.description)
  upsert('property', 'og:image', abs(opts.ogImage))
  upsert('property', 'og:image:width', '1080')
  upsert('property', 'og:image:height', '1350')
  upsert('property', 'og:url', abs(opts.url))
  upsert('name', 'twitter:card', 'summary_large_image')
  upsert('name', 'twitter:image', abs(opts.ogImage))
  upsert('name', 'description', opts.description)
}

export function setPageMeta(title: string, description: string) {
  document.title = title
  upsert('name', 'description', description)
}
