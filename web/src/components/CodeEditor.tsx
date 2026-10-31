import Editor, { type OnMount } from "@monaco-editor/react";
import { useEffect, useRef } from "react";
import { monaco } from "../lib/monaco";
import { useTheme } from "../lib/hooks";

type Ed = Parameters<OnMount>[0];

declare global {
  interface Window {
    __gcEditor?: Ed;
  }
}

export function CodeEditor({
  value,
  onChange,
  onRun,
  onSubmit,
}: {
  value: string;
  onChange: (v: string) => void;
  onRun: () => void;
  onSubmit: () => void;
}) {
  const theme = useTheme();
  const handlers = useRef({ onRun, onSubmit });
  handlers.current = { onRun, onSubmit };
  const edRef = useRef<Ed | null>(null);

  // Keep the editor in sync when the value changes from outside (reset, loading a submission, switching problems).
  useEffect(() => {
    const ed = edRef.current;
    if (ed && ed.getValue() !== value) ed.setValue(value);
  }, [value]);

  return (
    <Editor
      language="python"
      theme={theme === "dark" ? "gc-dark" : "gc-light"}
      defaultValue={value}
      onChange={(v) => onChange(v ?? "")}
      loading={<div className="p-4 text-[13px] text-muted">Loading editor…</div>}
      onMount={(ed) => {
        edRef.current = ed;
        window.__gcEditor = ed;
        ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Quote, () => handlers.current.onRun());
        ed.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => handlers.current.onSubmit());
      }}
      options={{
        fontFamily: 'Menlo, "SF Mono", Monaco, Consolas, monospace',
        fontSize: 13,
        lineHeight: 20,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true,
        tabSize: 4,
        insertSpaces: true,
        renderLineHighlight: "all",
        padding: { top: 8 },
        scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
        overviewRulerLanes: 0,
        hideCursorInOverviewRuler: true,
        overviewRulerBorder: false,
        fixedOverflowWidgets: true,
        quickSuggestions: false,
        suggestOnTriggerCharacters: false,
        wordBasedSuggestions: "off",
      }}
    />
  );
}
