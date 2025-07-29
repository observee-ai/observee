/**
 * MCP Client wrapper - similar to Python's fastmcp Client
 */

import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { WebSocketClientTransport } from '@modelcontextprotocol/sdk/client/websocket.js';

export interface MCPServerConfig {
  url: string;
  headers?: Record<string, string>;
}

export interface MCPTool {
  name: string;
  description?: string;
  inputSchema?: any;
}

export class MCPClientWrapper {
  private client: Client;
  private transport?: any;
  private connected: boolean = false;
  private serverUrl: string;
  private headers?: Record<string, string>;
  private serverName: string;

  constructor(config: { mcpServers: Record<string, MCPServerConfig> }) {
    // Get the first server config
    this.serverName = Object.keys(config.mcpServers)[0];
    const serverConfig = config.mcpServers[this.serverName];
    
    this.serverUrl = serverConfig.url;
    this.headers = serverConfig.headers;
    
    this.client = new Client({
      name: 'mcp-agent-system',
      version: '1.0.0'
    });
  }

  async connect(): Promise<void> {
    if (this.connected) return;

    try {
      // Determine transport type based on URL
      if (this.serverUrl.startsWith('ws://') || this.serverUrl.startsWith('wss://')) {
        // WebSocket transport
        this.transport = new WebSocketClientTransport(new URL(this.serverUrl));
      } else {
        // Use StreamableHTTP transport for HTTP URLs (like Python's fastmcp)
        // Add trailing slash to path if needed, but don't modify query parameters
        let url = this.serverUrl;

        
        const transportOptions: any = {
          requestInit: {
            headers: this.headers || {}
          }
        };
        
        // Create StreamableHTTP transport (this is what fastmcp uses by default)
        this.transport = new StreamableHTTPClientTransport(new URL(url), transportOptions);
      }

      await this.client.connect(this.transport);
      this.connected = true;
      
      console.log(`✅ Successfully connected to MCP server: ${this.serverName} at ${this.serverUrl}`);
    } catch (error: any) {
      console.error('Failed to connect to MCP server:', error);
      console.error('Error details:', error.message);
      
      // Provide more specific error messages
      if (error.message?.includes('400')) {
        console.error('400 Bad Request - The server rejected the connection. Check that the URL and client_id are correct.');
      } else if (error.message?.includes('401')) {
        console.error('401 Unauthorized - Check that your API key is valid.');
      } else if (error.message?.includes('404')) {
        console.error('404 Not Found - The MCP endpoint may not exist at this URL.');
      } else if (error.message?.includes('406')) {
        console.error('406 Not Acceptable - The server requires specific Accept headers.');
      }
      
      throw error;
    }
  }

  async listTools(): Promise<MCPTool[]> {
    if (!this.connected) {
      await this.connect();
    }

    try {
      const result = await this.client.listTools();
      
      if (!result) {
        console.warn('MCP server returned null/undefined result for listTools');
        return [];
      }
      
      if (!result.tools) {
        console.warn('MCP server result missing tools array:', result);
        return [];
      }
      
      console.log(`Successfully loaded ${result.tools.length} tools from MCP server`);
      return result.tools || [];
    } catch (error) {
      console.error('Failed to list tools from MCP server:', error);
      console.error('Server URL:', this.serverUrl);
      console.error('Connected status:', this.connected);
      
      // Re-throw the error so the caller knows something went wrong
      // instead of silently returning empty array
      throw new Error(`Failed to list tools from MCP server: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  async callTool(name: string, args: Record<string, any>): Promise<any> {
    if (!this.connected) {
      await this.connect();
    }

    try {
      // The MCP SDK expects params with 'name' and 'arguments' properties
      const params = {
        name: name,
        arguments: args
      };
      
      const result = await this.client.callTool(params);
      
      return result.content || result;
    } catch (error) {
      console.error(`Failed to call tool ${name}:`, error);
      throw error;
    }
  }

  async close(): Promise<void> {
    if (this.connected && this.transport) {
      await this.transport.close();
      this.connected = false;
    }
  }

  // Expose session for providers that need it
  get session(): any {
    return {
      callTool: this.callTool.bind(this),
      listTools: this.listTools.bind(this)
    };
  }
}