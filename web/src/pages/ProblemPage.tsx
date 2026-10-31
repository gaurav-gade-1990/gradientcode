import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import { Panel, PanelGroup } from "react-resizable-panels";
import { CodeEditor } from "../components/CodeEditor";
import { ResultPane, TestcasePane, type CustomCase, type RanResult } from "../components/Console";
import { Examples } from "../components/Examples";
import {
  IconBook,
  IconBulb,
  IconCheck,
  IconChevronDown,
  IconCode,
  IconDoc,
  IconHistory,
  IconMaximize,
  IconMinimize,
  IconPlay,
  IconReset,
  IconSpinner,
  IconSquareCheck,
  IconTerminal,
  IconUpload,
} from "../components/Icons";
import { Markdown } from "../components/Markdown";
import { Gutter, PanelTabs, TopBar } from "../components/WorkspaceChrome";
import { DesignWorkspace } from "../components/DesignWorkspace";
import { DifficultyPill, Pill, diffText, relTime } from "../components/ui";
import { loadProblem } from "../lib/data";
import { argsToPython } from "../lib/format";
import { useIndex, useProgress } from "../lib/hooks";
import { judgeClient, useEngineState } from "../lib/judge";
import { addSubmission, clearDraft, getDraft, getSubs, setDraft } from "../lib/storage";
import { isDesign, type DesignProblem, type Problem, type ProblemIndex, type Submission } from "../lib/types";

type LeftTab = "description" | "editorial" | "hints" | "submissions";

export default function ProblemPage() {
  const { slug = "" } = useParams();
  const { index } = useIndex();
  const [problem, setProblem] = useState<Problem | DesignProblem | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    // Start Pyodide as soon as a code problem opens (design problems have no judge).
    if (problem && !isDesign(problem)) judgeClient.ensure().catch(() => {});
  }, [problem]);

  useEffect(() => {
    let live = true;
    setProblem(null);
    setError("");
    loadProblem(slug)
      .then((p) => live && setProblem(p))
      .catch((e) => live && setError(String(e.message ?? e)));
    return () => {
      live = false;
    };
  }, [slug]);

  return (
    <div className="flex h-full flex-col bg-page">
      {problem && isDesign(problem) ? (
        <DesignWorkspace key={slug} problem={problem} index={index} />
      ) : problem ? (
        <Workspace key={slug} problem={problem} index={index} />
      ) : (
        <>
          <TopBar index={index} slug={slug} center={null} />
          <div className="flex flex-1 items-center justify-center text-[14px] text-muted">{error ? <span className="text-gc-red">{error}</span> : "Loading…"}</div>
        </>
      )}
    </div>
  );
}

