import Link from 'next/link'

export function convertSourceReferences(text: string): React.ReactNode {
  // Pattern: [source_insight:id], [note:id], [source:id], [source_embedding:id]
  const pattern = /\[((?:source_insight|note|source|source_embedding):[\w\d]+)\]/g

  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let match

  while ((match = pattern.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index))
    }

    // Add link
    const ref = match[1]
    parts.push(
      <Link key={match.index} href={`/?object_id=${ref}`} className="text-primary hover:underline">
        [{ref}]
      </Link>
    )

    lastIndex = pattern.lastIndex
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex))
  }

  return parts.length > 0 ? parts : text
}
