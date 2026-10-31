import { useState, type ReactNode } from "react";
import { argEntries, show } from "../lib/format";
import type { Case, CaseResult, JudgeResult } from "../lib/types";
import { IconCheck, IconPlus, IconSpinner, IconX } from "./Icons";

export interface CustomCase {
  id: number;
  src: string;
}

export interface RanResult {
  mode: "run" | "submit";
  result: JudgeResult;
  visible: Case[];
  custom: CustomCase[];
  budgetMs?: number;
  seq?: number;
}

function Block({ label, children, tone = "normal", testId }: { label: string; children: ReactNode; tone?: "normal" | "error"; testId?: string }) {
  return (
    <div className="mb-3">
      <div className="mb-1.5 text-[12px] font-medium text-muted">{label}</div>
      <pre
        data-testid={testId}
        className={`overflow-x-auto whitespace-pre-wrap break-words rounded-lg px-3 py-2.5 font-mono text-[13px] leading-5 ${
          tone === "error" ? "bg-err text-gc-red" : "bg-fill3 text-strong"
        }`}
      >
        {children}
      </pre>
    </div>
  );
}

function ArgBoxes({ args }: { args: unknown }) {
  return (
    <>
      {argEntries(args).map(([k, v]) => (
        <Block key={k} label={`${k} =`}>
          {show(v)}
        </Block>
      ))}
    </>
  );
}

function CasePill({ active, onClick, children, testId, onRemove }: { active: boolean; onClick: () => void; children: ReactNode; testId?: string; onRemove?: () => void }) {
  return (
    <div className="group relative">
      <button
        type="button"
        data-testid={testId}
        onClick={onClick}
        className={`flex h-8 items-center gap-1.5 rounded-lg px-3 text-[13px] ${active ? "bg-fill2 font-medium text-strong" : "text-muted hover:bg-fill3 hover:text-label"}`}
      >
        {children}
      </button>
      {onRemove && (
        <button
          type="button"
          aria-label="Remove case"
          onClick={onRemove}
          className="absolute -right-1 -top-1 hidden h-4 w-4 items-center justify-center rounded-full bg-fill1 text-label group-hover:flex"
        >
          <IconX size={10} />
        </button>
      )}
    </div>
  );
}

export function TestcasePane({
  visible,
  custom,
  selected,
  onSelect,
  onAdd,
  onEdit,
  onRemove,
}: {
  visible: Case[];
  custom: CustomCase[];
  selected: number;
  onSelect: (i: number) => void;
  onAdd: () => void;
  onEdit: (id: number, src: string) => void;
  onRemove: (id: number) => void;
}) {
  const total = visible.length + custom.length;
  const sel = Math.min(selected, total - 1);
  const cust = sel >= visible.length ? custom[sel - visible.length] : null;
  return (
    <div className="px-4 py-3">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {visible.map((_, i) => (
          <CasePill key={`v${i}`} active={sel === i} onClick={() => onSelect(i)} testId={`case-pill-${i}`}>
            Case {i + 1}
          </CasePill>
        ))}
        {custom.map((c, j) => (
          <CasePill key={c.id} active={sel === visible.length + j} onClick={() => onSelect(visible.length + j)} onRemove={() => onRemove(c.id)} testId={`case-pill-${visible.length + j}`}>
            Case {visible.length + j + 1}
          </CasePill>
        ))}
        <button type="button" onClick={onAdd} title="Add a custom testcase" data-testid="add-case" className="flex h-8 w-8 items-center justify-center rounded-lg text-muted hover:bg-fill3 hover:text-strong">
          <IconPlus size={16} />
        </button>
      </div>
      {cust ? (
        <div>
          <div className="mb-1.5 text-[12px] font-medium text-muted">Custom testcase: one Python assignment per argument (np is imported)</div>
          <textarea
            data-testid="custom-case-input"
            spellCheck={false}
            value={cust.src}
            onChange={(e) => onEdit(cust.id, e.target.value)}
            rows={Math.max(4, cust.src.split("\n").length + 1)}
            className="w-full resize-y rounded-lg border border-transparent bg-fill3 px-3 py-2.5 font-mono text-[13px] leading-5 text-strong outline-none focus:border-line"
          />
        </div>
      ) : visible[sel] ? (
        <ArgBoxes args={visible[sel].args} />
      ) : null}
    </div>
  );
}

