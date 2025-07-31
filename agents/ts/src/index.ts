/**
 * MCP Agent System - A TypeScript SDK for MCP tool integration with LLM providers
 */

import * as dotenv from 'dotenv';
import { MCPAgent } from './agents/agent.js';
import {
  AgentConfig,
  ChatWithToolsResponse,
  FilteredTool,
  ObserveeConfig,
  StreamChunk,
  ToolInfo
} from './types.js';

// Load environment variables
dotenv.config();

export const VERSION = '0.1.0';

/**
 * Get Observee configuration with priority: params > env vars
 */
function getObserveeConfig(
  observeeUrl?: string,
  observeeApiKey?: string,
  clientId?: string
): ObserveeConfig {
  // Get client_id with priority: param > env var
  if (!clientId) {
    clientId = process.env.OBSERVEE_CLIENT_ID;
  }

  function updateClientIdInUrl(url: string, newClientId: string): string {
    // If client_id already exists, replace it
    if (url.includes('client_id=')) {
      return url.replace(/client_id=[^&]*/, `client_id=${newClientId}`);
    } else if (newClientId) {
      // Add client_id to URL
      const separator = url.includes('?') ? '&' : '?';
      return `${url}${separator}client_id=${newClientId}`;
    }
    return url;
  }

  // Priority 1: Direct URL parameter
  if (observeeUrl) {
    const updatedUrl = clientId ? updateClientIdInUrl(observeeUrl, clientId) : observeeUrl;
    return {
      url: updatedUrl,
      authToken: null
    };
  }

  // Priority 2: API key parameter
  if (observeeApiKey) {
    if (!clientId) {
      throw new Error('client_id is required when using observee_api_key. Set OBSERVEE_CLIENT_ID env var or pass client_id parameter.');
    }
    return {
      url: `https://mcp.observee.ai/mcp?client_id=${clientId}`,
      authToken: observeeApiKey
    };
  }

  // Priority 3: Environment variables
  const envUrl = process.env.OBSERVEE_URL;
  if (envUrl) {
    const updatedUrl = clientId ? updateClientIdInUrl(envUrl, clientId) : envUrl;
    return {
      url: updatedUrl,
      authToken: null
    };
  }

  const envApiKey = process.env.OBSERVEE_API_KEY;
  if (envApiKey) {
    if (!clientId) {
      throw new Error('client_id is required when using OBSERVEE_API_KEY. Set OBSERVEE_CLIENT_ID env var or pass client_id parameter.');
    }
    return {
      url: `https://mcp.observee.ai/mcp?client_id=${clientId}`,
      authToken: envApiKey
    };
  }

  // No configuration provided
  throw new Error(
    'No Observee configuration found. Please provide one of:\n' +
    '1. observee_url parameter or OBSERVEE_URL env var\n' +
    '2. observee_api_key parameter or OBSERVEE_API_KEY env var (requires client_id)\n' +
    '3. Set environment variables in .env file'
  );
}

/**
 * Chat with tools using the MCP agent system
 * 
 * @param message - The user message/query
 * @param options - Configuration options
 * @returns Response with content, tool calls, and results
 * 
 * @example
 * ```typescript
 * import { chatWithTools } from '@observee/agents';
 * 
 * const result = await chatWithTools(
 *   "Search for recent news about AI",
 *   {
 *     provider: "anthropic",
 *     model: "claude-3-5-sonnet-20241022",
 *     observeeApiKey: "obs_your_key_here"
 *   }
 * );
 * console.log(result.content);
 * ```
 */
export async function chatWithTools(
  message: string,
  options: {
    provider?: string;
    model?: string;
    observeeUrl?: string;
    observeeApiKey?: string;
    clientId?: string;
    serverName?: string;
    maxTools?: number;
    minScore?: number;
    filterType?: string;
    enableFiltering?: boolean;
    syncTools?: boolean;
    [key: string]: any;
  } = {}
): Promise<ChatWithToolsResponse> {
  const {
    provider = 'anthropic',
    model,
    observeeUrl,
    observeeApiKey,
    clientId,
    serverName = 'observee',
    maxTools = 20,
    minScore = 8.0,
    filterType = 'bm25',
    enableFiltering = true,
    syncTools = false,
    ...providerKwargs
  } = options;

  // Get configuration
  const config = getObserveeConfig(observeeUrl, observeeApiKey, clientId);

  // Create agent config
  const agentConfig: AgentConfig = {
    provider,
    model,
    serverName: serverName,
    serverUrl: config.url,
    authToken: config.authToken || undefined,
    syncTools: syncTools,
    filterType: filterType,
    enableFiltering: enableFiltering,
    ...providerKwargs
  };

  // Create and initialize agent
  const agent = new MCPAgent(agentConfig);
  
  try {
    await agent.initialize();
    
    // Execute the chat with tools
    const result = await agent.chatWithTools(message, maxTools, minScore);
    
    return result;
  } finally {
    // Clean up
    await agent.close();
  }
}


