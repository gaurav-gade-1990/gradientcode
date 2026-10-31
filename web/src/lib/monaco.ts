// Monaco is bundled locally (no CDN): the editor API, its standard contributions, Python highlighting, and the editor worker.
import * as monaco from "monaco-editor/esm/vs/editor/editor.api";
import "monaco-editor/esm/vs/editor/editor.all";
import "monaco-editor/esm/vs/basic-languages/python/python.contribution";
import EditorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import { loader } from "@monaco-editor/react";

(self as unknown as { MonacoEnvironment: unknown }).MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
};

monaco.editor.defineTheme("gc-dark", {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "comment", foreground: "7f848e", fontStyle: "italic" },
    { token: "keyword", foreground: "c678dd" },
    { token: "string", foreground: "98c379" },
    { token: "number", foreground: "d19a66" },
  ],
  colors: {
    "editor.background": "#262626",
    "editor.lineHighlightBackground": "#ffffff0a",
    "editor.lineHighlightBorder": "#00000000",
    "editorLineNumber.foreground": "#6e6e6e",
    "editorLineNumber.activeForeground": "#c7c7c7",
    "editorGutter.background": "#262626",
    "editorIndentGuide.background1": "#ffffff14",
    "scrollbarSlider.background": "#ffffff1f",
    "editorWidget.background": "#303030",
  },
});

monaco.editor.defineTheme("gc-light", {
  base: "vs",
  inherit: true,
  rules: [],
  colors: {
    "editor.background": "#ffffff",
    "editor.lineHighlightBackground": "#0000000a",
    "editor.lineHighlightBorder": "#00000000",
    "editorLineNumber.foreground": "#b0b0b0",
  },
});

loader.config({ monaco });

export { monaco };
