import { getCollection } from 'astro:content';
import rss from '@astrojs/rss';
import { getPostUrl } from '../../utils/postUrl';

export async function GET(context) {
	const posts = (await getCollection('blog'))
		.filter((post) => !post.data.serenityArchive && post.data.tags?.includes('个股分析'))
		.sort((a, b) => (b.data.updatedDate ?? b.data.pubDate).valueOf() - (a.data.updatedDate ?? a.data.pubDate).valueOf());
	return rss({
		title: 'AI选股 - A股分析订阅',
		description: 'A股量价研判与交易执行日志：结论先行，动态跟踪多空边界与筹码演变。',
		site: context.site,
		items: posts.map((post) => ({
			...post.data,
			link: getPostUrl(post),
		})),
	});
}
