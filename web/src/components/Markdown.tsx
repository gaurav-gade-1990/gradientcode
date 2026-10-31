import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeHighlight from "rehype-highlight";

/** `prose`: dollar signs are money, not math (design prompts and answers). `$$...$$` display math still works. */
export function Markdown({ children, prose = false }: { children: string; prose?: boolean }) {
  return (
    <div className="md">
      <ReactMarkdown remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: !prose }]]} rehypePlugins={[[rehypeKatex, { throwOnError: false }], [rehypeHighlight, { detect: false, ignoreMissing: true }]]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
