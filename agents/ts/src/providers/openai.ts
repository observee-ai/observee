/**
 * OpenAI GPT provider
 */

import OpenAI from 'openai';
import { LLMResponse, Message, StreamChunk } from '../types.js';
import { BaseLLMProvider, LLMProviderOptions } from './base.js';

export class OpenAIProvider extends BaseLLMProvider {
  private client: OpenAI;

  constructor(options: LLMProviderOptions = {}) {
    super(options);
    this.model = this.model || 'gpt-4o';
    
    const apiKey = options.apiKey || process.env.OPENAI_API_KEY;
    if (!apiKey) {
      throw new Error('OpenAI API key not found. Set OPENAI_API_KEY environment variable.');
    }

    this.client = new OpenAI({ apiKey });
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
      max_tokens = this.maxTokens,
      temperature = this.temperature
    } = params;

    try {
      // Convert messages to OpenAI format
      const openaiMessages = messages.map(msg => ({
        role: msg.role as 'user' | 'assistant' | 'system',
        content: msg.content
      }));

      // Build request parameters
      const requestParams: any = {
        model: this.model!,
        messages: openaiMessages,
        max_tokens,
        temperature
      };

      // Add tools if provided
      if (tools && tools.length > 0) {
        requestParams.tools = tools.map(tool => {
          // Handle both formats: new OpenAI format and legacy format
          if (tool.type === 'function' && tool.function) {
            // Already in OpenAI format
            return tool;
          } else {
            // Legacy format - convert to OpenAI format
            const parameters = tool.input_schema || tool.parameters || { type: 'object', properties: {} };
            
            return {
              type: 'function',
              function: {
                name: tool.name,
                description: tool.description,
                parameters: parameters
              }
            };
          }
        });
        
        // Encourage tool usage - OpenAI can be reluctant to use tools without this
        requestParams.tool_choice = 'auto';
      }

      // Make the API call
      const response = await this.client.chat.completions.create(requestParams);

      // Extract content and tool calls
      const message = response.choices[0]?.message;
      const content = message?.content || '';
      const toolCalls = message?.tool_calls?.map(tc => ({
        type: 'function',
        function: {
          name: tc.function.name,
          arguments: tc.function.arguments
        }
      })) || [];

      return {
        content,
        toolCalls
      };
    } catch (error) {
      console.error('Error calling OpenAI API:', error);
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
    try {
      // Use the non-streaming API to ensure tool calls work properly
      const response = await this.generate(params);
      
      // Simulate streaming by yielding content in chunks
      if (response.content) {
        const words = response.content.split(' ');
        for (let i = 0; i < words.length; i++) {
          const chunk = i === words.length - 1 ? words[i] : words[i] + ' ';
          yield {
            type: 'content',
            content: chunk
          };
          // Small delay to simulate streaming
          await new Promise(resolve => setTimeout(resolve, 30));
        }
      }

      // Yield tool calls if available
      if (response.toolCalls && response.toolCalls.length > 0) {
        for (const toolCall of response.toolCalls) {
          yield {
            type: 'tool_call',
            toolCall: {
              name: toolCall.function?.name || '',
              input: JSON.parse(toolCall.function?.arguments || '{}')
            }
          };
        }
      }

      // Signal completion
      yield {
        type: 'done'
      };

    } catch (error) {
      console.error('Error streaming from OpenAI API:', error);
      throw error;
    }
  }
}