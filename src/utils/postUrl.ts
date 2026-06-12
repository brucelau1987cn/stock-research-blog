import type { CollectionEntry } from 'astro:content';

// 个股分析文章（tags 含「个股分析」+ id 以 YYYYMMDD-6位代码- 开头）
// 链接去掉日期前缀，保证跟踪过程中 URL 稳定
// 规则：post.id 形如 `20260612-002026-swd` → URL 形如 `/002026-swd/`
export function getPostUrl(post: CollectionEntry<'blog'>) {
	const tags = post.data.tags ?? [];
	if (tags.includes('白发股神') && /^\d{6}$/.test(post.id)) {
		// 月度推文页（如 202606）保留原状
		return `/${post.id}/`;
	}
	if (tags.includes('个股分析')) {
		// 个股跟踪页：剥掉 YYYYMMDD- 前缀
		const stripped = post.id.replace(/^\d{8}-/, '');
		return `/${stripped}/`;
	}
	return `/${post.id}/`;
}
