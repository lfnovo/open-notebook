export type BuiltinTemplate = {
  id: string;
  name: string;
  description: string | null;
  body_md: string;
};

type FrontMatter = {
  id?: string;
  name?: string;
  description?: string;
};

const rawTemplates = import.meta.glob('../../../report-formats/*.md', {
  as: 'raw',
  eager: true,
});

const FRONT_MATTER_DELIMITER = /^---\s*$/m;

const parseFrontMatter = (content: string): { data: FrontMatter; body: string } => {
  const lines = content.split('\n');
  if (lines.length === 0 || !FRONT_MATTER_DELIMITER.test(lines[0])) {
    return { data: {}, body: content };
  }

  let closingIndex = -1;
  for (let i = 1; i < lines.length; i += 1) {
    if (FRONT_MATTER_DELIMITER.test(lines[i])) {
      closingIndex = i;
      break;
    }
  }

  if (closingIndex === -1) {
    return { data: {}, body: content };
  }

  const data: FrontMatter = {};
  const frontMatterLines = lines.slice(1, closingIndex);
  frontMatterLines.forEach((line) => {
    if (!line.trim()) return;
    const colonIndex = line.indexOf(':');
    if (colonIndex === -1) return;
    const key = line.slice(0, colonIndex).trim();
    let value = line.slice(colonIndex + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!key) return;
    if (key === 'id') data.id = value;
    else if (key === 'name') data.name = value;
    else if (key === 'description') data.description = value;
  });

  const body = lines.slice(closingIndex + 1).join('\n').trimStart();
  return { data, body };
};

const deriveIdFromPath = (path: string) => {
  const match = path.match(/\/([^/]+)\.md$/);
  if (!match) return undefined;
  return `builtin:${match[1].replace(/\s+/g, '-').toLowerCase()}`;
};

const builtinTemplates: BuiltinTemplate[] = Object.entries(rawTemplates)
  .map(([path, content]) => {
    const { data, body } = parseFrontMatter(content as string);
    const id = data.id ?? deriveIdFromPath(path);
    const name = data.name ?? id ?? 'Built-in Template';

    if (!id) {
      throw new Error(`Built-in report template "${path}" is missing an id in its front matter.`);
    }

    return {
      id,
      name,
      description: data.description ?? null,
      body_md: body.trim(),
    };
  })
  .sort((a, b) => a.name.localeCompare(b.name));

export default builtinTemplates;
