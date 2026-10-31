import { argEntries, show } from "../lib/format";
import type { Case } from "../lib/types";

function argLines(args: unknown): { text: string; multiline: boolean } {
  const parts = argEntries(args).map(([k, v]) => {
    const s = show(v);
    const pad = " ".repeat(k.length + 3);
    return `${k} = ${s.split("\n").join("\n" + pad)}`;
  });
  const multiline = parts.some((p) => p.includes("\n"));
  return { text: parts.join(multiline ? ",\n" : ", "), multiline };
}

/** "Example 1, 2, …" built from the visible test cases, in LeetCode's grey example block. */
export function Examples({ cases }: { cases: Case[] }) {
  const visible = cases.filter((c) => !c.hidden);
  return (
    <div data-testid="examples">
      {visible.map((c, i) => {
        const input = argLines(c.args);
        const out = show(c.expected);
        return (
          <div key={i}>
            <p className="mb-3 mt-4 text-[14px] font-semibold text-strong">Example {i + 1}:</p>
            <div className="example">
              <b>Input:</b>
              {input.multiline ? "\n" : " "}
              {input.text}
              {"\n"}
              <b>Output:</b>
              {out.includes("\n") ? "\n" : " "}
              {out}
              {c.explanation ? (
                <>
                  {"\n"}
                  <b>Explanation:</b> <span className="font-sans">{c.explanation}</span>
                </>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
