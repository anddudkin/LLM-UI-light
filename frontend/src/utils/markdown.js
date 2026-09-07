import MarkdownIt from "markdown-it";
import texmath from "markdown-it-texmath";
import katex from "katex";
import DOMPurify from "dompurify";

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
});

md.use(texmath, {
  engine: katex,
  delimiters: ["dollars", "brackets"],
  katexOptions: { throwOnError: false, output: "html" },
});

md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
  tokens[idx].attrSet("target", "_blank");
  tokens[idx].attrSet("rel", "noopener noreferrer");
  return self.renderToken(tokens, idx, options);
};

export function renderMarkdown(text) {
  if (!text) return "";
  const html = md.render(text);
  return DOMPurify.sanitize(html, { ADD_ATTR: ["target"] });
}
