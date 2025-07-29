/**
 * Google Gemini provider with FastMCP session support
 */

import { GoogleGenerativeAI } from '@google/generative-ai';
import { LLMResponse, Message, StreamChunk } from '../types.js';
import { BaseLLMProvider, LLMProviderOptions } from './base.js';

export class GeminiProvider extends BaseLLMProvider {
  private client: GoogleGenerativeAI;
  private mcpClient?: any;

  constructor(options: LLMProviderOptions = {}) {
    super(options);
    this.model = this.model || 'gemini-1.5-pro';
    
    const apiKey = options.apiKey || process.env.GOOGLE_API_KEY || process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error('Google API key not found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.');
    }

    this.client = new GoogleGenerativeAI(apiKey);
  }

  setMcpClient(mcpClient: any): void {
    this.mcpClient = mcpClient;
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
      const model = this.client.getGenerativeModel({ 
        model: this.model!,
        generationConfig: {
          maxOutputTokens: max_tokens,
          temperature: temperature
        }
      });

      // Convert messages to Gemini format
      const lastMessage = messages[messages.length - 1];
      const prompt = lastMessage.content;

      // Build function declarations if tools are provided
      let functionDeclarations: any[] = [];
      if (tools && tools.length > 0) {
        functionDeclarations = tools.map(tool => ({
          name: tool.name,
          description: tool.description,
          parameters: tool.input_schema || tool.parameters
        }));
      }

      const generationConfig = {
        maxOutputTokens: max_tokens,
        temperature: temperature
      };

      let result;
      if (functionDeclarations.length > 0) {
        result = await model.generateContent({
          contents: [{ role: 'user', parts: [{ text: prompt }] }],
          tools: [{ functionDeclarations }],
          generationConfig
        });
      } else {
        result = await model.generateContent({
          contents: [{ role: 'user', parts: [{ text: prompt }] }],
          generationConfig
        });
      }

      const response = result.response;
      const content = response.text() || '';
      
      // Extract tool calls if present
      const toolCalls: any[] = [];
      const candidates = response.candidates || [];
      for (const candidate of candidates) {
        const parts = candidate.content?.parts || [];
        for (const part of parts) {
          if (part.functionCall) {
            toolCalls.push({
              type: 'function',
              function: {
                name: part.functionCall.name,
                arguments: JSON.stringify(part.functionCall.args || {})
              }
            });
          }
        }
      }

      return {
        content,
        toolCalls
      };
    } catch (error) {
      console.error('Error calling Gemini API:', error);
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
    // For now, implement a simple fallback that yields the full response
    // TODO: Implement proper streaming with Gemini SDK
    try {
      const response = await this.generate(params);
      
      // Yield content if available
      if (response.content) {
        yield {
          type: 'content',
          content: response.content
        };
      }

      // Yield tool calls if available
      if (response.toolCalls) {
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
      console.error('Error streaming from Gemini API:', error);
      throw error;
    }
  }
}