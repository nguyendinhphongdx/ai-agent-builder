import { SourceHandle } from "../../components/handles";
import type { NodeContentProps } from "../types";

interface CaseItem {
  id: string;
  label?: string;
}

export default function ConditionNode({ id, data }: NodeContentProps) {
  const cases: CaseItem[] = (data.config.cases as CaseItem[]) || [
    { id: "true", label: "True" },
    { id: "false", label: "False" },
  ];

  return (
    <div className="space-y-1">
      {cases.map((c, i) => (
        <div key={c.id} className="relative flex items-center justify-between pr-5">
          <span className="text-[10px] font-medium text-muted-foreground">
            {c.label || `Case ${i + 1}`}
          </span>
          <SourceHandle
            handleId={c.id}
            nodeId={id}
            label={c.label}

          />
        </div>
      ))}
      <div className="relative flex items-center justify-between pr-5">
        <span className="text-[10px] font-medium text-muted-foreground">ELSE</span>
        <SourceHandle
          handleId="else"
          nodeId={id}
          label="Else"
        />
      </div>
    </div>
  );
}
