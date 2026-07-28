import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

// Renders answer/feedback markdown (bold, headers, lists, tables) safely — no raw
// HTML. remark-breaks preserves the single-line breaks carried over from the source
// HTML conversion. `[Sketch]`/`[Graph]` text markers pass through as plain text.
export default function Markdown({ children, className = "markdown" }) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          img: ({ node, ...props }) => (
            <img {...props} loading="lazy" decoding="async" />
          ),
        }}
      >
        {children || ""}
      </ReactMarkdown>
    </div>
  );
}
