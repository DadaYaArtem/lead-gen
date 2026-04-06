import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders GPT reply text with markdown support.
 * Used in both LeadChatPanel and CasesPage chat bubbles.
 *
 * Applies prose-style Tailwind classes so headings, lists, code blocks,
 * bold/italic, and tables look clean inside the chat bubble.
 */
export function MarkdownMessage({ content, isUser = false }) {
  if (isUser) {
    // User messages are plain text — no markdown needed
    return <span className="whitespace-pre-wrap">{content}</span>;
  }

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Headings
        h1: ({ children }) => (
          <h1 className="text-base font-bold mt-3 mb-1 first:mt-0">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="text-sm font-bold mt-3 mb-1 first:mt-0">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="text-sm font-semibold mt-2 mb-0.5 first:mt-0">{children}</h3>
        ),
        // Paragraphs
        p: ({ children }) => (
          <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
        ),
        // Lists
        ul: ({ children }) => (
          <ul className="list-disc list-outside pl-4 mb-2 space-y-0.5">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal list-outside pl-4 mb-2 space-y-0.5">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        // Inline code
        code: ({ inline, children }) =>
          inline ? (
            <code className="bg-slate-200/70 text-slate-800 rounded px-1 py-0.5 text-[0.8em] font-mono">
              {children}
            </code>
          ) : (
            <code className="block bg-slate-100 text-slate-800 rounded-lg px-3 py-2 text-xs font-mono overflow-x-auto my-2 whitespace-pre">
              {children}
            </code>
          ),
        // Code block wrapper
        pre: ({ children }) => <>{children}</>,
        // Bold / italic
        strong: ({ children }) => (
          <strong className="font-semibold">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        // Horizontal rule
        hr: () => <hr className="border-slate-300 my-3" />,
        // Blockquote
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-slate-300 pl-3 text-slate-600 italic my-2">
            {children}
          </blockquote>
        ),
        // Tables (remark-gfm)
        table: ({ children }) => (
          <div className="overflow-x-auto my-2">
            <table className="text-xs border-collapse w-full">{children}</table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border border-slate-300 bg-slate-100 px-2 py-1 text-left font-semibold">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border border-slate-300 px-2 py-1">{children}</td>
        ),
        // Links
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#10b981] underline underline-offset-2 hover:text-[#0d9469]"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
