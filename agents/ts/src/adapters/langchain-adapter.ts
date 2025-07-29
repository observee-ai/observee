/**
 * LangChain adapter for converting MCP tools to LangChain format
 */

import type { JSONSchema } from '@dmitryrechkin/json-schema-to-zod';
import { JSONSchemaToZod } from '@dmitryrechkin/json-schema-to-zod';
import { DynamicStructuredTool } from '@langchain/core/tools';
import { z } from 'zod';

import { MCPClientWrapper } from '../utils/mcp-client.js';

interface CallToolResult {
  content?: Array<{
    type: string;
    text?: string;
    data?: string;
    resource?: {
      text?: string;
      blob?: string | Uint8Array | Buffer;
      type?: string;
    };
  }>;
  isError?: boolean;
}

function parseMcpToolResult(toolResult: CallToolResult): string {
  if (toolResult.isError) {
    throw new Error(`Tool execution failed: ${JSON.stringify(toolResult.content)}`);
  }
  if (!toolResult.content || toolResult.content.length === 0) {
    throw new Error('Tool execution returned no content');
  }

  let decoded = '';
  for (const item of toolResult.content) {
    switch (item.type) {
      case 'text': {
        decoded += item.text || '';
        break;
      }
      case 'image': {
        decoded += item.data || '';
        break;
      }
      case 'resource': {
        const res = item.resource;
        if (res?.text !== undefined) {
          decoded += res.text;
        } else if (res?.blob !== undefined) {
          // Check if blob is Uint8Array or Buffer
          const blob = res.blob;
          if (typeof blob === 'object' && blob !== null && 
              (blob.constructor === Uint8Array || (typeof Buffer !== 'undefined' && blob.constructor === Buffer))) {
            decoded += Buffer.from(blob as any).toString('base64');
          } else {
            decoded += String(blob);
          }
        } else {
          throw new Error(`Unexpected resource type: ${res?.type}`);
        }
        break;
      }
      default:
        throw new Error(`Unexpected content type: ${item.type}`);
    }
  }
  return decoded;
}

function schemaToZod(schema: unknown): z.ZodTypeAny {
  try {
    return JSONSchemaToZod.convert(schema as JSONSchema);
  } catch (err) {
    console.warn(`Failed to convert JSON schema to Zod: ${err}`);
    return z.any();
  }
}

export class LangChainAdapter {
  private mcpClient: MCPClientWrapper;

  constructor(mcpClient: MCPClientWrapper) {
    this.mcpClient = mcpClient;
  }

  /**
   * Convert MCP tools to LangChain tools
   */
  convertToolsToLangchain(tools: any[]): DynamicStructuredTool[] {
    const langchainTools: DynamicStructuredTool[] = [];

    for (const tool of tools) {
      try {
        // Convert JSON Schema to Zod schema using the proper converter
        const zodSchema = tool.inputSchema 
          ? schemaToZod(tool.inputSchema)
          : z.object({}).optional();

        // Create LangChain tool
        const langchainTool = new DynamicStructuredTool({
          name: tool.name || 'NO_NAME',
          description: tool.description || '', // Blank is acceptable but discouraged
          schema: zodSchema as any, // Type assertion to avoid deep instantiation error
          func: async (input: Record<string, any>): Promise<string> => {
            console.debug(`MCP tool "${tool.name}" received input:`, JSON.stringify(input));
            try {
              // Call the MCP tool
              const result = await this.mcpClient.callTool(tool.name, input);
              
              // Handle the result - it might be an array directly
              if (Array.isArray(result)) {
                return parseMcpToolResult({ content: result } as CallToolResult);
              } else if (result && typeof result === 'object' && 'content' in result) {
                return parseMcpToolResult(result as CallToolResult);
              } else {
                // Fallback - stringify the result
                return JSON.stringify(result);
              }
            } catch (error: any) {
              console.error(`Error executing MCP tool ${tool.name}:`, error.message);
              return `Error executing MCP tool: ${String(error)}`;
            }
          }
        });

        langchainTools.push(langchainTool);
      } catch (error) {
        console.warn(`Failed to convert tool ${tool.name}:`, error instanceof Error ? error.message : error);
      }
    }

    return langchainTools;
  }

}