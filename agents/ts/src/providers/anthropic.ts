/**
 * Anthropic Claude provider with native MCP support
 */

import Anthropic from '@anthropic-ai/sdk';
import { LLMResponse, Message, StreamChunk } from '../types.js';
import { BaseLLMProvider, LLMProviderOptions } from './base.js';

export class AnthropicProvider extends BaseLLMProvider {
  private client: Anthropic;

  constructor(options: LLMProviderOptions = {}) {
    super(options);
    this.model = this.model || 'claude-3-5-sonnet-20241022';
    
    const apiKey = options.apiKey || process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      throw new Error('Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.');
    }

    this.client = new Anthropic({ apiKey });
  }

  async generate(params: {
    messages: Message[];
    tools?: any[];
    mcp_config?: any;
    max_tokens?: number;
    temperature?: number;
  }): Promise<LLMResponse> {
    const {
      messages,
      tools,
      mcp_config,
      max_tokens = this.maxTokens,
      temperature = this.temperature
    } = params;

    try {
      // Convert messages to Anthropic format
      const anthropicMessages = messages.map(msg => ({
        role: msg.role as 'user' | 'assistant',
        content: msg.content
      }));

      // Build request parameters
      const requestParams: any = {
        model: this.model!,
        messages: anthropicMessages,
        max_tokens,
        temperature
      };

      // Add tools if provided
      if (tools && tools.length > 0) {
        requestParams.tools = tools;
      }

      let response;
      // Add MCP config if provided (for native MCP support)
      if (mcp_config) {
        // Native MCP support for Anthropic - matching Python implementation
        // Note: This requires beta access to Anthropic's MCP feature
        console.warn('Native MCP support for Anthropic requires beta access');
        // The actual implementation would include the proper beta headers
        // For now, we'll use standard tool calling
        response = await this.client.beta.messages.create({
          model: this.model!,
          messages: anthropicMessages,
          max_tokens,
          temperature,
          mcp_servers: mcp_config,
          betas: ["mcp-client-2025-04-04"],
        });
      } else {  

        // Make the API call
        response = await this.client.messages.create(requestParams);
      } 


      // Extract content and tool calls
      let content = '';
      const toolCalls: any[] = [];

      for (const block of response.content) {
        if (block.type === 'text') {
          content = block.text;
        } else if (block.type === 'tool_use') {
          toolCalls.push({
            type: 'function',
            function: {
              name: block.name,
              arguments: JSON.stringify(block.input)
            }
          });
        }
      }

      return {
        content,
        toolCalls: toolCalls
      };
    } catch (error) {
      console.error('Error calling Anthropic API:', error);
      throw error;
    }
  }

  async* generateStream(params: {
    messages: Message[];
    tools?: any[];
    mcp_config?: any;
    max_tokens?: number;
    temperature?: number;
  }): AsyncGenerator<StreamChunk, void, unknown> {
    const {
      messages,
      tools,
      mcp_config,
      max_tokens = this.maxTokens,
      temperature = this.temperature
    } = params;

    try {
      // Convert messages to Anthropic format
      const anthropicMessages = messages.map(msg => ({
        role: msg.role as 'user' | 'assistant',
        content: msg.content
      }));

      // Build request parameters
      const requestParams: any = {
        model: this.model!,
        messages: anthropicMessages,
        max_tokens,
        temperature,
        stream: true
      };

      // Add tools if provided
      if (tools && tools.length > 0) {
        requestParams.tools = tools;
      }

      let stream;
      // Add MCP config if provided (for native MCP support)
      if (mcp_config) {
        console.warn('Native MCP support for Anthropic requires beta access');
        stream = this.client.beta.messages.stream({
          model: this.model!,
          messages: anthropicMessages,
          max_tokens,
          temperature,
          mcp_servers: mcp_config,
          betas: ["mcp-client-2025-04-04"],
        });
      } else {
        stream = this.client.messages.stream(requestParams);
      }

      // Track tool calls during streaming
      const pendingToolCalls: Map<number, any> = new Map();

      for await (const chunk of stream) {
        if (chunk.type === 'message_start') {
          // Message started, nothing to yield yet
          continue;
        } else if (chunk.type === 'content_block_start') {
          // Content block started - check if it's a tool use
          if (chunk.content_block && chunk.content_block.type === 'tool_use') {
            // Store the tool call but don't yield yet - arguments might come in deltas
            pendingToolCalls.set(chunk.index, {
              name: chunk.content_block.name,
              input: chunk.content_block.input || {}
            });
          }
        } else if (chunk.type === 'content_block_delta') {
          if (chunk.delta && chunk.delta.type === 'text_delta') {
            const content = chunk.delta.text;
            yield {
              type: 'content',
              content: content
            };
          } else if (chunk.delta && chunk.delta.type === 'input_json_delta') {
            // Update tool call arguments as they stream in
            const existingToolCall = pendingToolCalls.get(chunk.index);
            if (existingToolCall) {
              // Append to input - Anthropic streams JSON deltas
              if (!existingToolCall.inputJson) {
                existingToolCall.inputJson = '';
              }
              existingToolCall.inputJson += chunk.delta.partial_json || '';
            }
          }
        } else if (chunk.type === 'content_block_stop') {
          // Content block ended - if it was a tool use, yield it now with complete arguments
          const toolCall = pendingToolCalls.get(chunk.index);
          if (toolCall) {
            // Parse the complete JSON if we have delta input
            if (toolCall.inputJson) {
              try {
                toolCall.input = JSON.parse(toolCall.inputJson);
              } catch (error) {
                console.warn('Failed to parse tool call arguments JSON:', toolCall.inputJson);
                toolCall.input = {};
              }
            }
            
            yield {
              type: 'tool_call',
              toolCall: {
                name: toolCall.name,
                input: toolCall.input
              }
            };
            
            // Remove from pending
            pendingToolCalls.delete(chunk.index);
          }
        } else if (chunk.type === 'message_delta') {
          // Message delta - might contain stop reason
          continue;
        } else if (chunk.type === 'message_stop') {
          // Message completed
          yield {
            type: 'done'
          };
          break;
        }
      }

    } catch (error) {
      console.error('Error streaming from Anthropic API:', error);
      throw error;
    }
  }
}