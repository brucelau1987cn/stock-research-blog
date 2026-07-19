import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
	// Load Markdown and MDX files in the `src/content/blog/` directory.
	loader: glob({ base: './src/content/blog', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: ({ image }) =>
		z.object({
			title: z.string(),
			description: z.string(),
			// Transform string to Date object
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date().optional(),
			heroImage: z.optional(image()),
			image: z.string().optional(),
			tags: z.array(z.string()).optional().default([]),
			serenityArchive: z.boolean().optional().default(false),
			decision: z.object({
				ticker: z.string(),
				name: z.string(),
				status: z.string(),
				currentPrice: z.number().positive(),
				previousClose: z.number().positive().optional(),
				changePct: z.number().optional(),
				currency: z.string(),
				asOf: z.string(),
				market: z.enum(['CN', 'US', 'HK']),
				sessionDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'sessionDate must use YYYY-MM-DD'),
				dataAsOf: z.string().datetime({ offset: true }),
				resistance: z.object({ label: z.string(), value: z.number().positive(), state: z.string() }),
				support: z.object({ label: z.string(), value: z.number().positive(), state: z.string() }),
				invalidation: z.object({ label: z.string(), value: z.number().positive(), action: z.string() }),
				action: z.string(),
				changeSummary: z.array(z.string()).max(4).optional().default([]),
			}).optional(),
			usMarket: z.object({
				asOf: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'asOf must use YYYY-MM-DD'),
				period: z.string().min(1).optional(),
				source: z.string().min(1),
				earnings: z.object({
					date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'earnings date must use YYYY-MM-DD').optional(),
					status: z.string().min(1),
				}).optional(),
				valuation: z.array(z.object({ label: z.string(), value: z.string() })).max(4).optional().default([]),
				macro: z.array(z.string()).max(3).optional().default([]),
				peers: z.array(z.object({ ticker: z.string(), name: z.string() })).max(4).optional().default([]),
			}).optional(),
		}),
});

export const collections = { blog };
