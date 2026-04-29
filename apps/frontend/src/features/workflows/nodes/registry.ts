import type { NodeRegistryEntry, NodeTypeDefinition } from "./types";

// --- Explicit imports: each node exports { definition, NodeComponent, PanelComponent } ---
import {
  definition as startDef,
  NodeComponent as StartNode,
  PanelComponent as StartPanel,
} from "./start";
import {
  definition as endDef,
  NodeComponent as EndNode,
  PanelComponent as EndPanel,
} from "./end";
import {
  definition as llmDef,
  NodeComponent as LLMNode,
  PanelComponent as LLMPanel,
} from "./llm";
import {
  definition as toolDef,
  NodeComponent as ToolNode,
  PanelComponent as ToolPanel,
} from "./tool";
import {
  definition as conditionDef,
  NodeComponent as ConditionNode,
  PanelComponent as ConditionPanel,
} from "./condition";
import {
  definition as humanInputDef,
  NodeComponent as HumanInputNode,
  PanelComponent as HumanInputPanel,
} from "./human-input";
import {
  definition as knowledgeDef,
  NodeComponent as KnowledgeNode,
  PanelComponent as KnowledgePanel,
} from "./knowledge-retrieval";
import {
  definition as codeDef,
  NodeComponent as CodeNode,
  PanelComponent as CodePanel,
} from "./code";
import {
  definition as agentDef,
  NodeComponent as AgentNode,
  PanelComponent as AgentPanel,
} from "./agent";
import {
  definition as httpRequestDef,
  NodeComponent as HttpRequestNode,
  PanelComponent as HttpRequestPanel,
} from "./http-request";
import {
  definition as mergeDef,
  NodeComponent as MergeNode,
  PanelComponent as MergePanel,
} from "./merge";
import {
  definition as delayDef,
  NodeComponent as DelayNode,
  PanelComponent as DelayPanel,
} from "./delay";
import {
  definition as templateDef,
  NodeComponent as TemplateNode,
  PanelComponent as TemplatePanel,
} from "./template";
import {
  definition as switchDef,
  NodeComponent as SwitchNode,
  PanelComponent as SwitchPanel,
} from "./switch";
import {
  definition as loopDef,
  NodeComponent as LoopNode,
  PanelComponent as LoopPanel,
} from "./loop";
import {
  definition as filterDef,
  NodeComponent as FilterNode,
  PanelComponent as FilterPanel,
} from "./filter";
import {
  definition as setVariableDef,
  NodeComponent as SetVariableNode,
  PanelComponent as SetVariablePanel,
} from "./set-variable";
import {
  definition as webhookTriggerDef,
  NodeComponent as WebhookTriggerNode,
  PanelComponent as WebhookTriggerPanel,
} from "./webhook-trigger";
import {
  definition as noteDef,
  NodeComponent as NoteNode,
  PanelComponent as NotePanel,
} from "./note";

// --- Registry: add new nodes here (1 import + 1 line) ---
const REGISTRY: NodeRegistryEntry[] = [
  // Triggers
  { definition: webhookTriggerDef, node: WebhookTriggerNode, panel: WebhookTriggerPanel },
  // AI
  { definition: llmDef, node: LLMNode, panel: LLMPanel },
  { definition: agentDef, node: AgentNode, panel: AgentPanel },
  // Integration
  { definition: toolDef, node: ToolNode, panel: ToolPanel },
  { definition: httpRequestDef, node: HttpRequestNode, panel: HttpRequestPanel },
  // Data
  { definition: codeDef, node: CodeNode, panel: CodePanel },
  { definition: knowledgeDef, node: KnowledgeNode, panel: KnowledgePanel },
  { definition: templateDef, node: TemplateNode, panel: TemplatePanel },
  { definition: setVariableDef, node: SetVariableNode, panel: SetVariablePanel },
  // Logic
  { definition: conditionDef, node: ConditionNode, panel: ConditionPanel },
  { definition: switchDef, node: SwitchNode, panel: SwitchPanel },
  { definition: filterDef, node: FilterNode, panel: FilterPanel },
  { definition: mergeDef, node: MergeNode, panel: MergePanel },
  { definition: loopDef, node: LoopNode, panel: LoopPanel },
  { definition: delayDef, node: DelayNode, panel: DelayPanel },
  // Core
  { definition: startDef, node: StartNode, panel: StartPanel },
  { definition: endDef, node: EndNode, panel: EndPanel },
  { definition: humanInputDef, node: HumanInputNode, panel: HumanInputPanel },
  { definition: noteDef, node: NoteNode, panel: NotePanel },
];

// --- Lookup map (computed once) ---
const byType = new Map(REGISTRY.map((e) => [e.definition.type, e]));

// --- Public API ---

export function getNodeEntry(type: string): NodeRegistryEntry | undefined {
  return byType.get(type);
}

export function getAllDefinitions(): NodeTypeDefinition[] {
  return REGISTRY.map((e) => e.definition);
}

export function getDefinitionsByCategory(
  category: string
): NodeTypeDefinition[] {
  return REGISTRY.filter((e) => e.definition.category === category).map(
    (e) => e.definition
  );
}
