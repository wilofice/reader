# Repository Guidelines

## Project Structure & Module Organization

This directory currently contains one French Markdown guide, `J'ai besoin de reprendre le travail que j'ai comme.md`. It documents a macOS terminal workflow using Poppler’s `pdftotext` and `less` to extract and read documents. There are no source-code modules, test directories, or bundled assets. Keep related documentation in the root until additional organization is needed; do not introduce application scaffolding for documentation-only changes.

## Setup & Local Commands

There is no build system or development server. The guide documents these commands:

- `brew install poppler`: install the PDF extraction dependency on macOS.
- `pdftotext -v`: check that the extraction tool is available.
- `pdftotext -layout "document.pdf" "document.txt"`: extract text while retaining approximate layout.
- `less -N +120 "document.txt"`: read extracted text starting at line 120 with line numbers.

Use local sample files when checking examples. Quote filenames and paths, especially those containing spaces or apostrophes.

## Documentation Style & Naming Conventions

Preserve the existing guide’s French language and instructional tone. Use descriptive Markdown headings, short paragraphs, and fenced code blocks labeled with the appropriate shell language. Keep shell commands unindented inside code fences. Use consistent list indentation and verify that footnote references resolve. No formatter or linter is configured. Prefer short, descriptive names for new documents; avoid renaming the existing guide without updating references.

## Validation Guidelines

No automated test framework or coverage requirement exists. Preview Markdown changes and manually check affected commands when their dependencies are available. Verify extraction against a sample PDF and check line navigation interactively in `less`. Distinguish extracted-text line numbers from PDF page numbers. Clearly state when an example has not been executed.

## Commit & Pull Request Guidelines

This directory has no Git metadata, so no existing commit convention can be inferred. If version control is introduced, use concise, imperative messages such as `docs: clarify PDF extraction workflow`. Keep changes focused. Pull requests should explain the documentation change and list manual validation performed; include screenshots only when they clarify rendering issues.
