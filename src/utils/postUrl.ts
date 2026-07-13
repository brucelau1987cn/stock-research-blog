import type { CollectionEntry } from 'astro:content';

// Normalize public post URLs:
// - A-share trackers strip optional YYYYMMDD- prefix
// - all non-monthly slugs are lowercased so Cloudflare/static hosting
//   never soft-404s on case mismatches like /NU-nubank/
export function getPostSlug(post: CollectionEntry<'blog'>) {
	const tags = post.data.tags ?? [];
	const id = String(post.id || '');

	if (tags.includes('白发股神') && /^\d{6}$/.test(id)) {
		// Monthly tweet digests stay numeric, e.g. 202606
		return id;
	}

	if (tags.includes('个股分析')) {
		return id.replace(/^\d{8}-/, '').toLowerCase();
	}

	return id.toLowerCase();
}

export function getPostUrl(post: CollectionEntry<'blog'>) {
	return `/${getPostSlug(post)}/`;
}
