/**
 * Core types for the MCP Agent System
 */

export interface Tool {
  name: string;
  description: string;
  server: string;
  parameters?: Record<string, any>;
  categories?: Set<string>;
  keywords?: Set<string>;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ToolCall {
  name: string;
  input: Record<string, any>;
}

export interface ChatResponse {
  content: string;
  toolCalls: ToolCall[];
  filteredToolsCount: number;
  filteredTools: string[];
  usedFiltering: boolean;
}

export interface ChatWithToolsResponse extends ChatResponse {
  initialResponse?: string;
  toolResults?: ToolResult[];
}

export interface ToolResult {
  tool: string;
  result?: string;
  error?: string;
}

export interface MCPConfig {
  mcpServers: {
    [key: string]: {
      url: string;
      headers?: Record<string, string>;
    };
  };
}

export interface ObserveeConfig {
  url: string;
  authToken: string | null;
}

export interface AgentConfig {
  provider?: string | LLMProvider;
  serverName?: string;
  model?: string;
  serverUrl?: string;
  syncTools?: boolean;
  filterType?: string;
  enableFiltering?: boolean;
  authToken?: string;
  [key: string]: any; // provider-specific kwargs
}

export interface LLMProvider {
  generate(params: {
    messages: Message[];
    tools?: any[];
    mcpConfig?: any;
    maxTokens?: number;
    temperature?: number;
  }): Promise<LLMResponse>;
  setMcpClient?(mcpClient: any): void;
}

export interface LLMResponse {
  content: string;
  toolCalls?: any[];
}

// Streaming types
export interface StreamChunk {
  type: 'content' | 'tool_call' | 'metadata' | 'phase' | 'tool_result' | 'tool_error' | 'final_content' | 'done';
  content?: string;
  toolCall?: ToolCall;
  toolName?: string;
  result?: string;
  error?: string;
  phase?: string;
  filteredToolsCount?: number;
  filteredTools?: string[];
  usedFiltering?: boolean;
  toolCalls?: ToolCall[];
  final_response?: ChatWithToolsResponse;
}