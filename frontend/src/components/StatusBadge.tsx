interface StatusBadgeProps {
  status: "idle" | "running" | "error";
  size?: "sm" | "md";
}

export default function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const sizeClass = size === "sm" ? "h-2 w-2" : "h-3 w-3";

  const colorMap = {
    idle: "bg-emerald-400",
    running: "bg-yellow-400 animate-pulse",
    error: "bg-red-500",
  };

  const labelMap = {
    idle: "Idle",
    running: "Running",
    error: "Error",
  };

  return (
    <span className="inline-flex items-center gap-1.5" title={labelMap[status]}>
      <span className={`inline-block rounded-full ${sizeClass} ${colorMap[status]}`} />
      {size === "md" && (
        <span
          className={`text-xs font-medium ${
            status === "idle"
              ? "text-emerald-400"
              : status === "running"
                ? "text-yellow-400"
                : "text-red-400"
          }`}
        >
          {labelMap[status]}
        </span>
      )}
    </span>
  );
}
