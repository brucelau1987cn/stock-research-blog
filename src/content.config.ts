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
			decision: z.object({
				ticker: z.string(),
				name: z.string(),
				status: z.string(),
				currentPrice: z.number().positive(),
				previousClose: z.number().positive().optional(),
				changePct: z.number().optional(),
				currency: z.string(),
				asOf: z.string(),
				resistance: z.object({ label: z.string(), value: z.number().positive(), state: z.string() }),
				support: z.object({ label: z.string(), value: z.number().positive(), state: z.string() }),
				invalidation: z.object({ label: z.string(), value: z.number().positive(), action: z.string() }),
				action: z.string(),
				changeSummary: z.array(z.string()).max(4).optional().default([]),
			}).optional(),
		}),
});

export const collections = { blog };
