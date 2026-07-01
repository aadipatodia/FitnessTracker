type Block =
  | { type: 'paragraph'; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }

function preprocessMarkdown(text: string): string {
  return text
    .replace(/\r\n/g, '\n')
    .replace(/\s+\*\s+(?=\*\*)/g, '\n- ')
    .replace(/^\*\s+/gm, '- ')
    .replace(/\s+\*$/gm, '')
    .trim()
}

function parseBlocks(text: string): Block[] {
  const lines = preprocessMarkdown(text).split('\n')
  const blocks: Block[] = []
  let currentList: { ordered: boolean; items: string[] } | null = null
  let paragraphLines: string[] = []

  const flushParagraph = () => {
    const joined = paragraphLines.join(' ').trim()
    if (joined) blocks.push({ type: 'paragraph', text: joined })
    paragraphLines = []
  }

  const flushList = () => {
    if (currentList?.items.length) {
      blocks.push({ type: 'list', ordered: currentList.ordered, items: currentList.items })
    }
    currentList = null
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      flushParagraph()
      flushList()
      continue
    }

    const numbered = trimmed.match(/^\d+\.\s+(.+)$/)
    const bulleted = trimmed.match(/^[-*•]\s+(.+)$/)

    if (numbered) {
      flushParagraph()
      if (!currentList?.ordered) {
        flushList()
        currentList = { ordered: true, items: [] }
      }
      currentList.items.push(numbered[1])
    } else if (bulleted) {
      flushParagraph()
      if (currentList?.ordered) {
        flushList()
        currentList = { ordered: false, items: [] }
      }
      if (!currentList) currentList = { ordered: false, items: [] }
      currentList.items.push(bulleted[1])
    } else {
      flushList()
      paragraphLines.push(trimmed)
    }
  }

  flushParagraph()
  flushList()
  return blocks
}

function cleanInlineText(text: string): string {
  return text.replace(/^\*\s*/, '').replace(/\s*\*$/, '').trim()
}

function parseInline(text: string): React.ReactNode[] {
  const cleaned = cleanInlineText(text)
  const segments = cleaned.split(/(\*\*[^*]+\*\*)/g).filter((segment) => segment.length > 0)

  return segments
    .map((segment, i) => {
      if (segment.startsWith('**') && segment.endsWith('**')) {
        return (
          <strong key={i} className="font-semibold text-foreground">
            {segment.slice(2, -2)}
          </strong>
        )
      }

      const plain = segment.replace(/\*/g, '')
      if (!plain) return null
      return <span key={i}>{plain}</span>
    })
    .filter(Boolean) as React.ReactNode[]
}

export function FormattedText({ text, className = '' }: { text: string; className?: string }) {
  if (!text.trim()) return null

  const blocks = parseBlocks(text)

  return (
    <div className={`space-y-3 text-base leading-relaxed text-secondary-foreground ${className}`.trim()}>
      {blocks.map((block, i) => {
        if (block.type === 'paragraph') {
          return <p key={i}>{parseInline(block.text)}</p>
        }

        const ListTag = block.ordered ? 'ol' : 'ul'
        const listClass = block.ordered
          ? 'list-decimal space-y-2 pl-5 marker:text-accent'
          : 'list-disc space-y-2 pl-5 marker:text-accent'

        return (
          <ListTag key={i} className={listClass}>
            {block.items.map((item, j) => (
              <li key={j} className="pl-1">{parseInline(item)}</li>
            ))}
          </ListTag>
        )
      })}
    </div>
  )
}
