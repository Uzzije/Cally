import type { ChatContentBlock } from '../types'


export function MessageBlockRenderer({ block }: { block: ChatContentBlock }) {
  if (block.type === 'clarification') {
    return <p className="chat-block chat-block-clarification">{block.text}</p>
  }

  if (block.type === 'status') {
    return <p className="chat-block chat-block-status">{block.text}</p>
  }

  return <p className="chat-block">{block.text}</p>
}