/**
 * Chat with tools using the MCP agent system
 * 
 * @param message - The user message/query
 * @param options - Configuration options
 * @returns Response with content, tool calls, and results
 * 
 * @example
 * ```typescript
 * import { chatWithTools } from '@observee/agents';
 * 
 * const result = await chatWithTools(
 *   "Search for recent news about AI",
 *   {
 *     provider: "anthropic",
 *     model: "claude-3-5-sonnet-20241022",
 *     observeeApiKey: "obs_your_key_here"
 *   }
 * );
 * console.log(result.content);
 * ```
 */
export async function chatWithToolsStreaming(
  message: string,
  options: {
    provider?: string;
    model?: string;
    observeeUrl?: string;
    observeeApiKey?: string;
    clientId?: string;
    serverName?: string;
    maxTools?: number;
    minScore?: number;
    filterType?: string;
    enableFiltering?: boolean;
    syncTools?: boolean;
    [key: string]: any;
  } = {}
): Promise<ChatWithToolsResponse> {
  const {
    provider = 'anthropic',
    model,
    observeeUrl,
    observeeApiKey,
    clientId,
    serverName = 'observee',
    maxTools = 20,
    minScore = 8.0,
    filterType = 'bm25',
    enableFiltering = true,
    syncTools = false,
    ...providerKwargs
  } = options;

  // Get configuration
  const config = getObserveeConfig(observeeUrl, observeeApiKey, clientId);

  // Create agent config
  const agentConfig: AgentConfig = {
    provider,
    model,
    serverName: serverName,
    serverUrl: config.url,
    authToken: config.authToken || undefined,
    syncTools: syncTools,
    filterType: filterType,
    enableFiltering: enableFiltering,
    ...providerKwargs
  };

  // Create and initialize agent
  const agent = new MCPAgent(agentConfig);
  
  try {
    await agent.initialize();
    
    // Execute the chat with tools
    const result = await agent.chatWithToolsStreaming(message, maxTools, minScore);
    
    return result;
  } finally {
    // Clean up
    await agent.close();
  }
}

/**
 * Chat with tools using streaming - high-level function
 * 
 * @param message - The user message/query
 * @param options - Configuration options
 * @returns AsyncGenerator that yields StreamChunk objects
 * 
 * @example
 * ```typescript
 * import { chatWithToolsStream } from '@observee/agents';
 * 
 * for await (const chunk of chatWithToolsStream("Search for AI news", {
 *   provider: "anthropic",
 *   observeeApiKey: "your-api-key"
 * })) {
 *   if (chunk.type === "content") {
 *     process.stdout.write(chunk.content || "");
 *   } else if (chunk.type === "tool_result") {
 *     console.log(`\nTool executed: ${chunk.tool_name}`);
 *   }
 * }
 * ```
 */
export async function* chatWithToolsStream(
  message: string,
  options: {
    provider?: string;
    model?: string;
    observeeUrl?: string;
    observeeApiKey?: string;
    clientId?: string;
    serverName?: string;
    maxTools?: number;
    minScore?: number;
    filterType?: string;
    enableFiltering?: boolean;
    syncTools?: boolean;
    [key: string]: any;
  } = {}
): AsyncGenerator<StreamChunk, void, unknown> {
  const {
    provider = 'anthropic',
    model,
    observeeUrl,
    observeeApiKey,
    clientId,
    serverName = 'observee',
    maxTools = 20,
    minScore = 8.0,
    filterType = 'bm25',
    enableFiltering = true,
    syncTools = false,
    ...providerKwargs
  } = options;

  // Get configuration
  const config = getObserveeConfig(observeeUrl, observeeApiKey, clientId);

  // Create agent config
  const agentConfig: AgentConfig = {
    provider,
    model,
    serverName: serverName,
    serverUrl: config.url,
    authToken: config.authToken || undefined,
    syncTools: syncTools,
    filterType: filterType,
    enableFiltering: enableFiltering,
    ...providerKwargs
  };

  // Create and initialize agent
  const agent = new MCPAgent(agentConfig);
  
  try {
    await agent.initialize();
    
    // Stream the chat with tools
    for await (const chunk of agent.chatWithToolsStream(message, maxTools, minScore)) {
      yield chunk;
    }
  } finally {
    // Clean up
    await agent.close();
  }
}

/**
 * List all available tools from the MCP server
 * 
 * @param options - Configuration options
 * @returns Array of tools with name, description, and input schema
 * 
 * @example
 * ```typescript
 * import { listTools } from '@observee/agents';
 * 
 * const tools = await listTools({
 *   observeeApiKey: "obs_your_key_here"
 * });
 * console.log(`Found ${tools.length} tools`);
 * for (const tool of tools.slice(0, 5)) {
 *   console.log(`- ${tool.name}: ${tool.description}`);
 * }
 * ```
 */