function statusTone(s: string) {
  return s === "Accepted" || s === "Finished" ? "text-gc-green" : "text-gc-red";
}

function CaseDetail({ r, args }: { r: CaseResult; args?: unknown }) {
  return (
    <div>
      {r.error && (
        <Block label={r.status} tone="error" testId="result-error">
          {r.error}
        </Block>
      )}
      {args ? <ArgBoxes args={args} /> : r.input ? <Block label="Input">{r.input}</Block> : null}
      {r.stdout ? <Block label="Stdout" testId="result-stdout">{r.stdout}</Block> : null}
      {r.output !== undefined && (
        <Block label="Output" testId="result-output">
          {r.output}
        </Block>
      )}
      {r.expected !== undefined && <Block label="Expected">{r.expected}</Block>}
      {r.message && (
        <div className="mb-3 rounded-lg bg-err px-3 py-2 font-mono text-[12px] text-gc-red" data-testid="result-message">
          {r.message}
        </div>
      )}
    </div>
  );
}

export function ResultPane({ ran, running }: { ran: RanResult | null; running: "run" | "submit" | null }) {
  const [sel, setSel] = useState(0);
  if (running) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-[14px] text-muted" data-testid="judging">
        <IconSpinner size={16} />
        {running === "submit" ? "Judging…" : "Running…"}
      </div>
    );
  }
  if (!ran) {
    return <div className="flex h-full items-center justify-center text-[14px] text-muted">You must run your code first</div>;
  }
  const { result, mode, visible } = ran;
  const head = (
    <div className="mb-4 flex flex-wrap items-baseline gap-x-3 gap-y-1">
      <h3 className={`text-[20px] font-semibold ${statusTone(result.status)}`} data-testid="result-status">
        {result.status}
      </h3>
      {mode === "submit" && !result.internalError && (
        <span className="text-[13px] text-muted" data-testid="result-passed">
          {result.passed} / {result.total} testcases passed
        </span>
      )}
      {!result.internalError && <span className="text-[13px] text-muted">Runtime: {Math.round(result.runtime_ms)} ms</span>}
    </div>
  );

  if (result.internalError) {
    return (
      <div className="px-4 py-3">
        {head}
        <Block label="Error" tone="error" testId="result-error">
          {result.internalError}
        </Block>
      </div>
    );
  }
  if (!result.cases.length && result.status === "Time Limit Exceeded") {
    return (
      <div className="px-4 py-3">
        {head}
        <p className="text-[13px] text-label">Your code did not finish within {ran.budgetMs ?? result.runtime_ms} ms, so it was stopped. Look for an infinite loop or a slow Python-level loop.</p>
      </div>
    );
  }
  if (mode === "submit") {
    const fail = result.cases[0];
    return (
      <div className="px-4 py-3">
        {head}
        {result.status === "Accepted" ? (
          <div className="rounded-lg bg-fill3 px-4 py-3 text-[13px] text-label">
            All testcases passed. <span className="text-muted">Your submission was saved to the Submissions tab.</span>
          </div>
        ) : fail ? (
          <CaseDetail r={fail} />
        ) : null}
      </div>
    );
  }
  const s = Math.min(sel, result.cases.length - 1);
  const r = result.cases[s];
  return (
    <div className="px-4 py-3">
      {head}
      <div className="mb-3 flex flex-wrap gap-2">
        {result.cases.map((c, i) => {
          const ok = c.status === "Accepted" || c.status === "Finished";
          return (
            <CasePill key={i} active={s === i} onClick={() => setSel(i)} testId={`result-pill-${i}`}>
              {ok ? <IconCheck size={13} className="text-gc-green" /> : <IconX size={13} className="text-gc-red" />}
              Case {i + 1}
            </CasePill>
          );
        })}
      </div>
      {r && <CaseDetail r={r} args={s < visible.length ? visible[s].args : undefined} />}
    </div>
  );
}
