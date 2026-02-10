import ReactMarkdown from "react-markdown";
import type { Report } from "../types";

const FRIENDLY_NAMES: Record<string, string> = {
  data_collector: "Data Collector",
  data_analyst: "Data Analyst",
  trade_executor: "Trade Executor",
  risk_manager: "Risk Manager",
};

const AGENT_COLORS: Record<string, string> = {
  data_collector: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  data_analyst: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  trade_executor: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  risk_manager: "bg-amber-500/15 text-amber-400 border-amber-500/30",
};

function formatTimestamp(filename: string): string {
  // filename is like "2026-02-08_11-38-00.md"
  const base = filename.replace(".md", "");
  const [datePart, timePart] = base.split("_");
  if (!timePart) return base;
  return `${datePart} ${timePart.replace(/-/g, ":")}`;
}

function extractSummary(content: string): string {
  const summaryMatch = content.match(/## Summary\s*\n([\s\S]*?)(?=\n##|$)/);
  if (!summaryMatch) return "";

  const summaryText = summaryMatch[1].trim();
  const maxLength = 150;

  if (summaryText.length > maxLength) {
    return summaryText.slice(0, maxLength).trim() + "...";
  }

  return summaryText;
}

interface ReportViewerProps {
  reports: Report[];
}

export default function ReportViewer({ reports }: ReportViewerProps) {
  return (
    <div className="flex min-h-0 h-full flex-col rounded-xl border border-gray-700/50 bg-gray-800/50 overflow-hidden">
      <div className="border-b border-gray-700/50 px-5 py-3">
        <h2 className="text-sm font-semibold text-gray-300">Reports</h2>
      </div>
      {reports.length === 0 ? (
        <div className="flex flex-1 items-center justify-center p-8">
          <p className="text-sm text-gray-500">No reports yet</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto">
          <div className="flex flex-col gap-3 p-4">
            {reports.map((report) => (
              <details
                key={`${report.agent}-${report.filename}`}
                className="group rounded-lg border border-gray-700/30 bg-gray-900/40"
              >
                <summary className="flex cursor-pointer items-center gap-3 px-4 py-3 text-sm select-none">
                  <span
                    className={`rounded-md border px-2 py-0.5 text-xs font-medium ${AGENT_COLORS[report.agent] ?? "bg-gray-500/15 text-gray-400 border-gray-500/30"}`}
                  >
                    {FRIENDLY_NAMES[report.agent] ?? report.agent}
                  </span>
                  <span className="text-xs tabular-nums text-gray-500">
                    {formatTimestamp(report.filename)}
                  </span>
                  {report.content && extractSummary(report.content) && (
                    <span className="text-xs text-gray-400 truncate flex-1 ml-2">
                      {extractSummary(report.content)}
                    </span>
                  )}
                </summary>
                {report.content && (
                  <div className="border-t border-gray-700/30 px-4 py-3">
                    <article className="prose prose-invert prose-sm max-w-none prose-headings:text-gray-200 prose-p:text-gray-300 prose-strong:text-gray-200 prose-code:rounded prose-code:bg-gray-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:text-gray-300 prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-700">
                      <ReactMarkdown>{report.content}</ReactMarkdown>
                    </article>
                  </div>
                )}
              </details>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
