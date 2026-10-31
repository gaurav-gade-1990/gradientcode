// A TypeScript mirror of harness.show(): Python-like reprs of values encoded by harness.encode().
// Arrays follow np.array2string(precision=4, suppress=True, threshold=60, edgeitems=3, linewidth=88, separator=", ").

const REPR_CAP = 1500;
const THRESHOLD = 60;
const EDGE = 3;
const LINEWIDTH = 88;

type Nd = { __nd__: true; dtype: string; shape: number[]; data: unknown[] };

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
export function isNd(v: unknown): v is Nd {
  return isObj(v) && v.__nd__ === true;
}

/** Python's "%.6g". */
export function pyG(x: number, prec = 6): string {
  if (Number.isNaN(x)) return "nan";
  if (!Number.isFinite(x)) return x > 0 ? "inf" : "-inf";
  if (x === 0) return Object.is(x, -0) ? "-0" : "0";
  const [mant, expStr] = x.toExponential(prec - 1).split("e");
  const e = parseInt(expStr, 10);
  if (e < -4 || e >= prec) {
    const m = mant.includes(".") ? mant.replace(/0+$/, "").replace(/\.$/, "") : mant;
    const sign = e < 0 ? "-" : "+";
    return `${m}e${sign}${String(Math.abs(e)).padStart(2, "0")}`;
  }
  const s = x.toFixed(Math.max(0, prec - 1 - e));
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

export function pyStr(s: string): string {
  const q = s.includes("'") && !s.includes('"') ? '"' : "'";
  let out = "";
  for (const ch of s) {
    if (ch === "\\") out += "\\\\";
    else if (ch === "\n") out += "\\n";
    else if (ch === "\t") out += "\\t";
    else if (ch === "\r") out += "\\r";
    else if (ch === q) out += "\\" + q;
    else out += ch;
  }
  return q + out + q;
}

function specialFloat(v: unknown): number | null {
  if (isObj(v) && typeof v.__float__ === "string") {
    const s = v.__float__;
    return s === "nan" ? NaN : s === "inf" ? Infinity : -Infinity;
  }
  return null;
}

function elemNumber(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "boolean") return v ? 1 : 0;
  const s = specialFloat(v);
  return s === null ? NaN : s;
}

/** Element formatter for the displayed subset of an array, padded like NumPy does. */
function makeElementFormatter(dtype: string, shown: unknown[]): (v: unknown) => string {
  const kind = dtype.replace(/^[<>|=]/, "")[0];
  if (dtype === "bool") {
    const w = shown.some((v) => v === false) ? 5 : 4;
    return (v) => (v ? "True" : "False").padStart(w);
  }
  if (kind === "U" || kind === "S" || dtype.startsWith("str")) {
    return (v) => pyStr(String(v));
  }
  if (dtype.startsWith("float") || kind === "f") {
    const parts = shown.map((v) => {
      const x = elemNumber(v);
      if (!Number.isFinite(x)) return null;
      let s = Math.abs(x).toFixed(4).replace(/0+$/, "");
      if (x < 0 || Object.is(x, -0)) s = "-" + s;
      const [i, f] = s.split(".");
      return [i, f ?? ""] as [string, string];
    });
    const finite = parts.filter((p): p is [string, string] => p !== null);
    const padL = Math.max(1, ...finite.map((p) => p[0].length));
    const padR = Math.max(0, ...finite.map((p) => p[1].length));
    return (v) => {
      const x = elemNumber(v);
      if (!Number.isFinite(x)) {
        const s = Number.isNaN(x) ? "nan" : x > 0 ? "inf" : "-inf";
        return s.padStart(padL + padR + 1);
      }
      let s = Math.abs(x).toFixed(4).replace(/0+$/, "");
      if (x < 0 || Object.is(x, -0)) s = "-" + s;
      const [i, f = ""] = s.split(".");
      return i.padStart(padL) + "." + f.padEnd(padR);
    };
  }
  const w = Math.max(1, ...shown.map((v) => String(v).length));
  return (v) => String(v).padStart(w);
}

function strides(shape: number[]): number[] {
  const st = new Array(shape.length).fill(1);
  for (let i = shape.length - 2; i >= 0; i--) st[i] = st[i + 1] * shape[i + 1];
  return st;
}

function axisIndices(len: number, summarize: boolean): (number | null)[] {
  if (!summarize || len <= 2 * EDGE) return Array.from({ length: len }, (_, i) => i);
  return [0, 1, 2, null, len - 3, len - 2, len - 1];
}

