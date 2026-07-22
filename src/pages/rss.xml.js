import { getCollection } from 'astro:content';
import rss from '@astrojs/rss';
import { SITE_DESCRIPTION, SITE_TITLE } from '../consts';
import { getPostUrl } from '../utils/postUrl';

export async function GET(context) {
	const posts = (await getCollection('blog'))
		.filter((post) => !post.data.serenityArchive)
		.sort((a, b) => (b.data.updatedDate ?? b.data.pubDate).valueOf() - (a.data.updatedDate ?? a.data.pubDate).valueOf());
	return rss({
		title: SITE_TITLE,
		description: SITE_DESCRIPTION,
		site: context.site,
		items: posts.map((post) => {
			let marketTag = '[全站]';
			if (post.data.tags?.includes('个股分析')) marketTag = '[A股]';
			else if (post.data.tags?.includes('美股分析')) marketTag = '[美股]';
			else if (post.data.tags?.includes('港股分析')) marketTag = '[港股]';
			else if (post.data.tags?.includes('白发股神')) marketTag = '[Serenity]';
			return {
				...post.data,
				title: `${marketTag} ${post.data.title}`,
				link: getPostUrl(post),
			};
		}),
	});
}
