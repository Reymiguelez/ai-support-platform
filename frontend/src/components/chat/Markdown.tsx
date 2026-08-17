'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { cn } from '@/utils/helpers';

interface MarkdownProps {
  children: string;
  className?: string;
}

function isStringChildren(children: React.ReactNode): children is string {
  return typeof children === 'string';
}

export function Markdown({ children, className }: MarkdownProps) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={{
        p: ({ children, ...props }) => (
          <p {...props} className={cn('my-2', props.className)}>{children}</p>
        ),
        code: ({ children, ...props }) => {
          const isInline = (props.className?.includes('inline') ?? false) || (isStringChildren(children) && !children.includes('\n'));
          if (isInline) {
            return <code className={cn('px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-primary-600 dark:text-primary-400 font-mono text-sm', props.className)}>{children}</code>;
          }
          return (
            <pre className={cn('p-3 rounded-lg bg-neutral-900 dark:bg-neutral-950 overflow-x-auto text-sm my-2', props.className)}>
              <code className="font-mono text-neutral-100">{children}</code>
            </pre>
          );
        },
        strong: ({ children, ...props }) => (
          <strong {...props} className={cn('font-semibold', props.className)}>{children}</strong>
        ),
        em: ({ children, ...props }) => (
          <em {...props} className={cn('italic', props.className)}>{children}</em>
        ),
        ul: ({ children, ...props }) => (
          <ul {...props} className={cn('list-disc list-inside my-2 space-y-1', props.className)}>{children}</ul>
        ),
        ol: ({ children, ...props }) => (
          <ol {...props} className={cn('list-decimal list-inside my-2 space-y-1', props.className)}>{children}</ol>
        ),
        li: ({ children, ...props }) => (
          <li {...props} className={cn('ml-4', props.className)}>{children}</li>
        ),
        blockquote: ({ children, ...props }) => (
          <blockquote {...props} className={cn('border-l-4 border-primary-500 pl-4 italic text-neutral-600 dark:text-neutral-400 my-2', props.className)}>{children}</blockquote>
        ),
        h1: ({ children, ...props }) => (
          <h1 {...props} className={cn('text-2xl font-bold mt-4 mb-2', props.className)}>{children}</h1>
        ),
        h2: ({ children, ...props }) => (
          <h2 {...props} className={cn('text-xl font-bold mt-4 mb-2', props.className)}>{children}</h2>
        ),
        h3: ({ children, ...props }) => (
          <h3 {...props} className={cn('text-lg font-bold mt-3 mb-1', props.className)}>{children}</h3>
        ),
        a: ({ children, href, ...props }) => (
          <a href={href} {...props} className={cn('text-primary-600 dark:text-primary-400 underline hover:no-underline', props.className)} target="_blank" rel="noopener noreferrer">{children}</a>
        ),
        hr: ({ ...props }) => (
          <hr {...props} className={cn('my-4 border-neutral-200 dark:border-neutral-800', props.className)} />
        ),
        table: ({ children, ...props }) => (
          <div className={cn('overflow-x-auto my-4', props.className)}>
            <table className="min-w-full divide-y divide-neutral-200 dark:divide-neutral-800">{children}</table>
          </div>
        ),
        thead: ({ children, ...props }) => (
          <thead {...props} className="bg-neutral-100 dark:bg-neutral-800">{children}</thead>
        ),
        th: ({ children, ...props }) => (
          <th {...props} className="px-3 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">{children}</th>
        ),
        tbody: ({ children, ...props }) => (
          <tbody {...props} className="bg-white dark:bg-neutral-900 divide-y divide-neutral-200 dark:divide-neutral-800">{children}</tbody>
        ),
        td: ({ children, ...props }) => (
          <td {...props} className="px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100">{children}</td>
        ),
      }}
      className={className}
    >
      {children}
    </ReactMarkdown>
  );
}