export function array2string(nd: Nd): string {
  const { shape, data, dtype } = nd;
  const size = shape.reduce((a, b) => a * b, 1);
  if (shape.length === 0) return makeElementFormatter(dtype, data)(data[0]);
  if (size === 0) return "[]".padStart(shape.length * 2, "[").padEnd(shape.length * 2, "]");
  const summarize = size > THRESHOLD;
  const st = strides(shape);
  const shown: unknown[] = [];
  const collect = (depth: number, offset: number) => {
    if (depth === shape.length) {
      shown.push(data[offset]);
      return;
    }
    for (const i of axisIndices(shape[depth], summarize)) if (i !== null) collect(depth + 1, offset + i * st[depth]);
  };
  collect(0, 0);
  const fmtEl = makeElementFormatter(dtype, shown);
  const nd_ = shape.length;

  const rec = (depth: number, offset: number): string => {
    const idx = axisIndices(shape[depth], summarize);
    const indent = " ".repeat(depth + 1);
    if (depth === nd_ - 1) {
      const words = idx.map((i) => (i === null ? "..." : fmtEl(data[offset + i * st[depth]])));
      const lines: string[] = [];
      let line = "[";
      words.forEach((w, k) => {
        const part = k < words.length - 1 ? w + "," : w;
        if (k === 0) {
          line += part;
          return;
        }
        if (line.length + 1 + part.length + (k === words.length - 1 ? 1 : 0) > LINEWIDTH - depth) {
          lines.push(line);
          line = indent + part;
        } else line += " " + part;
      });
      lines.push(line + "]");
      return lines.join("\n");
    }
    const sep = ",\n" + "\n".repeat(Math.max(0, nd_ - depth - 2)) + indent;
    const kids = idx.map((i) => (i === null ? "..." : rec(depth + 1, offset + i * st[depth])));
    return "[" + kids.join(sep) + "]";
  };
  return rec(0, 0);
}

function showInner(v: unknown): string {
  if (v === null || v === undefined) return "None";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : pyG(v);
  if (typeof v === "string") return pyStr(v);
  if (Array.isArray(v)) return "[" + v.map(showInner).join(", ") + "]";
  if (isNd(v)) return array2string(v);
  if (isObj(v)) {
    const sf = specialFloat(v);
    if (sf !== null) return pyG(sf);
    if (Array.isArray(v.__tuple__)) {
      const items = v.__tuple__.map(showInner);
      return "(" + items.join(", ") + (items.length === 1 ? ",)" : ")");
    }
    if (Array.isArray(v.__dict__)) {
      return "{" + (v.__dict__ as [unknown, unknown][]).map(([k, x]) => `${showInner(k)}: ${showInner(x)}`).join(", ") + "}";
    }
  }
  return String(v);
}

/** Mirror of harness.show. */
export function show(v: unknown): string {
  const s = showInner(v);
  return s.length <= REPR_CAP ? s : s.slice(0, REPR_CAP) + " ...";
}

// ------------------------------------------------------------ Python source for custom testcases

function pyFloatLit(x: number): string {
  if (Number.isNaN(x)) return "float('nan')";
  if (!Number.isFinite(x)) return x > 0 ? "float('inf')" : "float('-inf')";
  const s = String(x);
  return /[.e]/.test(s) ? s : s + ".0";
}

function nested(nd: Nd, lit: (v: unknown) => string): string {
  const st = strides(nd.shape);
  const rec = (depth: number, offset: number): string => {
    if (depth === nd.shape.length) return lit(nd.data[offset]);
    const parts: string[] = [];
    for (let i = 0; i < nd.shape[depth]; i++) parts.push(rec(depth + 1, offset + i * st[depth]));
    return "[" + parts.join(", ") + "]";
  };
  return rec(0, 0);
}

/** Python source that rebuilds an encoded value (used to prefill custom testcases). */
export function toPython(v: unknown): string {
  if (v === null || v === undefined) return "None";
  if (typeof v === "boolean") return v ? "True" : "False";
  if (typeof v === "number") return String(v);
  if (typeof v === "string") return pyStr(v);
  if (Array.isArray(v)) return "[" + v.map(toPython).join(", ") + "]";
  if (isNd(v)) {
    const isFloat = v.dtype.startsWith("float");
    const lit = isFloat ? (x: unknown) => pyFloatLit(elemNumber(x)) : v.dtype === "bool" ? (x: unknown) => (x ? "True" : "False") : (x: unknown) => toPython(x);
    const dt = v.dtype === "bool" ? "bool" : /^[a-z]+\d*$/.test(v.dtype) ? "np." + v.dtype : JSON.stringify(v.dtype);
    const size = v.shape.reduce((a, b) => a * b, 1);
    if (size === 0) return `np.zeros(${toPython({ __tuple__: v.shape })}, dtype=${dt})`;
    const body = v.shape.length === 0 ? lit(v.data[0]) : nested(v, lit);
    return v.dtype === "float64" ? `np.array(${body})` : `np.array(${body}, dtype=${dt})`;
  }
  if (isObj(v)) {
    const sf = specialFloat(v);
    if (sf !== null) return pyFloatLit(sf);
    if (Array.isArray(v.__tuple__)) {
      const items = v.__tuple__.map(toPython);
      return "(" + items.join(", ") + (items.length === 1 ? ",)" : ")");
    }
    if (Array.isArray(v.__dict__)) {
      return "{" + (v.__dict__ as [unknown, unknown][]).map(([k, x]) => `${toPython(k)}: ${toPython(x)}`).join(", ") + "}";
    }
  }
  return "None";
}

/** A case's args are an encoded dict ({__dict__: [[name, value], ...]}); return them as [name, value] pairs. */
export function argEntries(args: unknown): [string, unknown][] {
  if (isObj(args) && Array.isArray(args.__dict__)) return (args.__dict__ as [unknown, unknown][]).map(([k, v]) => [String(k), v]);
  if (isObj(args)) return Object.entries(args);
  return [];
}

export function argsToPython(args: unknown): string {
  return argEntries(args)
    .map(([k, v]) => `${k} = ${toPython(v)}`)
    .join("\n");
}