function Workspace({ problem, index }: { problem: Problem; index: ProblemIndex | null }) {
  const { meta } = problem;
  const slug = meta.slug;
  const engine = useEngineState();
  const { solved } = useProgress();
  const [code, setCode] = useState(() => getDraft(slug) ?? problem.starter);
  const [leftTab, setLeftTab] = useState<LeftTab>("description");
  const [consoleTab, setConsoleTab] = useState<"testcase" | "result">("testcase");
  const visible = useMemo(() => problem.cases.filter((c) => !c.hidden), [problem]);
  const [custom, setCustom] = useState<CustomCase[]>([]);
  const [selCase, setSelCase] = useState(0);
  const [running, setRunning] = useState<"run" | "submit" | null>(null);
  const [ran, setRan] = useState<RanResult | null>(null);
  const [subs, setSubs] = useState<Submission[]>(() => getSubs(slug));
  const [full, setFull] = useState(false);
  const nextId = useRef(1);

  // Debounced draft save.
  useEffect(() => {
    const t = setTimeout(() => {
      if (code === problem.starter) clearDraft(slug);
      else setDraft(slug, code);
    }, 400);
    return () => clearTimeout(t);
  }, [code, slug, problem.starter]);

  const busy = running !== null || engine !== "ready";

  const execute = useCallback(
    async (mode: "run" | "submit") => {
      if (running) return;
      setRunning(mode);
      setConsoleTab("result");
      const customNow = mode === "run" ? custom : [];
      const limit = meta.time_limit_ms ?? 5000;
      const n = mode === "submit" ? problem.cases.length : visible.length + customNow.length;
      const result = await judgeClient.judge(
        problem,
        code.replace(/\r\n?/g, "\n"),
        mode,
        customNow.map((c) => c.src),
      );
      setRan({ mode, result, visible, custom: customNow, budgetMs: Math.max(8000, n * limit), seq: Date.now() });
      setRunning(null);
      if (mode === "submit" && !result.internalError) {
        addSubmission(slug, { status: result.status, runtime_ms: result.runtime_ms, passed: result.passed, total: result.total, code });
        setSubs(getSubs(slug));
      }
    },
    [running, custom, problem, code, visible, slug, meta.time_limit_ms],
  );

  const run = useCallback(() => {
    if (!busy) execute("run");
  }, [busy, execute]);
  const submit = useCallback(() => {
    if (!busy) execute("submit");
  }, [busy, execute]);

  // LeetCode shortcuts outside the editor (inside it, Monaco commands handle them).
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.defaultPrevented) return;
      if ((e.target as HTMLElement | null)?.closest?.(".monaco-editor")) return;
      if (e.key === "'") {
        e.preventDefault();
        run();
      } else if (e.key === "Enter") {
        e.preventDefault();
        submit();
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [run, submit]);

  useEffect(() => {
    if (!full) return;
    const h = (e: KeyboardEvent) => e.key === "Escape" && setFull(false);
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [full]);

  const addCase = () => {
    const total = visible.length + custom.length;
    const sel = Math.min(selCase, total - 1);
    const src = sel >= visible.length ? custom[sel - visible.length].src : visible[sel] ? argsToPython(visible[sel].args) : "";
    setCustom((c) => [...c, { id: nextId.current++, src }]);
    setSelCase(total);
    setConsoleTab("testcase");
  };

  const loading = engine !== "ready";
  const center = (
    <>
      <button
        type="button"
        onClick={run}
        disabled={busy}
        data-testid="run"
        title="Run (Ctrl/Cmd + ')"
        className="flex h-8 items-center gap-1.5 rounded-l-lg bg-fill3 px-3 text-[14px] font-medium text-label hover:bg-fill2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading || running === "run" ? <IconSpinner size={14} /> : <IconPlay size={14} />}
        {loading ? <span data-testid="loading-python">{engine === "error" ? "Python failed" : "Loading Python…"}</span> : "Run"}
      </button>
      <button
        type="button"
        onClick={submit}
        disabled={busy}
        data-testid="submit"
        title="Submit (Ctrl/Cmd + Enter)"
        className="flex h-8 items-center gap-1.5 rounded-r-lg bg-gc-green px-3 text-[14px] font-medium text-white hover:bg-gc-green-hover disabled:cursor-not-allowed disabled:opacity-60"
      >
        {running === "submit" ? <IconSpinner size={14} /> : <IconUpload size={14} />}
        Submit
      </button>
    </>
  );

  const builtSlugs = new Map((index?.problems ?? []).map((p) => [p.slug, p]));
  const related = (meta.related ?? []).map((s) => builtSlugs.get(s)).filter((p): p is NonNullable<typeof p> => !!p);
  const isSolved = !!solved[slug];

  const left = (
    <div className="flex h-full flex-col overflow-hidden rounded-lg bg-layer1">
      <PanelTabs<LeftTab>
        value={leftTab}
        onChange={setLeftTab}
        tabs={[
          { key: "description", label: "Description", icon: <IconDoc size={15} className="text-gc-blue" /> },
          { key: "editorial", label: "Editorial", icon: <IconBook size={15} className="text-accent" /> },
          { key: "hints", label: "Hints", icon: <IconBulb size={15} className="text-medium" /> },
          { key: "submissions", label: "Submissions", icon: <IconHistory size={15} className="text-gc-blue" /> },
        ]}
      />
      <div className="min-h-0 flex-1 overflow-y-auto">
        {leftTab === "description" && (
          <div className="px-5 pb-8 pt-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <h1 className="text-[24px] font-semibold leading-8 text-strong" data-testid="problem-title">
                {meta.id}. {meta.title}
              </h1>
              {isSolved && (
                <span className="mt-1.5 flex shrink-0 items-center gap-1 text-[13px] text-gc-green">
                  Solved <IconCheck size={14} />
                </span>
              )}
            </div>
            <div className="mb-5 flex flex-wrap gap-2">
              <DifficultyPill d={meta.difficulty} />
              {meta.tags.map((t) => (
                <Pill key={t}>{t}</Pill>
              ))}
            </div>
            <Markdown>{problem.description}</Markdown>
            <Examples cases={problem.cases} />
            {related.length > 0 && (
              <div className="mt-6 border-t border-divider pt-4">
                <div className="mb-2 text-[14px] font-medium text-strong">Related</div>
                <ul className="flex flex-col gap-1.5">
                  {related.map((p) => (
                    <li key={p.slug} className="flex items-center justify-between text-[14px]">
                      <Link to={`/problems/${p.slug}`} className="text-label hover:text-gc-blue">
                        {p.id}. {p.title}
                      </Link>
                      <span className={`text-[12px] ${diffText[p.difficulty]}`}>{p.difficulty}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {leftTab === "editorial" && (
          <div className="px-5 pb-8 pt-4">
            <h2 className="mb-4 text-[20px] font-semibold text-strong">Editorial</h2>
            {problem.editorial ? <Markdown>{problem.editorial}</Markdown> : <p className="text-muted">No editorial yet.</p>}
          </div>
        )}
        {leftTab === "hints" && <Hints hints={meta.hints ?? []} />}
        {leftTab === "submissions" && (
          <SubmissionsList
            subs={subs}
            onLoad={(s) => {
              setCode(s.code);
            }}
          />
        )}
      </div>
    </div>
  );

  const editorPanel = (
    <div className={full ? "fixed inset-0 z-50 flex flex-col bg-page p-2" : "h-full"}>
      <div className="flex h-full flex-col overflow-hidden rounded-lg bg-layer1">
        <PanelTabs tabs={[{ key: "code", label: "Code", icon: <IconCode size={15} className="text-gc-green" /> }]} value="code" onChange={() => {}} />
        <div className="flex h-8 shrink-0 items-center border-b border-divider px-3">
          <span className="flex items-center gap-1 text-[13px] text-label" data-testid="language">
            Python3 (NumPy)
            <IconChevronDown size={12} className="text-muted" />
          </span>
          <div className="ml-auto flex items-center gap-0.5">
            <button
              type="button"
              title="Reset to starter code"
              data-testid="reset-code"
              onClick={() => {
                if (code === problem.starter || window.confirm("Reset the editor to the starter code? Your current code will be lost.")) setCode(problem.starter);
              }}
              className="flex h-6 w-6 items-center justify-center rounded text-muted hover:bg-fill3 hover:text-strong"
            >
              <IconReset size={14} />
            </button>
            <button
              type="button"
              title={full ? "Exit full screen" : "Full screen"}
              data-testid="fullscreen"
              onClick={() => setFull((f) => !f)}
              className="flex h-6 w-6 items-center justify-center rounded text-muted hover:bg-fill3 hover:text-strong"
            >
              {full ? <IconMinimize size={14} /> : <IconMaximize size={14} />}
            </button>
          </div>
        </div>
        <div className="min-h-0 flex-1" data-testid="editor">
          <CodeEditor value={code} onChange={setCode} onRun={run} onSubmit={submit} />
        </div>
      </div>
    </div>
  );

  const consolePanel = (
    <div className="flex h-full flex-col overflow-hidden rounded-lg bg-layer1">
      <PanelTabs<"testcase" | "result">
        value={consoleTab}
        onChange={setConsoleTab}
        tabs={[
          { key: "testcase", label: "Testcase", icon: <IconSquareCheck size={15} className="text-gc-green" /> },
          { key: "result", label: "Test Result", icon: <IconTerminal size={15} className="text-gc-green" /> },
        ]}
      />
      <div className="min-h-0 flex-1 overflow-y-auto" data-testid="console">
        {consoleTab === "testcase" ? (
          <TestcasePane
            visible={visible}
            custom={custom}
            selected={selCase}
            onSelect={setSelCase}
            onAdd={addCase}
            onEdit={(id, src) => setCustom((cs) => cs.map((c) => (c.id === id ? { ...c, src } : c)))}
            onRemove={(id) => {
              setCustom((cs) => cs.filter((c) => c.id !== id));
              setSelCase(0);
            }}
          />
        ) : (
          <ResultPane key={ran ? String(ran.seq) : "none"} ran={ran} running={running} />
        )}
      </div>
    </div>
  );

  return (
    <>
      <TopBar index={index} slug={slug} center={center} />
      <div className="min-h-0 flex-1 px-2 pb-2">
        <PanelGroup direction="horizontal" autoSaveId="gc:layout:h">
          <Panel defaultSize={45} minSize={20}>
            {left}
          </Panel>
          <Gutter />
          <Panel defaultSize={55} minSize={25}>
            <PanelGroup direction="vertical" autoSaveId="gc:layout:v">
              <Panel defaultSize={62} minSize={15}>
                {editorPanel}
              </Panel>
              <Gutter />
              <Panel defaultSize={38} minSize={10}>
                {consolePanel}
              </Panel>
            </PanelGroup>
          </Panel>
        </PanelGroup>
      </div>
    </>
  );
}

function Hints({ hints }: { hints: string[] }) {
  const [open, setOpen] = useState<Set<number>>(new Set());
  if (!hints.length) return <p className="px-5 py-4 text-muted">No hints for this problem.</p>;
  return (
    <div className="px-5 pb-8 pt-4">
      <h2 className="mb-4 text-[20px] font-semibold text-strong">Hints</h2>
      <div className="border-t border-divider">
        {hints.map((h, i) => {
          const on = open.has(i);
          return (
            <div key={i} className="border-b border-divider">
              <button
                type="button"
                data-testid={`hint-${i + 1}`}
                onClick={() =>
                  setOpen((s) => {
                    const n = new Set(s);
                    if (n.has(i)) n.delete(i);
                    else n.add(i);
                    return n;
                  })
                }
                className="flex w-full items-center gap-2 py-3 text-left text-[14px] text-strong"
              >
                <IconBulb size={15} className="text-muted" />
                Hint {i + 1}
                <IconChevronDown size={15} className={`ml-auto text-muted transition-transform ${on ? "rotate-180" : ""}`} />
              </button>
              {on && (
                <div className="pb-4 pl-6">
                  <Markdown>{h}</Markdown>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SubmissionsList({ subs, onLoad }: { subs: Submission[]; onLoad: (s: Submission) => void }) {
  if (!subs.length) {
    return <div className="flex h-full flex-col items-center justify-center py-16 text-[14px] text-muted">No submissions yet</div>;
  }
  return (
    <div className="px-2 py-2" data-testid="submissions">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="text-left text-[12px] text-muted">
            <th className="px-3 py-2 font-normal">Status</th>
            <th className="px-3 py-2 font-normal">Runtime</th>
            <th className="px-3 py-2 font-normal">Submitted</th>
          </tr>
        </thead>
        <tbody>
          {subs.map((s, i) => (
            <tr key={s.id} onClick={() => onLoad(s)} title="Load this code into the editor" className={`cursor-pointer ${i % 2 === 0 ? "bg-fill4" : ""} hover:bg-fill3`} data-testid="submission-row">
              <td className="px-3 py-2.5">
                <div className={`font-medium ${s.status === "Accepted" ? "text-gc-green" : "text-gc-red"}`}>{s.status}</div>
                <div className="text-[12px] text-muted">
                  {s.passed}/{s.total} passed
                </div>
              </td>
              <td className="px-3 py-2.5 text-label">{Math.round(s.runtime_ms)} ms</td>
              <td className="px-3 py-2.5 text-label" title={new Date(s.time).toLocaleString()}>
                {relTime(s.time)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
