
export interface ToolEvent {
  id: string;
  name: string;
  status: "running" | "completed" | "error";
  input?: Record<string, any>;
  result?: any;
  error?: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  thinking?: string;
  tools_used?: string[];
  tool_events?: ToolEvent[];
}
