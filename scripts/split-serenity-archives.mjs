import fs from 'node:fs';
import path from 'node:path';
import GithubSlugger from 'github-slugger';

const CONTENT_DIR = path.resolve('src/content/blog');
const REDIRECT_PATH = path.resolve('public/serenity-archive-redirect.js');
const KEEP_RECENT = 30;
const ARCHIVE_SIZE = 25;
const MONTH_RE = /^20\d{4}\.md$/;
const ARCHIVE_RE = /^(20\d{4})-archive-(\d+)\.md$/;
const TWEET_RE = /^### Tweet(?:\s+\d+)?\s+·/gm;

function splitFrontmatter(text) {
  const match = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (!match) throw new Error('Missing frontmatter');
  return { frontmatter: match[1], body: text.slice(match[0].length) };
}

function splitTweetSections(body) {
  const matches = [...body.matchAll(TWEET_RE)];
  if (!matches.length) return { preamble: body.trimEnd(), sections: [] };
  return {
    preamble: body.slice(0, matches[0].index).trimEnd(),
    sections: matches.map((match, index) => {
      const start = match.index;
      const end = matches[index + 1]?.index ?? body.length;
      return body.slice(start, end).trim();
    }),
  };
}

function headingSlug(section) {
  const heading = section
    .split('\n', 1)[0]
    .replace(/^###\s+Tweet(?:\s+\d+)?\s+·\s*/, '')
    .trim();
  return new GithubSlugger().slug(heading);
}

function normalizeSection(section, number) {
  const lines = section.split('\n').map((line) => line.trimEnd());
  lines[0] = lines[0].replace(
    /^### Tweet(?:\s+\d+)?\s+·/,
    `### Tweet ${number} ·`,
  );
  return lines.join('\n').trim();
}

function frontmatterValue(frontmatter, key, fallback = '') {
  const match = frontmatter.match(new RegExp(`^${key}:\\s*['\"]?(.+?)['\"]?\\s*$`, 'm'));
  return match?.[1] ?? fallback;
}

function cleanPreamble(preamble) {
  return preamble.replace(/\n## 🗂 历史推文归档[\s\S]*$/, '').trimEnd();
}

function archiveNavigation(month, count) {
  if (!count) return '';
  const links = Array.from({ length: count }, (_, index) =>
    `- [归档 ${index + 1}](/${month}-archive-${index + 1}/)`
  ).join('\n');
  return `\n\n## 🗂 历史推文归档\n\n主页面保留最近 ${KEEP_RECENT} 条推文；较早内容已拆分以减少页面载荷。\n\n${links}`;
}

function archiveFrontmatter(month, index, sourceFrontmatter, sectionCount) {
  const monthLabel = `${month.slice(0, 4)}年${Number(month.slice(4))}月`;
  const updatedDate = frontmatterValue(sourceFrontmatter, 'updatedDate', `${month.slice(0, 4)}-${month.slice(4)}-01`);
  return `---\ntitle: '白发股神：${monthLabel}推文归档 ${index}'\ndescription: 'Serenity ${monthLabel}较早推文归档，第 ${index} 部分，共 ${sectionCount} 条。'\npubDate: ${month.slice(0, 4)}-${month.slice(4)}-01\nupdatedDate: ${updatedDate}\ntags: ['白发股神']\nserenityArchive: true\n---`;
}

const files = fs.readdirSync(CONTENT_DIR);
const months = files.filter((file) => MONTH_RE.test(file));
const archiveStarts = {};

for (const monthFile of months) {
  const month = monthFile.slice(0, -3);
  const mainPath = path.join(CONTENT_DIR, monthFile);
  const mainText = fs.readFileSync(mainPath, 'utf8');
  const { frontmatter, body } = splitFrontmatter(mainText);
  if (!frontmatter.includes('白发股神')) continue;

  const mainParts = splitTweetSections(body);
  const existingArchives = files
    .map((file) => ({ file, match: file.match(ARCHIVE_RE) }))
    .filter(({ match }) => match?.[1] === month)
    .sort((a, b) => Number(a.match[2]) - Number(b.match[2]));

  const existingSections = existingArchives.flatMap(({ file }) => {
    const archiveText = fs.readFileSync(path.join(CONTENT_DIR, file), 'utf8');
    return splitTweetSections(splitFrontmatter(archiveText).body).sections;
  });

  const allSections = [...mainParts.sections, ...existingSections];
  const seen = new Set();
  const uniqueSections = allSections.filter((section) => {
    const slug = headingSlug(section);
    if (!slug || seen.has(slug)) return false;
    seen.add(slug);
    return true;
  });

  const currentNumbers = uniqueSections.map((section) =>
    Number(section.match(/^### Tweet (\d+)\s+·/)?.[1])
  );
  const needsRenumber = currentNumbers.some(
    (number, index) => number !== index + 1
  );
  const numberedSections = needsRenumber
    ? uniqueSections.map((section, index) => normalizeSection(section, index + 1))
    : uniqueSections;
  const recent = numberedSections.slice(0, KEEP_RECENT);
  const older = numberedSections.slice(KEEP_RECENT);
  const chunks = Array.from({ length: Math.ceil(older.length / ARCHIVE_SIZE) }, (_, index) =>
    older.slice(index * ARCHIVE_SIZE, (index + 1) * ARCHIVE_SIZE)
  );

  const mainBody = `${cleanPreamble(mainParts.preamble)}${archiveNavigation(month, chunks.length)}\n\n${recent.join('\n\n')}\n`;
  fs.writeFileSync(mainPath, `---\n${frontmatter}\n---\n${mainBody}`);

  existingArchives.forEach(({ file }) => fs.unlinkSync(path.join(CONTENT_DIR, file)));
  chunks.forEach((chunk, index) => {
    const page = index + 1;
    const archiveBody = `\n\n[← 返回 ${month} 月度主页面](/${month}/)\n\n${chunk.join('\n\n')}\n`;
    fs.writeFileSync(
      path.join(CONTENT_DIR, `${month}-archive-${page}.md`),
      `${archiveFrontmatter(month, page, frontmatter, chunk.length)}${archiveBody}`,
    );
    const firstNumber = Number(chunk[0]?.match(/^### Tweet (\d+)\s+·/)?.[1]);
    if (Number.isFinite(firstNumber)) (archiveStarts[month] ??= []).push(firstNumber);
  });

  console.log(`${month}: ${uniqueSections.length} tweets -> ${recent.length} main + ${chunks.length} archive page(s)`);
}

fs.writeFileSync(
  REDIRECT_PATH,
  `(()=>{const m=location.pathname.match(/^\\/(20\\d{4})\\/$/),n=Number(decodeURIComponent(location.hash).match(/^#tweet-(\\d+)-/)?.[1]);if(!m||!n)return;const a=${JSON.stringify(archiveStarts)}[m[1]]||[];let p=0;for(let i=0;i<a.length;i++)if(n>=a[i])p=i+1;if(p)location.replace('/'+m[1]+'-archive-'+p+'/'+location.hash)})();\n`,
);
