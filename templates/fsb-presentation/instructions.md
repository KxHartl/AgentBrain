# AI Agent Instructions for FSB Presentation

You are generating a LaTeX Beamer presentation for academic purposes.
- **ALWAYS** output by modifying the corresponding `.tex` file in `docs/` directory.
- **DO NOT** output Markdown in the chat unless specifically requested. Use LaTeX for formatting the presentation.

## Structure

- Use `\begin{frame}{Naslov Slajda}` ... `\end{frame}` for each slide.
- Use `\section{...}` outside of frames to organize the Table of Contents.
- Use standard `itemize` and `enumerate` for lists.
- For math formulas, use `$ ... $` for inline and `\[ ... \]` for block equations.
- Replace `{{SADRZAJ}}` with the actual frames.
