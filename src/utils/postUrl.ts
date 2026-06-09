import type { CollectionEntry } from 'astro:content';

export function getPostUrl(post: CollectionEntry<'blog'>) {
	if (post.data.tags?.includes('白发股神') && /^\d{6}$/.test(post.id)) {
		return `/${post.id}/`;
	}
	return `/${post.id}/`;
}
