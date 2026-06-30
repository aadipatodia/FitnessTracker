type Block =
  | { type: 'paragraph'; text: string }
  | { type: 'list'; ordered: boolean; items: string[] }

function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n/g, '\n').split('\n')
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

function parseInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-medium text-foreground">
          {part.slice(2, -2)}
        </strong>
      )
    }
    return part
  })
}

export function FormattedText({ text, className = '' }: { text: string; className?: string }) {
  if (!text.trim()) return null

  const blocks = parseBlocks(text)

  return (
    <div className={`space-y-3 text-sm leading-relaxed text-muted-foreground ${className}`.trim()}>
      {blocks.map((block, i) => {
        if (block.type === 'paragraph') {
          return <p key={i}>{parseInline(block.text)}</p>
        }

        const ListTag = block.ordered ? 'ol' : 'ul'
        const listClass = block.ordered
          ? 'list-decimal space-y-1.5 pl-5'
          : 'list-disc space-y-1.5 pl-5'

        return (
          <ListTag key={i} className={listClass}>
            {block.items.map((item, j) => (
              <li key={j}>{parseInline(item)}</li>
            ))}
          </ListTag>
        )
      })}
    </div>
  )
}