export async function listTools(options: {
  observeeUrl?: string;
  observeeApiKey?: string;
  clientId?: string;
  serverName?: string;
} = {}): Promise<ToolInfo[]> {
  const {
    observeeUrl,
    observeeApiKey,
    clientId,
    serverName = 'observee'
  } = options;

  // Get configuration
  const config = getObserveeConfig(observeeUrl, observeeApiKey, clientId);

  // Create agent with minimal configuration for tool listing
  const agentConfig: AgentConfig = {
    provider: 'anthropic',
    serverName: serverName,
    serverUrl: config.url,
    authToken: config.authToken || undefined,
    syncTools: false,
    enableFiltering: false
  };

  // Create and initialize agent
  const agent = new MCPAgent(agentConfig);
  
  try {
    await agent.initialize();
    
    // Get tools using the agent's MCP client
    const mcpTools = await agent.getMcpClient().listTools();
    
    // Convert MCP tools to ToolInfo format
    const tools: ToolInfo[] = mcpTools.map(tool => ({
      name: tool.name,
      description: tool.description || '',
      input_schema: tool.inputSchema || {}
    }));
    
    return tools;
  } finally {
    // Clean up
    await agent.close();
  }
}

/**
 * Filter tools based on a query to find the most relevant ones
 * 
 * @param query - Search query to filter tools
 * @param options - Configuration options
 * @returns Array of filtered tools with relevance scores
 * 
 * @example
 * ```typescript
 * import { filterTools } from '@observee/agents';
 * 
 * const tools = await filterTools(
 *   "search YouTube videos",
 *   {
 *     maxTools: 5,
 *     observeeApiKey: "obs_your_key_here"
 *   }
 * );
 * for (const tool of tools) {
 *   console.log(`- ${tool.name} (score: ${tool.relevance_score})`);
 * }
 * ```
 */
export async function filterTools(
  query: string,
  options: {
    maxTools?: number;
    minScore?: number;
    filterType?: string;
    observeeUrl?: string;
    observeeApiKey?: string;
    clientId?: string;
    serverName?: string;
  } = {}
): Promise<FilteredTool[]> {
  const {
    maxTools = 10,
    minScore = 8.0,
    filterType = 'bm25',
    observeeUrl,
    observeeApiKey,
    clientId,
    serverName = 'observee'
  } = options;

  // Get configuration
  const config = getObserveeConfig(observeeUrl, observeeApiKey, clientId);

  // Create agent with filtering enabled
  const agentConfig: AgentConfig = {
    provider: 'anthropic',
    serverName: serverName,
    serverUrl: config.url,
    authToken: config.authToken || undefined,
    syncTools: false,
    filterType: filterType,
    enableFiltering: true
  };

  // Create and initialize agent
  const agent = new MCPAgent(agentConfig);
  
  try {
    await agent.initialize();
    
    // Filter tools using the agent's tool filter
    const toolFilter = agent.getToolFilter();
    if (!toolFilter) {
      throw new Error('Tool filter not available. This should not happen when filtering is enabled.');
    }
    const filteredTools = await toolFilter.filterTools(query, maxTools, minScore);
    
    // Convert to FilteredTool format with relevance scores
    const tools: FilteredTool[] = filteredTools.map(tool => ({
      name: tool.name,
      description: tool.description || '',
      input_schema: tool.parameters || {},
      relevance_score: (tool as any).score || 0.0
    }));
    
    return tools;
  } finally {
    // Clean up
    await agent.close();
  }
}

/**
 * Execute a specific tool with given input parameters
 * 
 * @param toolName - Name of the tool to execute
 * @param toolInput - Input parameters for the tool
 * @param options - Configuration options
 * @returns Tool execution result
 * 
 * @example
 * ```typescript
 * import { executeTool } from '@observee/agents';
 * 
 * const result = await executeTool(
 *   "youtube_get_transcript",
 *   { video_url: "https://youtube.com/watch?v=..." },
 *   { observeeApiKey: "obs_your_key_here" }
 * );
 * console.log(result);
 * ```
 */
export async function executeTool(
  toolName: string,
  toolInput: Record<string, any>,
  options: {
    observeeUrl?: string;
    observeeApiKey?: string;
    clientId?: string;
    serverName?: string;
  } = {}
): Promise<any> {
  const {
    observeeUrl,
    observeeApiKey,
    clientId,
    serverName = 'observee'
  } = options;

  // Get configuration
  const config = getObserveeConfig(observeeUrl, observeeApiKey, clientId);

  // Create agent with minimal configuration for tool execution
  const agentConfig: AgentConfig = {
    provider: 'anthropic',
    serverName: serverName,
    serverUrl: config.url,
    authToken: config.authToken || undefined,
    syncTools: false,
    enableFiltering: false
  };

  // Create and initialize agent
  const agent = new MCPAgent(agentConfig);
  
  try {
    await agent.initialize();
    
    // Execute the tool using the agent's MCP client
    const result = await agent.getMcpClient().callTool(toolName, toolInput);
    
    return result;
  } finally {
    // Clean up
    await agent.close();
  }
}

// Export all types and classes
export { MCPAgent } from './agents/agent.js';
export * from './providers/index.js';
export * from './search/index.js';
export * from './types.js';

